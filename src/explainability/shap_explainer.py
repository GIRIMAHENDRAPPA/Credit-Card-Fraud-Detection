"""
Explainable AI (XAI) & Reason Code Generation Module.
Leverages TreeSHAP to compute local feature attributions and generate compliance-grade
adverse action reason codes for every flagged credit card transaction.
"""
import numpy as np
import pandas as pd
import shap
from typing import List, Dict, Any, Union, Optional
import joblib
from pathlib import Path


# Human-interpretable banking reason code translation dictionary
FEATURE_CODE_MAPPINGS = {
    "anomaly_score": "High-dimensional outlier signature detected by Unsupervised Anomaly Layer",
    "impossible_travel_flag": "Geographic impossibility: card used in distant locations in quick succession",
    "travel_speed_kmh": "Abnormal physical velocity between consecutive transactions",
    "distance_prev_km": "Extreme geographic displacement from prior transaction location",
    "amt_z_score": "Transaction amount significantly exceeds cardholder historical spending baseline",
    "velocity_cnt_1h": "High frequency transaction burst detected within 1-hour window",
    "velocity_amt_1h": "Rapid cumulative spend velocity within 1-hour window",
    "velocity_cnt_24h": "Unusual 24-hour transaction frequency spike",
    "velocity_amt_24h": "Unusual 24-hour total spend volume",
    "amt_to_avg_ratio": "Transaction amount is disproportionately higher than recent daily average",
    "Amount": "Unusual absolute transaction monetary value",
    "hour_sin": "Transaction occurred outside normal cardholder diurnal activity hours",
    "hour_cos": "Uncharacteristic late-night or off-peak transaction timestamp",
    "day_sin": "Atypical day-of-week transaction timing pattern",
    "day_cos": "Atypical weekend/weekday transaction behavior",
    "V14": "Latent financial terminal risk pattern V14 (high fraud correlation)",
    "V4": "Latent merchant acquiring risk signal V4",
    "V12": "Latent account behavioral deviation signal V12",
    "V10": "Latent cardholder identity verification anomaly V10",
    "V17": "Latent behavioral pattern deviation V17",
    "V11": "Latent transaction frequency pattern V11",
    "V16": "Latent transaction sequence risk signal V16"
}


class FraudShapExplainer:
    """
    Computes TreeSHAP explanations for the supervised gradient-boosted models
    and translates attributions into actionable reason codes for risk analysts.
    """
    def __init__(self, model: Any, feature_names: List[str]):
        self.feature_names = feature_names
        self.explainer = shap.TreeExplainer(model)
        self.expected_value = float(
            self.explainer.expected_value if not isinstance(self.explainer.expected_value, (list, np.ndarray))
            else self.explainer.expected_value[-1]
        )

    def explain_transaction(
        self,
        features: Union[np.ndarray, pd.Series, pd.DataFrame, List[float]],
        top_k: int = 5
    ) -> Dict[str, Any]:
        """
        Generates local explanation for a single transaction.
        Returns top contributing reason codes with attribution values.
        """
        if isinstance(features, (pd.DataFrame, pd.Series)):
            x_arr = features.values.reshape(1, -1)
        elif isinstance(features, list):
            x_arr = np.array(features, dtype=float).reshape(1, -1)
        else:
            x_arr = np.asarray(features, dtype=float).reshape(1, -1)

        shap_vals = self.explainer.shap_values(x_arr)
        if isinstance(shap_vals, list):
            # For binary classification where list of [class 0, class 1] is returned
            shap_vec = shap_vals[1][0]
        elif shap_vals.ndim == 3:
            shap_vec = shap_vals[0, :, 1]
        else:
            shap_vec = shap_vals[0]

        feature_vals = x_arr[0]
        total_positive_push = float(np.sum(shap_vec[shap_vec > 0]))

        # Sort features by positive fraud contribution (increasing risk)
        positive_indices = np.where(shap_vec > 0)[0]
        sorted_pos = positive_indices[np.argsort(-shap_vec[positive_indices])]

        reason_codes = []
        for rank, idx in enumerate(sorted_pos[:top_k], start=1):
            feat_name = self.feature_names[idx] if idx < len(self.feature_names) else f"Feature_{idx}"
            val = float(feature_vals[idx])
            attribution = float(shap_vec[idx])
            rel_impact = (attribution / (total_positive_push + 1e-10)) * 100.0

            description = FEATURE_CODE_MAPPINGS.get(
                feat_name,
                f"Statistical indicator {feat_name} showed abnormal fraud attribution"
            )

            reason_codes.append({
                "rank": rank,
                "feature": feat_name,
                "feature_value": round(val, 4),
                "shap_attribution": round(attribution, 4),
                "relative_impact_percent": round(rel_impact, 1),
                "reason_code": f"RC_{feat_name.upper()}",
                "plain_english_explanation": description
            })

        # Top mitigating features (pulling score towards legitimate)
        negative_indices = np.where(shap_vec < 0)[0]
        sorted_neg = negative_indices[np.argsort(shap_vec[negative_indices])]
        mitigating_factors = []
        for idx in sorted_neg[:3]:
            feat_name = self.feature_names[idx] if idx < len(self.feature_names) else f"Feature_{idx}"
            mitigating_factors.append({
                "feature": feat_name,
                "feature_value": round(float(feature_vals[idx]), 4),
                "shap_attribution": round(float(shap_vec[idx]), 4)
            })

        return {
            "base_value": round(self.expected_value, 4),
            "top_fraud_reasons": reason_codes,
            "mitigating_factors": mitigating_factors,
            "all_shap_values": {
                name: round(float(val), 4)
                for name, val in zip(self.feature_names, shap_vec)
            }
        }

    def save(self, filepath: Union[str, Path]):
        joblib.dump({
            "feature_names": self.feature_names,
            "explainer": self.explainer,
            "expected_value": self.expected_value
        }, filepath)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "FraudShapExplainer":
        state = joblib.load(filepath)
        instance = cls.__new__(cls)
        instance.feature_names = state["feature_names"]
        instance.explainer = state["explainer"]
        instance.expected_value = state["expected_value"]
        return instance
