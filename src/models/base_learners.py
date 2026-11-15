"""
Supervised Base Learners Module.
Implements the gradient-boosted ensemble: XGBoost, LightGBM, and CatBoost.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, Optional
import xgboost as xgb
import lightgbm as lgb
from catboost import CatBoostClassifier
from src.config import MODEL_CONFIG


def get_base_models(
    random_state: int = MODEL_CONFIG.random_state,
    scale_pos_weight: float = 1.0
) -> Dict[str, Any]:
    """
    Instantiates the 3 gradient-boosted base learners with optimized hyperparameter defaults.
    """
    models = {
        "xgboost": xgb.XGBClassifier(
            n_estimators=150,
            learning_rate=0.08,
            max_depth=5,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            eval_metric="logloss",
            random_state=random_state,
            n_jobs=-1,
            tree_method="hist"
        ),
        "lightgbm": lgb.LGBMClassifier(
            n_estimators=150,
            learning_rate=0.08,
            max_depth=6,
            num_leaves=31,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale_pos_weight,
            random_state=random_state,
            n_jobs=-1,
            verbose=-1
        ),
        "catboost": CatBoostClassifier(
            iterations=150,
            learning_rate=0.08,
            depth=5,
            auto_class_weights="Balanced" if scale_pos_weight > 1.5 else None,
            random_seed=random_state,
            thread_count=-1,
            verbose=False
        )
    }
    return models
