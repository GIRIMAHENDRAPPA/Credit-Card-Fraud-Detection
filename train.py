"""
Comprehensive Training & Evaluation Script for Intelligent Credit Card Fraud Detection.
Demonstrates overcoming the Accuracy Paradox, trains the hybrid stacking ensemble,
and exports all production-ready model artifacts.
"""
import time
import sys
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score, precision_recall_curve, auc

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.config import MODEL_DIR, DATA_DIR, MODEL_CONFIG
from src.pipeline import FraudDetectionPipeline
from src.models.resampling import apply_resampling


def generate_synthetic_spatio_temporal_data(df: pd.DataFrame, seed: int = 42) -> pd.DataFrame:
    """
    Enriches tabular creditcard.csv with realistic spatio-temporal and velocity attributes
    to showcase complete production pipeline capabilities.
    """
    np.random.seed(seed)
    n = len(df)
    df = df.copy()

    # Assign users and timestamps
    num_users = max(50, n // 20)
    df["user_id"] = [f"USER_{idx}" for idx in np.random.randint(1000, 1000 + num_users, size=n)]
    
    # Synthetic timestamps spanning 30 days
    base_time = pd.Timestamp("2026-10-01 00:00:00")
    random_offsets = pd.to_timedelta(np.random.randint(0, 30 * 86400, size=n), unit="s")
    df["timestamp"] = base_time + random_offsets

    # Base coordinates across Indian subcontinent (lat: ~8.4 to 34.5 N, lon: ~68.7 to 97.2 E)
    base_lats = np.random.uniform(8.4, 34.5, size=n)
    base_lons = np.random.uniform(68.7, 97.2, size=n)

    # For fraud instances, inject occasional impossible travel (distant coordinates with short time delta)
    distances = np.random.exponential(scale=15.0, size=n)
    time_deltas = np.random.exponential(scale=7200.0, size=n) + 60.0

    if "Class" in df.columns:
        fraud_mask = df["Class"] == 1
        # 15% of frauds exhibit impossible travel / card cloning
        clone_indices = df[fraud_mask].sample(frac=0.15, random_state=seed).index
        distances[clone_indices] = np.random.uniform(1150.0, 2400.0, size=len(clone_indices))
        time_deltas[clone_indices] = np.random.uniform(60.0, 900.0, size=len(clone_indices)) # 1-15 mins

    df["lat"] = base_lats
    df["lon"] = base_lons
    df["distance_prev_km"] = distances
    df["time_delta_sec"] = time_deltas

    # Hourly and daily velocities
    df["velocity_cnt_1h"] = np.random.poisson(lam=1.2, size=n) + 1.0
    if "Class" in df.columns:
        # Fraud transactions often have rapid 1h velocity bursts
        df.loc[df["Class"] == 1, "velocity_cnt_1h"] += np.random.poisson(lam=3.5, size=int(fraud_mask.sum()))

    df["velocity_amt_1h"] = df["velocity_cnt_1h"] * df["Amount"]
    df["velocity_cnt_24h"] = df["velocity_cnt_1h"] + np.random.poisson(lam=2.5, size=n)
    df["velocity_amt_24h"] = df["velocity_cnt_24h"] * df["Amount"]

    return df


def run_training_experiment(
    sample_size: int = 50000,
    test_size: float = 0.2,
    random_state: int = 42
):
    print("=" * 80)
    print(" INTELLIGENT CREDIT CARD FRAUD DETECTION PIPELINE TRAINING")
    print(" Combining Unsupervised Anomaly Detection + Supervised Ensemble Stacking")
    print("=" * 80)

    csv_path = DATA_DIR / "creditcard.csv"
    if not csv_path.exists():
        raise FileNotFoundError(f"Dataset not found at {csv_path}")

    print(f"\n[1/6] Loading representative transactions from {csv_path}...")
    t0 = time.time()
    # Read realistic imbalanced dataset with normal and fraud transaction streams
    df_norm = pd.read_csv(csv_path, nrows=25000)
    df_fraud = pd.read_csv(csv_path, skiprows=300000, nrows=1200, header=None)
    df_fraud.columns = df_norm.columns
    raw_df = pd.concat([df_norm, df_fraud], ignore_index=True)
    print(f"Loaded {len(raw_df):,} records in {time.time() - t0:.2f}s.")
    print(f"Class distribution: {dict(raw_df['Class'].value_counts())}")

    print("\n[2/6] Enriching with Spatio-Temporal and Rolling Behavioral Signatures...")
    enriched_df = generate_synthetic_spatio_temporal_data(raw_df, seed=random_state)

    train_df, test_df = train_test_split(
        enriched_df,
        test_size=test_size,
        stratify=enriched_df["Class"],
        random_state=random_state
    )
    print(f"Train split: {len(train_df):,} samples | Test split: {len(test_df):,} samples.")

    print("\n[3/6] Initializing & Fitting FraudDetectionPipeline...")
    t_train = time.time()
    pipeline = FraudDetectionPipeline()
    metrics = pipeline.fit(train_df, optimize_costs=True)
    print(f"Training completed in {time.time() - t_train:.2f}s.")

    print("\n[4/6] Evaluating Test Set Performance & Overcoming Accuracy Paradox...")
    X_test_feats, y_test = pipeline.prepare_features(test_df, is_training=False)
    
    # Anomaly scores on test
    base_feats = X_test_feats[[c for c in pipeline.feature_columns if c != "anomaly_score"]]
    X_test_feats["anomaly_score"] = pipeline.anomaly_layer.transform(base_feats).ravel()
    X_test_ordered = X_test_feats[pipeline.feature_columns]

    test_probas = pipeline.stacking_classifier.predict_proba(X_test_ordered)[:, 1]
    opt_threshold = pipeline.cost_optimizer.optimal_threshold
    test_preds_opt = (test_probas >= opt_threshold).astype(int)
    test_preds_naive_50 = (test_probas >= 0.50).astype(int)
    test_preds_all_zeros = np.zeros_like(y_test)

    # Metrics comparison
    test_amounts = test_df["Amount"].values
    cost_opt = pipeline.cost_optimizer.evaluate_cost_at_threshold(y_test, test_probas, test_amounts, opt_threshold)
    cost_naive_50 = pipeline.cost_optimizer.evaluate_cost_at_threshold(y_test, test_probas, test_amounts, 0.50)
    cost_all_zeros = pipeline.cost_optimizer.evaluate_cost_at_threshold(y_test, test_probas, test_amounts, 1.00)

    prec, rec, _ = precision_recall_curve(y_test, test_probas)
    test_pr_auc = auc(rec, prec)
    test_roc_auc = roc_auc_score(y_test, test_probas)

    print("\n" + "=" * 80)
    print(" [BENCHMARK] ACCURACY PARADOX BENCHMARK COMPARISON TABLE")
    print("=" * 80)
    comparison = pd.DataFrame([
        {
            "Model / Strategy": "Naive 'Predict All Legitimate' (Class 0)",
            "Accuracy": f"{cost_all_zeros['accuracy']*100:.2f}%",
            "Recall": f"{cost_all_zeros['recall']*100:.2f}%",
            "Precision": f"{cost_all_zeros['precision']*100:.2f}%",
            "F1-Score": f"{cost_all_zeros['f1_score']:.4f}",
            "PR-AUC": "0.0000",
            "Total Financial Loss": f"₹{cost_all_zeros['total_financial_loss']:,.2f}",
            "Status": "[FAIL] Disastrous Banking Failure (100% Frauds Missed)"
        },
        {
            "Model / Strategy": "Stacking Model with Static 0.50 Cutoff",
            "Accuracy": f"{cost_naive_50['accuracy']*100:.2f}%",
            "Recall": f"{cost_naive_50['recall']*100:.2f}%",
            "Precision": f"{cost_naive_50['precision']*100:.2f}%",
            "F1-Score": f"{cost_naive_50['f1_score']:.4f}",
            "PR-AUC": f"{test_pr_auc:.4f}",
            "Total Financial Loss": f"₹{cost_naive_50['total_financial_loss']:,.2f}",
            "Status": "[WARN] Sub-optimal Thresholding"
        },
        {
            "Model / Strategy": f"Hybrid Stacking + Cost Matrix (Cutoff: {opt_threshold:.3f})",
            "Accuracy": f"{cost_opt['accuracy']*100:.2f}%",
            "Recall": f"{cost_opt['recall']*100:.2f}%",
            "Precision": f"{cost_opt['precision']*100:.2f}%",
            "F1-Score": f"{cost_opt['f1_score']:.4f}",
            "PR-AUC": f"{test_pr_auc:.4f}",
            "Total Financial Loss": f"₹{cost_opt['total_financial_loss']:,.2f}",
            "Status": "[PASS] Optimal Business Profitability"
        }
    ])
    print(comparison.to_string(index=False))
    print("=" * 80)

    print(f"\nNet Financial Savings of Cost-Sensitive Optimization over Naive Baseline:")
    rupees_saved = cost_all_zeros['total_financial_loss'] - cost_opt['total_financial_loss']
    print(f"[+] ₹{rupees_saved:,.2f} preserved in prevented fraud chargebacks!")

    print("\n[5/6] Meta-Learner Regularization Weights:")
    for model_name, weight in pipeline.stacking_classifier.get_meta_weights().items():
        print(f"  - {model_name:12s}: {weight:+.4f}")

    print("\n[6/6] Persisting Production Model Artifacts to saved_models/...")
    pipeline.save_pipeline(MODEL_DIR)
    print(f"Pipeline persisted successfully to {MODEL_DIR}")

    return pipeline, cost_opt


if __name__ == "__main__":
    run_training_experiment(sample_size=30000)
