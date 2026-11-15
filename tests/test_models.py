"""
Unit tests for Unsupervised Anomaly Layer, Cost Matrix Optimizer, and PSI Drift Monitor.
"""
import unittest
import numpy as np
import pandas as pd

from src.models.anomaly_layer import UnsupervisedAnomalyLayer
from src.models.cost_sensitive import FinancialCostOptimizer
from src.monitoring.drift_detector import compute_psi, PSIDriftMonitor


class TestModels(unittest.TestCase):
    def test_anomaly_layer_output_bounds(self):
        np.random.seed(42)
        X_normal = np.random.normal(loc=0.0, scale=1.0, size=(200, 10))
        X_outlier = np.random.uniform(low=10.0, high=20.0, size=(5, 10))
        X = np.vstack([X_normal, X_outlier])

        layer = UnsupervisedAnomalyLayer(n_estimators=50, contamination=0.05, random_state=42)
        scores = layer.fit_transform(X)

        self.assertTrue(np.all(scores >= 0.0))
        self.assertTrue(np.all(scores <= 1.0))
        self.assertGreater(np.mean(scores[-5:]), np.mean(scores[:-5]))

    def test_cost_matrix_optimizer(self):
        optimizer = FinancialCostOptimizer()
        y_true = np.array([0]*900 + [1]*100)
        y_proba = np.concatenate([
            np.random.beta(1, 10, size=900),
            np.random.beta(10, 2, size=100)
        ])
        amounts = np.concatenate([
            np.random.uniform(10, 100, size=900),
            np.random.uniform(500, 2500, size=100)
        ])

        report = optimizer.optimize_threshold(y_true, y_proba, amounts=amounts)
        self.assertTrue(0.01 <= optimizer.optimal_threshold <= 0.99)
        self.assertGreater(report["pr_auc"], 0.5)
        self.assertGreater(report["net_savings"], 0.0)

    def test_psi_drift_detection(self):
        np.random.seed(42)
        baseline = np.random.normal(0, 1, 1000)
        prod_stable = np.random.normal(0, 1, 1000)
        psi_stable, _ = compute_psi(baseline, prod_stable)
        self.assertLess(psi_stable, 0.10)

        prod_drifted = np.random.normal(2.5, 1.5, 1000)
        psi_drifted, _ = compute_psi(baseline, prod_drifted)
        self.assertGreaterEqual(psi_drifted, 0.25)


if __name__ == "__main__":
    unittest.main()
