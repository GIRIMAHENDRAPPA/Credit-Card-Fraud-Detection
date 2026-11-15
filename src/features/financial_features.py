"""
Financial Feature Engineering Module.
Computes rolling spend velocities, user amount Z-scores,
and cyclical timestamp transformations.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, Optional


def compute_cyclical_time_features(
    timestamps: pd.Series
) -> pd.DataFrame:
    """
    Transforms datetime series into cyclical sine and cosine components
    preserving the circular 24-hour daily and 7-day weekly periodicities.
    """
    dt_series = pd.to_datetime(timestamps)
    hours = dt_series.dt.hour + dt_series.dt.minute / 60.0 + dt_series.dt.second / 3600.0
    day_of_week = dt_series.dt.dayofweek

    hour_sin = np.sin(2.0 * np.pi * hours / 24.0)
    hour_cos = np.cos(2.0 * np.pi * hours / 24.0)
    day_sin = np.sin(2.0 * np.pi * day_of_week / 7.0)
    day_cos = np.cos(2.0 * np.pi * day_of_week / 7.0)

    return pd.DataFrame({
        "hour_sin": hour_sin,
        "hour_cos": hour_cos,
        "day_sin": day_sin,
        "day_cos": day_cos,
    }, index=timestamps.index)


class UserProfileRegistry:
    """
    Maintains historical user spending profiles (mean and std of transaction amounts)
    for computing real-time user-level Z-scores and spend velocity baselines.
    """
    def __init__(self, global_mean: float = 100.0, global_std: float = 250.0):
        self.global_mean = global_mean
        self.global_std = max(global_std, 1.0)
        self.user_stats: Dict[str, Dict[str, float]] = {}

    def fit(self, df: pd.DataFrame, user_col: str = "user_id", amount_col: str = "Amount"):
        if user_col in df.columns and amount_col in df.columns:
            self.global_mean = float(df[amount_col].mean())
            self.global_std = float(max(df[amount_col].std(), 1.0))
            grouped = df.groupby(user_col)[amount_col].agg(["mean", "std", "count"])
            for user_id, row in grouped.iterrows():
                std_val = row["std"] if pd.notnull(row["std"]) and row["std"] > 1e-4 else self.global_std * 0.5
                self.user_stats[str(user_id)] = {
                    "mean": float(row["mean"]),
                    "std": float(std_val),
                    "count": int(row["count"])
                }

    def compute_z_score(self, user_id: Any, amount: float) -> float:
        """Calculates normalized Z-score of transaction relative to cardholder history."""
        user_key = str(user_id)
        if user_key in self.user_stats:
            stats = self.user_stats[user_key]
            mean = stats["mean"]
            std = stats["std"]
        else:
            mean = self.global_mean
            std = self.global_std

        z = (amount - mean) / (std + 1e-5)
        return float(np.clip(z, -5.0, 15.0))


def compute_rolling_velocity_features(
    df: pd.DataFrame,
    user_col: str = "user_id",
    time_col: str = "timestamp",
    amount_col: str = "Amount"
) -> pd.DataFrame:
    """
    Computes windowed rolling velocities for each user:
    - 1-hour transaction count & amount sum
    - 24-hour transaction count & amount sum
    - Ratio of current amount to 24-hour rolling average
    """
    df = df.copy()
    if user_col not in df.columns or time_col not in df.columns or amount_col not in df.columns:
        df["velocity_cnt_1h"] = 1.0
        df["velocity_amt_1h"] = df.get(amount_col, 0.0)
        df["velocity_cnt_24h"] = 1.0
        df["velocity_amt_24h"] = df.get(amount_col, 0.0)
        df["amt_to_avg_ratio"] = 1.0
        return df

    if not np.issubdtype(df[time_col].dtype, np.datetime64):
        df[time_col] = pd.to_datetime(df[time_col])

    df = df.sort_values([user_col, time_col]).reset_index(drop=True)

    # Set datetime index temporarily for rolling window calculation
    df = df.set_index(time_col)
    
    # 1-hour window
    grouped_1h = df.groupby(user_col)[amount_col].rolling("1h", closed="left")
    df["velocity_cnt_1h"] = grouped_1h.count().fillna(0.0).values
    df["velocity_amt_1h"] = grouped_1h.sum().fillna(0.0).values

    # 24-hour window
    grouped_24h = df.groupby(user_col)[amount_col].rolling("24h", closed="left")
    df["velocity_cnt_24h"] = grouped_24h.count().fillna(0.0).values
    df["velocity_amt_24h"] = grouped_24h.sum().fillna(0.0).values

    # Ratio to 24-hour average
    avg_24h = (df["velocity_amt_24h"] / np.maximum(df["velocity_cnt_24h"], 1.0)).fillna(df[amount_col])
    df["amt_to_avg_ratio"] = np.clip(df[amount_col] / np.maximum(avg_24h, 1e-2), 0.1, 50.0)

    # Return with original integer indexing
    df = df.reset_index()
    return df
