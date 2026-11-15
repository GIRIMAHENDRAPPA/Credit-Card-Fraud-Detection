"""
Feature engineering subpackage.
"""
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

__all__ = [
    "haversine_distance",
    "compute_travel_speed",
    "evaluate_impossible_travel",
    "add_spatio_temporal_features",
    "compute_cyclical_time_features",
    "compute_rolling_velocity_features",
    "UserProfileRegistry"
]
