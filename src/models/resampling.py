"""
Class Imbalance Control Module.
Provides targeted resampling strategies to manage extreme class distributions
prior to training supervised base learners.
"""
import numpy as np
import pandas as pd
from typing import Tuple
from imblearn.over_sampling import SMOTE, BorderlineSMOTE
from imblearn.under_sampling import RandomUnderSampler
from imblearn.pipeline import Pipeline as ImbPipeline
from src.config import MODEL_CONFIG


def get_resampler(
    strategy: str = MODEL_CONFIG.resampling_strategy,
    smote_ratio: float = MODEL_CONFIG.smote_sampling_strategy,
    under_ratio: float = MODEL_CONFIG.undersample_sampling_strategy,
    random_state: int = MODEL_CONFIG.random_state
):
    """
    Constructs an imbalanced-learn resampling pipeline based on strategy.
    
    Strategies:
      - 'smote_undersample': Two-phase strategy. Generates synthetic minority instances
        via SMOTE up to smote_ratio, followed by controlled RandomUnderSampler.
      - 'borderline_smote': Focuses synthetic oversampling strictly on decision boundary fraud vectors.
      - 'undersample': Fast majority class reduction.
      - 'none': Passthrough with no resampling.
    """
    if strategy == "smote_undersample":
        return ImbPipeline([
            ("smote", SMOTE(sampling_strategy=smote_ratio, random_state=random_state)),
            ("under", RandomUnderSampler(sampling_strategy=under_ratio, random_state=random_state))
        ])
    elif strategy == "borderline_smote":
        return BorderlineSMOTE(sampling_strategy=smote_ratio, random_state=random_state)
    elif strategy == "undersample":
        return RandomUnderSampler(sampling_strategy=under_ratio, random_state=random_state)
    elif strategy in ("none", "passthrough"):
        return None
    else:
        raise ValueError(f"Unknown resampling strategy: {strategy}")


def apply_resampling(
    X: np.ndarray | pd.DataFrame,
    y: np.ndarray | pd.Series,
    strategy: str = MODEL_CONFIG.resampling_strategy
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Applies the targeted resampling strategy to the training dataset.
    Returns resampled (X_res, y_res).
    """
    resampler = get_resampler(strategy=strategy)
    if resampler is None:
        if isinstance(X, pd.DataFrame):
            X = X.values
        if isinstance(y, pd.Series):
            y = y.values
        return X, y

    X_res, y_res = resampler.fit_resample(X, y)
    return X_res, y_res
