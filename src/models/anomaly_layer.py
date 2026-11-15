"""
Unsupervised Anomaly Detection Layer.
Utilizes an Isolation Forest to detect zero-day fraud patterns, high-dimensional
outliers, and novel transaction vectors independent of historical labels.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import joblib
from pathlib import Path
from typing import Union, Tuple, Optional
from src.config import MODEL_CONFIG


class UnsupervisedAnomalyLayer:
    """
    Isolation Forest anomaly detector that outputs:
    - Raw anomaly score (continuous risk metric in [0, 1])
    - Outlier classification (binary 0 or 1)
    These outputs feed directly into the downstream supervised stacking classifiers.
    """
    def __init__(
        self,
        n_estimators: int = MODEL_CONFIG.iso_n_estimators,
        contamination: float = MODEL_CONFIG.iso_contamination,
        random_state: int = MODEL_CONFIG.random_state
    ):
        self.n_estimators = n_estimators
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            n_estimators=self.n_estimators,
            contamination=self.contamination,
            random_state=self.random_state,
            n_jobs=-1
        )
        self.min_score_: float = -0.5
        self.max_score_: float = 0.5
        self.is_fitted: bool = False

    def fit(self, X: Union[np.ndarray, pd.DataFrame]) -> "UnsupervisedAnomalyLayer":
        """Fits the Isolation Forest on transaction feature vectors."""
        if isinstance(X, pd.DataFrame):
            X_arr = X.values
        else:
            X_arr = X

        self.model.fit(X_arr)
        # Calibration bounds using decision function
        raw_scores = self.model.decision_function(X_arr)
        self.min_score_ = float(np.percentile(raw_scores, 0.5))
        self.max_score_ = float(np.percentile(raw_scores, 99.5))
        self.is_fitted = True
        return self

    def transform(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Transforms input feature vectors into a normalized [0, 1] anomaly risk score.
        Higher score indicates higher anomaly / outlier probability.
        """
        if not self.is_fitted:
            raise ValueError("AnomalyLayer must be fitted before transforming data.")

        if isinstance(X, pd.DataFrame):
            X_arr = X.values
        else:
            X_arr = X

        # IsolationForest decision_function: lower (negative) means more abnormal.
        # We invert it: negative decision_function -> higher anomaly risk.
        raw = self.model.decision_function(X_arr)
        
        # Sigmoid-inverted calibration
        # center around 0, scale so negative is close to 1, positive is close to 0
        normalized = 1.0 / (1.0 + np.exp(3.0 * raw))
        return normalized.reshape(-1, 1)

    def fit_transform(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        return self.fit(X).transform(X)

    def save(self, filepath: Union[str, Path]):
        joblib.dump({
            "model": self.model,
            "min_score": self.min_score_,
            "max_score": self.max_score_,
            "is_fitted": self.is_fitted
        }, filepath)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "UnsupervisedAnomalyLayer":
        state = joblib.load(filepath)
        instance = cls()
        instance.model = state["model"]
        instance.min_score_ = state["min_score"]
        instance.max_score_ = state["max_score"]
        instance.is_fitted = state["is_fitted"]
        return instance
