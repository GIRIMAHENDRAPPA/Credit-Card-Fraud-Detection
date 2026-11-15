"""
Cost-Sensitive Thresholding & Financial Matrix Optimizer.
Replaces arbitrary static thresholds (e.g., 0.5) with a rigorous financial cost matrix
that minimizes net fraud loss against customer friction and operational overhead.
"""
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
from sklearn.metrics import precision_recall_curve, roc_auc_score, auc, f1_score, fbeta_score
from src.config import COST_CONFIG, CostMatrixConfig


class FinancialCostOptimizer:
    """
    Computes business-driven optimal decision thresholds based on real financial economics:
    - False Negative (FN): Chargeback fraud loss = Transaction Amount + Fixed Penalty
    - False Positive (FP): False alarm customer friction & support overhead
    - True Positive (TP): Minor automated verification/investigation fee
    - True Negative (TN): Clean zero-friction transaction
    """
    def __init__(self, cost_config: CostMatrixConfig = COST_CONFIG):
        self.config = cost_config
        self.optimal_threshold: float = 0.5
        self.step_up_threshold: float = 0.35
        self.min_expected_loss: float = 0.0
        self.cost_curve: List[Dict[str, float]] = []

    def evaluate_cost_at_threshold(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        amounts: np.ndarray,
        threshold: float
    ) -> Dict[str, float]:
        """
        Calculates detailed financial and classification metrics at a given threshold.
        """
        y_pred = (y_proba >= threshold).astype(int)
        
        tp_mask = (y_true == 1) & (y_pred == 1)
        fp_mask = (y_true == 0) & (y_pred == 1)
        fn_mask = (y_true == 1) & (y_pred == 0)
        tn_mask = (y_true == 0) & (y_pred == 0)

        tp_count = int(np.sum(tp_mask))
        fp_count = int(np.sum(fp_mask))
        fn_count = int(np.sum(fn_mask))
        tn_count = int(np.sum(tn_mask))

        # Financial costs
        fn_amounts = amounts[fn_mask] if len(amounts) > 0 else np.zeros(0)
        tp_amounts = amounts[tp_mask] if len(amounts) > 0 else np.zeros(0)

        fn_cost = float(np.sum(fn_amounts * self.config.fn_chargeback_multiplier + self.config.fn_fixed_fee))
        fp_cost = float(fp_count * self.config.fp_friction_cost)
        tp_cost = float(tp_count * self.config.tp_investigation_cost)
        tn_cost = float(tn_count * self.config.tn_friction_cost)

        total_financial_loss = fn_cost + fp_cost + tp_cost + tn_cost
        fraud_amount_prevented = float(np.sum(tp_amounts))
        net_savings = fraud_amount_prevented - total_financial_loss

        # Core ML metrics
        precision = tp_count / (tp_count + fp_count + 1e-10)
        recall = tp_count / (tp_count + fn_count + 1e-10)
        f1 = 2 * (precision * recall) / (precision + recall + 1e-10)
        f2 = 5 * (precision * recall) / (4 * precision + recall + 1e-10)
        accuracy = (tp_count + tn_count) / max(len(y_true), 1)

        return {
            "threshold": round(threshold, 4),
            "total_financial_loss": round(total_financial_loss, 2),
            "fraud_prevented": round(fraud_amount_prevented, 2),
            "net_savings": round(net_savings, 2),
            "fn_cost": round(fn_cost, 2),
            "fp_cost": round(fp_cost, 2),
            "tp_cost": round(tp_cost, 2),
            "tp_count": tp_count,
            "fp_count": fp_count,
            "fn_count": fn_count,
            "tn_count": tn_count,
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "f2_score": round(f2, 4),
            "accuracy": round(accuracy, 4)
        }

    def optimize_threshold(
        self,
        y_true: np.ndarray,
        y_proba: np.ndarray,
        amounts: Optional[np.ndarray] = None,
        num_points: int = 100
    ) -> Dict[str, Any]:
        """
        Sweeps candidate thresholds across [0.01, 0.99] to discover the global
        minimum financial loss threshold.
        """
        y_true = np.asarray(y_true).ravel()
        y_proba = np.asarray(y_proba).ravel()
        if amounts is None:
            amounts = np.full_like(y_true, fill_value=150.0, dtype=float)
        else:
            amounts = np.asarray(amounts).ravel()

        thresholds = np.linspace(0.02, 0.98, num_points)
        curve = []
        best_loss = float("inf")
        best_threshold = 0.5

        for th in thresholds:
            metrics = self.evaluate_cost_at_threshold(y_true, y_proba, amounts, th)
            curve.append(metrics)
            if metrics["total_financial_loss"] < best_loss:
                best_loss = metrics["total_financial_loss"]
                best_threshold = th

        self.cost_curve = curve
        self.optimal_threshold = round(best_threshold, 4)
        # Set step-up 2FA threshold at 70% of optimal block threshold
        self.step_up_threshold = round(max(0.15, self.optimal_threshold * 0.7), 4)
        self.min_expected_loss = best_loss

        # Precision-Recall AUC
        prec, rec, _ = precision_recall_curve(y_true, y_proba)
        pr_auc = auc(rec, prec)
        roc_auc = roc_auc_score(y_true, y_proba)

        optimal_metrics = self.evaluate_cost_at_threshold(y_true, y_proba, amounts, self.optimal_threshold)
        optimal_metrics["pr_auc"] = round(pr_auc, 4)
        optimal_metrics["roc_auc"] = round(roc_auc, 4)
        optimal_metrics["step_up_threshold"] = self.step_up_threshold

        return optimal_metrics

    def determine_action(self, fraud_probability: float) -> Dict[str, Any]:
        """
        Routes a transaction into a banking operational decision tier:
        - ALLOW: Frictionless approval
        - STEP_UP_CHALLENGE: Request SMS / OTP authentication
        - DECLINE_BLOCK: Immediate transaction decline
        """
        if fraud_probability >= self.optimal_threshold:
            action = "DECLINE_BLOCK"
            recommendation = "Immediate decline. Route to Tier-2 Fraud Squad."
            color = "#ff4d4f"
        elif fraud_probability >= self.step_up_threshold:
            action = "STEP_UP_CHALLENGE"
            recommendation = "Hold transaction and trigger 3D-Secure / SMS OTP verification."
            color = "#faad14"
        else:
            action = "ALLOW"
            recommendation = "Approve seamlessly. Transaction behavior is within safe bounds."
            color = "#52c41a"

        return {
            "fraud_probability": round(fraud_probability, 4),
            "decision": action,
            "recommendation": recommendation,
            "status_color": color,
            "block_threshold": self.optimal_threshold,
            "challenge_threshold": self.step_up_threshold
        }
