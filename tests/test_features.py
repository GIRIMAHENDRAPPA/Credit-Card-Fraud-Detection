"""
Unit tests for spatio-temporal tracking, rolling spend velocity,
and cyclical feature engineering.
"""
import unittest
import numpy as np
import pandas as pd

from src.features.spatio_temporal import (
    haversine_distance,
    compute_travel_speed,
    evaluate_impossible_travel
)
from src.features.financial_features import (
    compute_cyclical_time_features,
    UserProfileRegistry
)


class TestFeatureEngineering(unittest.TestCase):
    def test_haversine_known_coordinates(self):
        # NYC (40.7128, -74.0060) to London (51.5074, -0.1278)
        dist = haversine_distance(40.7128, -74.0060, 51.5074, -0.1278)
        # Distance should be approximately 5,570 km (+/- 70km)
        self.assertTrue(5500.0 < dist < 5650.0)

    def test_impossible_travel_detection(self):
        # 5,000 km in 600 seconds (10 minutes) = 30,000 km/h -> impossible
        res_fraud = evaluate_impossible_travel(5000.0, 600.0)
        self.assertTrue(res_fraud["is_impossible_travel"])
        self.assertGreater(res_fraud["travel_risk_score"], 0.8)
        self.assertGreater(res_fraud["speed_kmh"], 850.0)

        # 15 km in 3600 seconds (1 hour) = 15 km/h -> normal vehicular speed
        res_normal = evaluate_impossible_travel(15.0, 3600.0)
        self.assertFalse(res_normal["is_impossible_travel"])
        self.assertEqual(res_normal["travel_risk_score"], 0.0)

    def test_cyclical_time_features(self):
        timestamps = pd.Series([
            "2026-10-30 00:00:00",
            "2026-10-30 06:00:00",
            "2026-10-30 12:00:00",
            "2026-10-30 18:00:00"
        ])
        cyclic_df = compute_cyclical_time_features(timestamps)
        
        # Pythagorean trigonometric identity: sin^2 + cos^2 == 1
        hour_norm = cyclic_df["hour_sin"] ** 2 + cyclic_df["hour_cos"] ** 2
        np.testing.assert_allclose(hour_norm, np.ones(4), atol=1e-5)

    def test_user_profile_z_score(self):
        df = pd.DataFrame({
            "user_id": ["USER_A"] * 10 + ["USER_B"] * 10,
            "Amount": [10.0, 12.0, 11.0, 10.5, 9.5, 10.0, 11.5, 12.5, 10.0, 11.0] +
                      [1000.0, 1050.0, 980.0, 1020.0, 1010.0, 990.0, 1030.0, 970.0, 1000.0, 1050.0]
        })
        registry = UserProfileRegistry()
        registry.fit(df, user_col="user_id", amount_col="Amount")

        # A $500 transaction for USER_A (mean ~11, std ~1) is a massive anomaly
        z_a = registry.compute_z_score("USER_A", 500.0)
        self.assertGreater(z_a, 5.0)

        # A $1020 transaction for USER_B (mean ~1010, std ~25) is normal
        z_b = registry.compute_z_score("USER_B", 1020.0)
        self.assertTrue(-1.0 < z_b < 1.0)


if __name__ == "__main__":
    unittest.main()
