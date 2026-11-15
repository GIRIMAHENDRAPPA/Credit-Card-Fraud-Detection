"""
Hybrid Stacking Ensemble Meta-Classifier.
Combines cross-validated base predictions from XGBoost, LightGBM, and CatBoost
alongside unsupervised anomaly risk scores using a regularized Logistic Regression meta-learner.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional, Union
from sklearn.model_selection import StratifiedKFold
from sklearn.linear_model import LogisticRegression
from sklearn.base import clone
import joblib
from pathlib import Path
from src.config import MODEL_CONFIG
from src.models.base_learners import get_base_models
from src.models.resampling import apply_resampling


class HybridStackingClassifier:
    """
    Implements multi-layer stacking:
    Layer 1 (Unsupervised): Anomaly risk score from Isolation Forest.
    Layer 2 (Supervised Base Learners): XGBoost, LightGBM, CatBoost.
    Layer 3 (Meta-Learner): Regularized Logistic Regression combining base probabilities.
    """
    def __init__(
        self,
        base_models: Optional[Dict[str, Any]] = None,
        meta_learner: Optional[Any] = None,
        cv_folds: int = MODEL_CONFIG.cv_folds,
        random_state: int = MODEL_CONFIG.random_state
    ):
        self.random_state = random_state
        self.cv_folds = cv_folds
        self.base_models = base_models or get_base_models(random_state=self.random_state)
        self.meta_learner = meta_learner or LogisticRegression(
            C=MODEL_CONFIG.meta_regularization_c,
            penalty="l2",
            solver="lbfgs",
            max_iter=1000,
            random_state=self.random_state
        )
        self.fitted_base_models: Dict[str, Any] = {}
        self.fitted_meta_learner: Optional[Any] = None
        self.feature_names_: List[str] = []

    def fit(
        self,
        X: Union[np.ndarray, pd.DataFrame],
        y: Union[np.ndarray, pd.Series]
    ) -> "HybridStackingClassifier":
        """
        Fits the ensemble using K-fold out-of-fold prediction to train the meta-learner
        without target leakage, then refits all base learners on full data.
        """
        if isinstance(X, pd.DataFrame):
            self.feature_names_ = list(X.columns)
            X_arr = X.values
        else:
            X_arr = np.asarray(X)
            self.feature_names_ = [f"f_{i}" for i in range(X_arr.shape[1])]

        if isinstance(y, (pd.Series, pd.DataFrame)):
            y_arr = y.values.ravel()
        else:
            y_arr = np.asarray(y).ravel()

        n_samples = X_arr.shape[0]
        model_names = list(self.base_models.keys())
        oof_preds = np.zeros((n_samples, len(model_names)))

        n_pos = int(np.sum(y_arr == 1))
        n_neg = int(np.sum(y_arr == 0))
        pos_weight = max(1.0, float(n_neg) / max(n_pos, 1))

        # Re-initialize base models with dynamic positive class weighting
        self.base_models = get_base_models(random_state=self.random_state, scale_pos_weight=min(pos_weight, 50.0))

        skf = StratifiedKFold(n_splits=self.cv_folds, shuffle=True, random_state=self.random_state)

        for fold, (train_idx, val_idx) in enumerate(skf.split(X_arr, y_arr)):
            X_tr, y_tr = X_arr[train_idx], y_arr[train_idx]
            X_val, y_val = X_arr[val_idx], y_arr[val_idx]

            for i, name in enumerate(model_names):
                fold_model = clone(self.base_models[name])
                fold_model.fit(X_tr, y_tr)
                # Predict positive class probability
                oof_preds[val_idx, i] = fold_model.predict_proba(X_val)[:, 1]

        # Fit meta-learner on out-of-fold probability predictions
        self.fitted_meta_learner = clone(self.meta_learner)
        self.fitted_meta_learner.fit(oof_preds, y_arr)

        # Refit base models on full dataset
        self.fitted_base_models = {}
        for name, model in self.base_models.items():
            full_model = clone(model)
            full_model.fit(X_arr, y_arr)
            self.fitted_base_models[name] = full_model

        return self

    def predict_base_probas(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """Generates probabilities from each base learner."""
        if isinstance(X, pd.DataFrame):
            X_arr = X.values
        else:
            X_arr = np.asarray(X)

        probas = []
        for name in self.base_models.keys():
            model = self.fitted_base_models[name]
            p = model.predict_proba(X_arr)[:, 1]
            probas.append(p)
        return np.column_stack(probas)

    def predict_proba(self, X: Union[np.ndarray, pd.DataFrame]) -> np.ndarray:
        """
        Generates calibrated ensemble class probabilities [P(y=0), P(y=1)].
        """
        base_probas = self.predict_base_probas(X)
        meta_probas = self.fitted_meta_learner.predict_proba(base_probas)
        return meta_probas

    def predict(self, X: Union[np.ndarray, pd.DataFrame], threshold: float = 0.5) -> np.ndarray:
        """Binary predictions using custom decision threshold."""
        probas = self.predict_proba(X)[:, 1]
        return (probas >= threshold).astype(int)

    def get_meta_weights(self) -> Dict[str, float]:
        """Returns the regularized meta-learner weights assigned to each base model."""
        if self.fitted_meta_learner is None:
            return {}
        coefs = self.fitted_meta_learner.coef_[0]
        names = list(self.base_models.keys())
        return {name: float(coef) for name, coef in zip(names, coefs)}

    def save(self, filepath: Union[str, Path]):
        joblib.dump({
            "base_models": self.fitted_base_models,
            "meta_learner": self.fitted_meta_learner,
            "feature_names": self.feature_names_,
            "cv_folds": self.cv_folds,
            "random_state": self.random_state
        }, filepath)

    @classmethod
    def load(cls, filepath: Union[str, Path]) -> "HybridStackingClassifier":
        state = joblib.load(filepath)
        instance = cls(cv_folds=state["cv_folds"], random_state=state["random_state"])
        instance.fitted_base_models = state["base_models"]
        instance.fitted_meta_learner = state["meta_learner"]
        instance.feature_names_ = state["feature_names"]
        return instance
