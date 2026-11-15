"""
Generate 8 Diverse, 50/50 Balanced Sample CSV Files for Testing.
Each file contains exactly 50% legitimate transactions and 50% fraudulent transactions
tailored to distinct real-world financial fraud vectors:
1. Retail & E-Commerce (Velocity spikes, card-not-present fraud)
2. Cross-Border & Travel (Impossible travel, intercontinental teleportation)
3. ATM Cash Skimming (High-value cash outs, off-hour terminal anomalies)
4. Digital Wallets & P2P (Zero-day novel attacks, high Isolation Forest outliers)
5. Luxury Goods & High-Ticket (Extreme amount Z-scores, compromised cards)
6. Gas Pumps & Micro-Testing (Small probe transactions followed by large spikes)
7. Entertainment & Nightlife (Late night bursts, atypical temporal patterns)
8. Global Mixed Stream (Comprehensive blend of all banking scenarios)
"""
import os
import numpy as np
import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "sample_data"
PUBLIC_SAMPLES_DIR = BASE_DIR / "frontend" / "public" / "samples"

SAMPLES_DIR.mkdir(parents=True, exist_ok=True)
PUBLIC_SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

COLUMNS = [
    "id", "Amount", "user_id", "distance_prev_km", "time_delta_sec", "velocity_cnt_1h",
    "V1", "V2", "V3", "V4", "V5", "V6", "V7", "V8", "V9", "V10",
    "V11", "V12", "V13", "V14", "V15", "V16", "V17", "V18", "V19", "V20",
    "V21", "V22", "V23", "V24", "V25", "V26", "V27", "V28", "expected_label"
]


def create_balanced_batch(
    scenario_name: str,
    n_pairs: int,  # n_pairs * 2 total rows (50% normal, 50% fraud)
    fraud_amount_range: tuple,
    normal_amount_range: tuple,
    impossible_travel: bool = False,
    high_velocity: bool = False,
    novel_anomaly: bool = False,
    seed: int = 42
) -> pd.DataFrame:
    np.random.seed(seed)
    total_rows = n_pairs * 2
    records = []

    # 1. Normal Transactions (50%)
    for i in range(n_pairs):
        uid = f"USER_{1000 + i}"
        amt = round(float(np.random.uniform(*normal_amount_range)), 2)
        dist = round(float(np.random.exponential(scale=3.5)), 2)
        time_sec = float(np.random.randint(1800, 28800)) # 30 min to 8 hours
        vel_1h = float(np.random.choice([1, 1, 1, 2]))

        # Normal PCA distributions centered around 0 with low variance
        pca = np.random.normal(0.0, 0.35, 28)
        # V14, V4, V12, V10 normal
        pca[13] = np.random.uniform(-0.3, 0.4) # V14
        pca[3] = np.random.uniform(-0.4, 0.3)  # V4
        pca[11] = np.random.uniform(-0.2, 0.5) # V12
        pca[9] = np.random.uniform(-0.3, 0.3)  # V10

        row = [
            f"TXN_{scenario_name[:3].upper()}_NORM_{i+1:02d}",
            amt, uid, dist, time_sec, vel_1h,
            *[round(float(v), 4) for v in pca],
            "Normal"
        ]
        records.append(row)

    # 2. Fraud Transactions (50%)
    for i in range(n_pairs):
        uid = f"USER_{2000 + i}"
        amt = round(float(np.random.uniform(*fraud_amount_range)), 2)
        
        # Geodesic Impossible Travel setup across Indian Subcontinent
        if impossible_travel:
            # Distances between major Indian hubs (e.g. Mumbai -> Delhi 1150km, Chennai -> Delhi 1750km, Bengaluru -> Kolkata 1550km)
            dist = round(float(np.random.uniform(1150.0, 2200.0)), 1)
            time_sec = float(np.random.randint(60, 900)) # 1 to 15 minutes (speeds 4,600 to 130,000 km/h)
        else:
            dist = round(float(np.random.uniform(1.0, 25.0)), 1)
            time_sec = float(np.random.randint(90, 600))

        # Velocity Burst setup
        if high_velocity:
            vel_1h = float(np.random.randint(6, 12))
        else:
            vel_1h = float(np.random.randint(2, 5))

        # Latent PCA setup with distinct fraud signatures
        pca = np.random.normal(0.0, 0.8, 28)
        if novel_anomaly:
            # High-dimensional multi-component deviation for Isolation Forest
            pca[13] = float(np.random.uniform(-7.5, -4.5)) # V14
            pca[3] = float(np.random.uniform(3.5, 6.0))    # V4
            pca[11] = float(np.random.uniform(-6.0, -3.8)) # V12
            pca[9] = float(np.random.uniform(-5.0, -3.0))  # V10
            pca[16] = float(np.random.uniform(-6.0, -3.5)) # V17
        else:
            pca[13] = float(np.random.uniform(-5.5, -3.0)) # V14
            pca[3] = float(np.random.uniform(2.5, 4.8))    # V4
            pca[11] = float(np.random.uniform(-4.5, -2.5)) # V12
            pca[9] = float(np.random.uniform(-3.5, -2.0))  # V10

        row = [
            f"TXN_{scenario_name[:3].upper()}_FRAUD_{i+1:02d}",
            amt, uid, dist, time_sec, vel_1h,
            *[round(float(v), 4) for v in pca],
            "Fraud"
        ]
        records.append(row)

    df = pd.DataFrame(records, columns=COLUMNS)
    # Shuffle rows so normal and fraud are interleaved naturally
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)
    return df


