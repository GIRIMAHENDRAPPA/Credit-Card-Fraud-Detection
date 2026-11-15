"""
Concept Drift & Population Stability Index (PSI) Monitoring Module.
Detects statistical shifts between training baselines and live production transaction
streams to safeguard model integrity and trigger retraining alerts.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union, Tuple
import joblib
from pathlib import Path
from src.config import PSI_CONFIG, PSIConfig


def compute_psi(
    expected: np.ndarray,
    actual: np.ndarray,
    num_bins: int = PSI_CONFIG.num_bins,
    epsilon: float = 1e-4
) -> Tuple[float, List[Dict[str, Any]]]:
    """
    Calculates Population Stability Index (PSI) between baseline (expected)
    and live monitoring (actual) data vectors.
    """
    expected = np.asarray(expected, dtype=float)
    actual = np.asarray(actual, dtype=float)

    # Filter out NaNs
    expected = expected[~np.isnan(expected)]
    actual = actual[~np.isnan(actual)]

    if len(expected) == 0 or len(actual) == 0:
        return 0.0, []

    # Calculate quantile bin edges from baseline (expected) distribution
    percentiles = np.linspace(0, 100, num_bins + 1)
    bin_edges = np.percentile(expected, percentiles)
    # Deduplicate bin edges in case of low variance
    bin_edges = np.unique(bin_edges)
    if len(bin_edges) < 2:
        return 0.0, []

    bin_edges[0] = -np.inf
    bin_edges[-1] = np.inf

    expected_counts, _ = np.histogram(expected, bins=bin_edges)
    actual_counts, _ = np.histogram(actual, bins=bin_edges)

    expected_pct = expected_counts / len(expected)
    actual_pct = actual_counts / len(actual)

    # Apply epsilon smoothing to prevent division by zero or log(0)
    expected_pct = np.clip(expected_pct, epsilon, 1.0)
    actual_pct = np.clip(actual_pct, epsilon, 1.0)

    # Re-normalize
    expected_pct = expected_pct / np.sum(expected_pct)
    actual_pct = actual_pct / np.sum(actual_pct)

    # PSI calculation formula: sum((Actual% - Expected%) * ln(Actual% / Expected%))
    psi_components = (actual_pct - expected_pct) * np.log(actual_pct / expected_pct)
    total_psi = float(np.sum(psi_components))

    bin_details = []
    for i in range(len(bin_edges) - 1):
        bin_details.append({
            "bin_index": i + 1,
            "lower": float(bin_edges[i]),
            "upper": float(bin_edges[i + 1]),
            "expected_pct": round(float(expected_pct[i] * 100.0), 2),
            "actual_pct": round(float(actual_pct[i] * 100.0), 2),
            "psi_contribution": round(float(psi_components[i]), 5)
        })

    return round(total_psi, 4), bin_details


class PSIDriftMonitor:
    """
    Monitors live transaction feature and score streams against baseline distributions.
    Categorizes stability into STABLE, MODERATE_DRIFT, and SIGNIFICANT_DRIFT.
    """
    def __init__(self, config: PSIConfig = PSI_CONFIG):
        self.config = config
        self.baseline_distributions: Dict[str, np.ndarray] = {}
        self.feature_names: List[str] = []

    def set_baseline(
        self,
        baseline_df: pd.DataFrame,
        features: Optional[List[str]] = None
    ):
        """Stores baseline feature profiles from training data."""
        self.feature_names = features if features is not None else list(baseline_df.columns)
        self.baseline_distributions = {}
        for feat in self.feature_names:
            if feat in baseline_df.columns:
                self.baseline_distributions[feat] = baseline_df[feat].dropna().values

    def check_drift(
        self,
        production_df: pd.DataFrame,
        alert_on_moderate: bool = False
    ) -> Dict[str, Any]:
        """
        Calculates PSI for each monitored feature and model score.
        Returns detailed drift diagnostics and alert status.
        """
        results = {}
        max_psi = 0.0
        drifted_features = []
        moderate_features = []

        for feat in self.feature_names:
            if feat in production_df.columns and feat in self.baseline_distributions:
                expected = self.baseline_distributions[feat]
                actual = production_df[feat].dropna().values
                psi_val, details = compute_psi(expected, actual, num_bins=self.config.num_bins)

                status = "STABLE"
                if psi_val >= self.config.moderate_drift_threshold:
                    status = "SIGNIFICANT_DRIFT"
                    drifted_features.append(feat)
                elif psi_val >= self.config.stable_threshold:
                    status = "MODERATE_DRIFT"
                    moderate_features.append(feat)

                results[feat] = {
                    "psi": psi_val,
                    "status": status,
                    "bin_breakdown": details
                }
                if psi_val > max_psi:
                    max_psi = psi_val

        overall_status = "STABLE"
        requires_retraining = False
        message = "All feature and risk score distributions are within stable operating bounds."

        if max_psi >= self.config.moderate_drift_threshold:
            overall_status = "SIGNIFICANT_DRIFT"
            requires_retraining = True
            message = (
                f"Severe concept drift detected in {len(drifted_features)} features "
                f"({', '.join(drifted_features[:3])}). Automated retraining alert triggered."
            )
        elif max_psi >= self.config.stable_threshold:
            overall_status = "MODERATE_DRIFT"
            message = (
                f"Moderate distribution shift detected in features: {', '.join(moderate_features[:3])}. "
                f"Supervised review advised."
            )

        return {
            "overall_status": overall_status,
            "max_psi": round(max_psi, 4),
            "requires_retraining_alert": requires_retraining,
            "drift_summary": message,
            "drifted_features": drifted_features,
            "moderate_features": moderate_features,
            "feature_metrics": results
        }

    def save(self, filepath: Union[str, Path]):
        joblib.dump({
            "baseline": self.baseline_distributions,
            "feature_names": self.feature_names,
            "config": self.config
        }, filepath)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "PSIDriftMonitor":
        state = joblib.load(filepath)
        instance = cls(config=state["config"])
        instance.baseline_distributions = state["baseline"]
        instance.feature_names = state["feature_names"]
        return instance
