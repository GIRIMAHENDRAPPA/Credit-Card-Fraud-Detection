"""
Spatio-Temporal Tracking Module.
Calculates geodesic Haversine distance, apparent transit speed,
and detects physical card cloning ("impossible travel") scenarios.
"""
import numpy as np
import pandas as pd
from typing import Tuple, Dict, Any
from src.config import SPATIO_CONFIG


def haversine_distance(
    lat1: np.ndarray | float,
    lon1: np.ndarray | float,
    lat2: np.ndarray | float,
    lon2: np.ndarray | float,
    radius_km: float = SPATIO_CONFIG.earth_radius_km
) -> np.ndarray | float:
    """
    Computes great-circle distance between two pairs of GPS coordinates
    using the spherical Haversine formula.

    Args:
        lat1, lon1: Coordinates of first point (in decimal degrees).
        lat2, lon2: Coordinates of second point (in decimal degrees).
        radius_km: Radius of the sphere in km (default Earth mean radius = 6371 km).

    Returns:
        Distance in kilometers.
    """
    # Convert degrees to radians
    phi1 = np.radians(lat1)
    phi2 = np.radians(lat2)
    delta_phi = np.radians(lat2 - lat1)
    delta_lambda = np.radians(lon2 - lon1)

    # Haversine central angle calculation
    a = (
        np.sin(delta_phi / 2.0) ** 2
        + np.cos(phi1) * np.cos(phi2) * np.sin(delta_lambda / 2.0) ** 2
    )
    # Clip for numerical stability within [-1, 1]
    a = np.clip(a, 0.0, 1.0)
    c = 2.0 * np.arcsin(np.sqrt(a))
    return radius_km * c


def compute_travel_speed(
    distance_km: np.ndarray | float,
    time_delta_seconds: np.ndarray | float
) -> np.ndarray | float:
    """
    Computes the apparent travel speed in km/h.
    If time_delta is zero or negative with non-zero distance, marks as extreme velocity.
    """
    time_delta_hours = np.maximum(time_delta_seconds, 1.0) / 3600.0
    speed = distance_km / time_delta_hours
    return speed


def evaluate_impossible_travel(
    distance_km: float,
    time_delta_seconds: float,
    max_speed_kmh: float = SPATIO_CONFIG.impossible_speed_kmh
) -> Dict[str, Any]:
    """
    Evaluates whether two consecutive transactions represent physically impossible travel
    indicating physical card cloning or compromised digital credentials.
    """
    speed_kmh = float(compute_travel_speed(distance_km, time_delta_seconds))
    is_impossible = (distance_km > 20.0) and (speed_kmh > max_speed_kmh)
    
    # Teleportation: significant distance in under 5 minutes
    is_teleportation = (distance_km > 50.0) and (time_delta_seconds < SPATIO_CONFIG.teleportation_time_sec)
    flagged = bool(is_impossible or is_teleportation)

    risk_score = 0.0
    if flagged:
        # Scale risk based on excess speed
        risk_score = min(1.0, 0.6 + (speed_kmh / 2000.0) * 0.4)
    elif speed_kmh > SPATIO_CONFIG.suspicious_speed_kmh:
        risk_score = 0.35

    return {
        "distance_km": round(distance_km, 2),
        "time_delta_seconds": round(time_delta_seconds, 1),
        "speed_kmh": round(speed_kmh, 2),
        "is_impossible_travel": flagged,
        "is_teleportation": bool(is_teleportation),
        "travel_risk_score": round(risk_score, 4),
        "reason": "Impossible travel: velocity exceeds commercial flight limits" if flagged else "Normal transit"
    }


def add_spatio_temporal_features(
    df: pd.DataFrame,
    user_col: str = "user_id",
    time_col: str = "timestamp",
    lat_col: str = "lat",
    lon_col: str = "lon"
) -> pd.DataFrame:
    """
    Vectorized extraction of spatio-temporal tracking features for a transaction dataframe.
    Sorts by user and timestamp, then computes lagged differences.
    """
    df = df.copy()
    if user_col not in df.columns or time_col not in df.columns or lat_col not in df.columns or lon_col not in df.columns:
        # If columns are absent, return df with default zeros
        df["distance_prev_km"] = 0.0
        df["time_delta_sec"] = 0.0
        df["travel_speed_kmh"] = 0.0
        df["impossible_travel_flag"] = 0
        return df

    # Ensure timestamp is datetime
    if not np.issubdtype(df[time_col].dtype, np.datetime64):
        df[time_col] = pd.to_datetime(df[time_col])

    df = df.sort_values([user_col, time_col]).reset_index(drop=True)

    # Shifted values by user
    grouped = df.groupby(user_col)
    df["prev_lat"] = grouped[lat_col].shift(1).fillna(df[lat_col])
    df["prev_lon"] = grouped[lon_col].shift(1).fillna(df[lon_col])
    prev_time = grouped[time_col].shift(1)

    # Distance calculation
    df["distance_prev_km"] = haversine_distance(
        df[lat_col].values,
        df[lon_col].values,
        df["prev_lat"].values,
        df["prev_lon"].values
    )
    df["distance_prev_km"] = df["distance_prev_km"].fillna(0.0)

    # Time delta in seconds
    time_diff = (df[time_col] - prev_time).dt.total_seconds().fillna(3600.0)
    df["time_delta_sec"] = np.maximum(time_diff, 1.0)

    # Apparent speed
    df["travel_speed_kmh"] = compute_travel_speed(df["distance_prev_km"].values, df["time_delta_sec"].values)

    # Impossible travel flag
    df["impossible_travel_flag"] = (
        (df["distance_prev_km"] > 20.0) & (df["travel_speed_kmh"] > SPATIO_CONFIG.impossible_speed_kmh)
    ).astype(int)

    # Clean intermediate shifted columns
    df = df.drop(columns=["prev_lat", "prev_lon"])
    return df