def generate_all_samples():
    configs = [
        {
            "filename": "sample_01_retail_ecommerce_50_50.csv",
            "scenario": "ECOMMERCE",
            "n_pairs": 8,  # 16 total rows (8 normal, 8 fraud)
            "fraud_amount_range": (18500.0, 55000.0),
            "normal_amount_range": (250.0, 2200.0),
            "high_velocity": True,
            "impossible_travel": False,
            "novel_anomaly": False,
            "seed": 101
        },
        {
            "filename": "sample_02_cross_border_travel_50_50.csv",
            "scenario": "TRAVEL",
            "n_pairs": 6,  # 12 total rows (6 normal, 6 fraud)
            "fraud_amount_range": (22000.0, 75000.0),
            "normal_amount_range": (450.0, 3500.0),
            "high_velocity": False,
            "impossible_travel": True, # Impossible Travel trigger (e.g. Mumbai -> Delhi)
            "novel_anomaly": False,
            "seed": 102
        },
        {
            "filename": "sample_03_atm_cash_withdrawals_50_50.csv",
            "scenario": "ATM_CASH",
            "n_pairs": 10, # 20 total rows (10 normal, 10 fraud)
            "fraud_amount_range": (25000.0, 85000.0),
            "normal_amount_range": (500.0, 4500.0),
            "high_velocity": True,
            "impossible_travel": False,
            "novel_anomaly": True,
            "seed": 103
        },
        {
            "filename": "sample_04_digital_wallets_p2p_50_50.csv",
            "scenario": "WALLET",
            "n_pairs": 8,  # 16 total rows (8 normal, 8 fraud)
            "fraud_amount_range": (15000.0, 52000.0),
            "normal_amount_range": (150.0, 1800.0),
            "high_velocity": True,
            "impossible_travel": False,
            "novel_anomaly": True, # High Isolation Forest anomaly
            "seed": 104
        },
        {
            "filename": "sample_05_luxury_goods_high_ticket_50_50.csv",
            "scenario": "LUXURY",
            "n_pairs": 7,  # 14 total rows (7 normal, 7 fraud)
            "fraud_amount_range": (85000.0, 280000.0),
            "normal_amount_range": (2500.0, 9500.0),
            "high_velocity": False,
            "impossible_travel": True,
            "novel_anomaly": True,
            "seed": 105
        },
        {
            "filename": "sample_06_gas_and_convenience_50_50.csv",
            "scenario": "GAS_STATION",
            "n_pairs": 10, # 20 total rows (10 normal, 10 fraud)
            "fraud_amount_range": (12000.0, 35000.0),
            "normal_amount_range": (200.0, 2500.0),
            "high_velocity": True,
            "impossible_travel": False,
            "novel_anomaly": False,
            "seed": 106
        },
        {
            "filename": "sample_07_entertainment_nightlife_50_50.csv",
            "scenario": "NIGHTLIFE",
            "n_pairs": 8,  # 16 total rows (8 normal, 8 fraud)
            "fraud_amount_range": (22000.0, 68000.0),
            "normal_amount_range": (450.0, 3800.0),
            "high_velocity": True,
            "impossible_travel": False,
            "novel_anomaly": True,
            "seed": 107
        },
        {
            "filename": "sample_08_global_mixed_stream_50_50.csv",
            "scenario": "MIXED",
            "n_pairs": 12, # 24 total rows (12 normal, 12 fraud)
            "fraud_amount_range": (18000.0, 160000.0),
            "normal_amount_range": (100.0, 4200.0),
            "high_velocity": True,
            "impossible_travel": True,
            "novel_anomaly": True,
            "seed": 108
        }
    ]

    manifest = []
    print("=" * 80)
    print(" GENERATING 8 BALANCED (50% NORMAL / 50% FRAUD) SAMPLE CSV DATASETS")
    print("=" * 80)

    for cfg in configs:
        df = create_balanced_batch(
            scenario_name=cfg["scenario"],
            n_pairs=cfg["n_pairs"],
            fraud_amount_range=cfg["fraud_amount_range"],
            normal_amount_range=cfg["normal_amount_range"],
            impossible_travel=cfg["impossible_travel"],
            high_velocity=cfg["high_velocity"],
            novel_anomaly=cfg["novel_anomaly"],
            seed=cfg["seed"]
        )

        out_path1 = SAMPLES_DIR / cfg["filename"]
        out_path2 = PUBLIC_SAMPLES_DIR / cfg["filename"]

        df.to_csv(out_path1, index=False)
        df.to_csv(out_path2, index=False)

        counts = dict(df["expected_label"].value_counts())
        total = len(df)
        normal_pct = counts.get("Normal", 0) / total * 100
        fraud_pct = counts.get("Fraud", 0) / total * 100

        print(f"[+] {cfg['filename']:<46} | Rows: {total:2d} ({normal_pct:.0f}% Normal / {fraud_pct:.0f}% Fraud)")
        manifest.append({
            "filename": cfg["filename"],
            "scenario": cfg["scenario"],
            "total_rows": int(total),
            "normal_count": int(counts.get("Normal", 0)),
            "fraud_count": int(counts.get("Fraud", 0)),
            "url": f"/samples/{cfg['filename']}"
        })

    # Save manifest as JSON
    import json
    with open(SAMPLES_DIR / "samples_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)
    with open(PUBLIC_SAMPLES_DIR / "samples_manifest.json", "w") as f:
        json.dump(manifest, f, indent=2)

    print(f"\nSaved all 8 balanced CSV datasets to:")
    print(f" - {SAMPLES_DIR}")
    print(f" - {PUBLIC_SAMPLES_DIR}")
    print("=" * 80)


if __name__ == "__main__":
    generate_all_samples()
