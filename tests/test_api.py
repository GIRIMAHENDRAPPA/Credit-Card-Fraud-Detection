"""
Unit tests for FastAPI endpoints: /health, /api/v1/predict, /api/v1/cost-matrix.
"""
import unittest
from fastapi.testclient import TestClient
from api.app import app


class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_system_root(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_api_info(self):
        response = self.client.get("/api/info")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("service", data)
        self.assertIn("endpoints", data)

    def test_system_health(self):
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")

    def test_cost_matrix_endpoint(self):
        response = self.client.get("/api/v1/cost-matrix")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("cost_matrix_parameters", data)
        self.assertIn("optimal_block_threshold", data)

    def test_predict_endpoint(self):
        payload = {
            "id": "TXN_TEST_01",
            "Amount": 120.50,
            "V14": -0.5,
            "V4": 0.2
        }
        response = self.client.post("/api/v1/predict", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("fraud_probability", data)
        self.assertIn("decision", data)
        self.assertIn("unsupervised_anomaly_score", data)
        self.assertIn("base_model_probabilities", data)


if __name__ == "__main__":
    unittest.main()
