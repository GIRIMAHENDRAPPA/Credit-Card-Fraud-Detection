"""
Unified End-to-End Hybrid Fraud Detection Pipeline.
Coordinates feature engineering, unsupervised anomaly scoring, ensemble stacking,
cost-sensitive decisioning, TreeSHAP explainability, and PSI drift monitoring.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Union, Tuple
from pathlib import Path
import joblib

from src.config import MODEL_DIR, COST_CONFIG, MODEL_CONFIG
from src.features.spatio_temporal import (
    haversine_distance,
    compute_travel_speed,
    evaluate_impossible_travel,
    add_spatio_temporal_features
)
from src.features.financial_features import (
    compute_cyclical_time_features,
    compute_rolling_velocity_features,
    UserProfileRegistry
)
from src.models.anomaly_layer import UnsupervisedAnomalyLayer
from src.models.stacking_meta import HybridStackingClassifier
from src.models.cost_sensitive import FinancialCostOptimizer
from src.explainability.shap_explainer import FraudShapExplainer
from src.monitoring.drift_detector import PSIDriftMonitor


class FraudDetectionPipeline:
    """
    Production-grade end-to-end pipeline encapsulating the entire intelligent
    credit card fraud detection architecture.
    """
    def __init__(self):
        self.user_registry = UserProfileRegistry()
        self.anomaly_layer = UnsupervisedAnomalyLayer()
        self.stacking_classifier = HybridStackingClassifier()
        self.cost_optimizer = FinancialCostOptimizer()
        self.shap_explainer: Optional[FraudShapExplainer] = None
        self.drift_monitor = PSIDriftMonitor()
        self.feature_columns: List[str] = []
        self.is_trained: bool = False

    def prepare_features(
        self,
        df: pd.DataFrame,
        is_training: bool = False
    ) -> Tuple[pd.DataFrame, np.ndarray]:
        """
        Extracts engineered features (spatio-temporal, rolling velocity, cyclical, z-scores)
        and merges with raw/PCA transaction attributes.
        """
        df = df.copy()

        # Handle ID column if present
        if "id" in df.columns:
            df = df.drop(columns=["id"])

        # Extract target if present
        target = None
        if "Class" in df.columns:
            target = df["Class"].values
            df = df.drop(columns=["Class"])

        # Spatio-Temporal features
        has_valid_coords = (
            "lat" in df.columns and "lon" in df.columns and
            df["lat"].notnull().all() and df["lon"].notnull().all() and
            df["lat"].iloc[0] is not None and df["lon"].iloc[0] is not None
        )
        if has_valid_coords:
            df = add_spatio_temporal_features(df)
        else:
            if "lat" in df.columns: df = df.drop(columns=["lat"])
            if "lon" in df.columns: df = df.drop(columns=["lon"])
            if "distance_prev_km" not in df.columns or df["distance_prev_km"].iloc[0] is None:
                df["distance_prev_km"] = 0.0
            if "travel_speed_kmh" not in df.columns or df["travel_speed_kmh"].iloc[0] is None:
                df["travel_speed_kmh"] = 0.0
            if "impossible_travel_flag" not in df.columns or df["impossible_travel_flag"].iloc[0] is None:
                df["impossible_travel_flag"] = 0

        # Cyclical Time features
        has_valid_timestamp = (
            "timestamp" in df.columns and df["timestamp"].notnull().all() and df["timestamp"].iloc[0] is not None
        )
        if has_valid_timestamp:
            time_feats = compute_cyclical_time_features(df["timestamp"])
            for c in time_feats.columns:
                df[c] = time_feats[c]
            df = df.drop(columns=["timestamp"])
        else:
            if "timestamp" in df.columns: df = df.drop(columns=["timestamp"])
            for c in ["hour_sin", "hour_cos", "day_sin", "day_cos"]:
                if c not in df.columns:
                    df[c] = 0.0
                if c not in df.columns:
                    df[c] = 0.0

        # User Profile & Z-score features
        if "user_id" in df.columns:
            if is_training:
                self.user_registry.fit(df, user_col="user_id", amount_col="Amount")
            df["amt_z_score"] = [
                self.user_registry.compute_z_score(uid, amt)
                for uid, amt in zip(df["user_id"], df["Amount"])
            ]
            df = df.drop(columns=["user_id"])
        else:
            if "amt_z_score" not in df.columns:
                amt_mean = float(df["Amount"].mean()) if "Amount" in df.columns else 100.0
                amt_std = float(df["Amount"].std()) if "Amount" in df.columns else 250.0
                amt_std = max(amt_std, 1.0)
                df["amt_z_score"] = (df["Amount"] - amt_mean) / amt_std

        # Velocity features
        for v in ["velocity_cnt_1h", "velocity_amt_1h", "velocity_cnt_24h", "velocity_amt_24h", "amt_to_avg_ratio"]:
            default_val = 1.0 if "cnt" in v or "ratio" in v else (float(df["Amount"].iloc[0]) if "Amount" in df.columns else 0.0)
            if v not in df.columns or df[v].iloc[0] is None:
                df[v] = default_val
            else:
                df[v] = df[v].fillna(default_val)

        # Log transform Amount
        if "Amount" in df.columns:
            df["log_amount"] = np.log1p(np.maximum(df["Amount"], 0.0))

        # Select only numeric features
        numeric_df = df.select_dtypes(include=[np.number])
        return numeric_df, target

    def fit(
        self,
        raw_df: pd.DataFrame,
        optimize_costs: bool = True
    ) -> Dict[str, Any]:
        """
        Trains the full multi-tier pipeline:
        1. Feature engineering
        2. Unsupervised Isolation Forest
        3. Supervised Stacking Base Learners + Meta-Classifier
        4. Financial Cost Matrix Threshold Optimizer
        5. TreeSHAP Explainer
        6. PSI Drift Baseline Profile
        """
        print("[PIPELINE] Phase 1: Feature Engineering...")
        X_feats, y = self.prepare_features(raw_df, is_training=True)
        if y is None:
            raise ValueError("Training dataframe must include 'Class' target column.")

        amounts = raw_df["Amount"].values if "Amount" in raw_df.columns else np.full(len(y), 150.0)

        print("[PIPELINE] Phase 2: Unsupervised Anomaly Layer (Isolation Forest)...")
        self.anomaly_layer.fit(X_feats)
        anomaly_scores = self.anomaly_layer.transform(X_feats)
        X_feats["anomaly_score"] = anomaly_scores.ravel()

        self.feature_columns = list(X_feats.columns)

        print("[PIPELINE] Phase 3: Hybrid Stacking Ensemble (XGBoost + LightGBM + CatBoost)...")
        self.stacking_classifier.fit(X_feats, y)

        print("[PIPELINE] Phase 4: Financial Cost Matrix Optimization...")
        train_probas = self.stacking_classifier.predict_proba(X_feats)[:, 1]
        cost_report = self.cost_optimizer.optimize_threshold(y, train_probas, amounts=amounts)

        print("[PIPELINE] Phase 5: TreeSHAP Explainer Initialization...")
        # Initialize TreeSHAP on primary gradient-boosted base model (XGBoost)
        primary_model = self.stacking_classifier.fitted_base_models["xgboost"]
        self.shap_explainer = FraudShapExplainer(primary_model, feature_names=self.feature_columns)

        print("[PIPELINE] Phase 6: Registering PSI Drift Monitoring Baseline...")
        self.drift_monitor.set_baseline(X_feats, features=self.feature_columns)

        self.is_trained = True
        return {
            "status": "SUCCESS",
            "optimal_threshold": self.cost_optimizer.optimal_threshold,
            "step_up_threshold": self.cost_optimizer.step_up_threshold,
            "pr_auc": cost_report["pr_auc"],
            "roc_auc": cost_report["roc_auc"],
            "f1_score": cost_report["f1_score"],
            "recall": cost_report["recall"],
            "precision": cost_report["precision"],
            "net_savings": cost_report["net_savings"],
            "meta_learner_weights": self.stacking_classifier.get_meta_weights()
        }

    def predict_transaction(
        self,
        transaction_data: Union[Dict[str, Any], pd.DataFrame],
        include_shap: bool = True
    ) -> Dict[str, Any]:
        """
        Scoring pipeline for a single live transaction in real-time (<15ms).
        """
        if not self.is_trained:
            raise RuntimeError("Pipeline must be trained or loaded before scoring transactions.")

        if isinstance(transaction_data, dict):
            df = pd.DataFrame([transaction_data])
        else:
            df = transaction_data.copy()

        # Check Spatio-Temporal impossible travel directly if previous location supplied
        impossible_eval = None
        if "distance_prev_km" in df.columns and "time_delta_sec" in df.columns:
            dist = float(df["distance_prev_km"].iloc[0])
            sec = float(df["time_delta_sec"].iloc[0])
            impossible_eval = evaluate_impossible_travel(dist, sec)

        X_feats, _ = self.prepare_features(df, is_training=False)
        
        # Calculate unsupervised anomaly score
        # Align features if missing
        for col in self.feature_columns:
            if col != "anomaly_score" and col not in X_feats.columns:
                X_feats[col] = 0.0

        # Anomaly scoring
        base_features_for_anomaly = X_feats[[c for c in self.feature_columns if c != "anomaly_score"]].fillna(0.0)
        anomaly_score = float(self.anomaly_layer.transform(base_features_for_anomaly)[0, 0])
        X_feats["anomaly_score"] = anomaly_score

        # Order features exactly as trained
        X_ordered = X_feats[self.feature_columns].fillna(0.0)

        # Stacking probabilities
        base_probas = self.stacking_classifier.predict_base_probas(X_ordered)[0]
        meta_probas = self.stacking_classifier.predict_proba(X_ordered)[0]
        fraud_prob = float(meta_probas[1])

        # Cost-sensitive tier decision
        action_result = self.cost_optimizer.determine_action(fraud_prob)

        # Override or escalate if physical impossible travel detected
        if impossible_eval and impossible_eval["is_impossible_travel"]:
            action_result["decision"] = "DECLINE_BLOCK"
            action_result["recommendation"] = "Impossible travel detected. Immediate card freeze."
            action_result["status_color"] = "#ff4d4f"

        response = {
            "transaction_id": str(transaction_data.get("id", "TXN_LIVE")),
            "fraud_probability": round(fraud_prob, 4),
            "decision": action_result["decision"],
            "recommendation": action_result["recommendation"],
            "status_color": action_result["status_color"],
            "unsupervised_anomaly_score": round(anomaly_score, 4),
            "base_model_probabilities": {
                "xgboost": round(float(base_probas[0]), 4),
                "lightgbm": round(float(base_probas[1]), 4),
                "catboost": round(float(base_probas[2]), 4)
            },
            "spatio_temporal_audit": impossible_eval
        }

        if include_shap and self.shap_explainer is not None:
            explanation = self.shap_explainer.explain_transaction(X_ordered.iloc[0], top_k=4)
            response["reason_codes"] = explanation["top_fraud_reasons"]
            response["mitigating_factors"] = explanation["mitigating_factors"]

        return response

    def save_pipeline(self, dir_path: Union[str, Path] = MODEL_DIR):
        """Persists all components to disk."""
        dir_path = Path(dir_path)
        dir_path.mkdir(parents=True, exist_ok=True)
        self.anomaly_layer.save(dir_path / "anomaly_layer.joblib")
        self.stacking_classifier.save(dir_path / "stacking_ensemble.joblib")
        self.drift_monitor.save(dir_path / "drift_monitor.joblib")
        if self.shap_explainer is not None:
            self.shap_explainer.save(dir_path / "shap_explainer.joblib")
        joblib.dump({
            "feature_columns": self.feature_columns,
            "cost_optimizer": self.cost_optimizer,
            "user_registry": self.user_registry,
            "is_trained": self.is_trained
        }, dir_path / "pipeline_state.joblib")
        print(f"[PIPELINE] Saved full pipeline components to {dir_path}")

    @classmethod
    def load_pipeline(cls, dir_path: Union[str, Path] = MODEL_DIR) -> "FraudDetectionPipeline":
        """Loads fitted pipeline from disk."""
        dir_path = Path(dir_path)
        instance = cls()
        instance.anomaly_layer = UnsupervisedAnomalyLayer.load(dir_path / "anomaly_layer.joblib")
        instance.stacking_classifier = HybridStackingClassifier.load(dir_path / "stacking_ensemble.joblib")
        instance.drift_monitor = PSIDriftMonitor.load(dir_path / "drift_monitor.joblib")
        if (dir_path / "shap_explainer.joblib").exists():
            instance.shap_explainer = FraudShapExplainer.load(dir_path / "shap_explainer.joblib")
        state = joblib.load(dir_path / "pipeline_state.joblib")
        instance.feature_columns = state["feature_columns"]
        instance.cost_optimizer = state["cost_optimizer"]
        instance.user_registry = state["user_registry"]
        instance.is_trained = state["is_trained"]
        return instance
