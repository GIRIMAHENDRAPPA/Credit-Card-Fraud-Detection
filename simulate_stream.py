"""
Real-Time Transaction Stream Simulator.
Sends simulated live transactions (routine purchases, velocity spikes, card cloning, and zero-day anomalies)
to the high-performance FastAPI backend to showcase real-time scoring and XAI reason codes.
"""
import time
import requests
import json
import sys

# Ensure UTF-8 output on Windows consoles
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

API_URL = "http://127.0.0.1:8000/api/v1/predict"

TEST_TRANSACTIONS = [
    {
        "id": "TXN_SIM_001_NORMAL",
        "Amount": 425.00,
        "user_id": "USER_1042",
        "distance_prev_km": 1.2,
        "time_delta_sec": 7200.0,
        "velocity_cnt_1h": 1.0,
        "V14": 0.12, "V4": -0.22, "V12": 0.18, "V10": 0.05
    },
    {
        "id": "TXN_SIM_002_VELOCITY_SPIKE",
        "Amount": 18500.00,
        "user_id": "USER_2089",
        "distance_prev_km": 8.5,
        "time_delta_sec": 120.0,
        "velocity_cnt_1h": 7.0,
        "V14": -4.20, "V4": 3.10, "V12": -3.80, "V10": -2.90
    },
    {
        "id": "TXN_SIM_003_IMPOSSIBLE_TRAVEL",
        "Amount": 9500.00,
        "user_id": "USER_3015",
        "distance_prev_km": 1150.0,  # 1,150 km in 15 minutes (Mumbai to Delhi) = 4,600 km/h
        "time_delta_sec": 900.0,
        "velocity_cnt_1h": 2.0,
        "V14": -1.80, "V4": 1.50, "V12": -1.20, "V10": -0.90
    },
    {
        "id": "TXN_SIM_004_ZERO_DAY_ANOMALY",
        "Amount": 34000.00,
        "user_id": "USER_4091",
        "distance_prev_km": 15.0,
        "time_delta_sec": 3600.0,
        "velocity_cnt_1h": 1.0,
        "V14": -5.90, "V4": 4.80, "V12": -5.10, "V10": -4.20, "V17": -4.90
    }
]


def run_stream_simulation():
    print("=" * 75)
    print(" REAL-TIME TRANSACTION STREAM SIMULATION")
    print(f" Target API: {API_URL}")
    print("=" * 75)

    for txn in TEST_TRANSACTIONS:
        print(f"\n[STREAM] Sending {txn['id']} | Amount: ₹{txn['Amount']:,.2f} ...")
        t0 = time.perf_counter()
        try:
            resp = requests.post(API_URL, json=txn, timeout=5)
            client_latency = (time.perf_counter() - t0) * 1000.0

            if resp.status_code == 200:
                data = resp.json()
                print(f"  Decision        : {data['decision']}")
                print(f"  Fraud Risk Prob : {data['fraud_probability']*100:.2f}%")
                print(f"  Server Latency  : {data['inference_latency_ms']} ms (Round-trip: {client_latency:.1f} ms)")
                print(f"  Recommendation  : {data['recommendation']}")
                
                if data.get("reason_codes"):
                    print("  TreeSHAP Reason Codes:")
                    for rc in data["reason_codes"]:
                        print(f"    - [{rc['reason_code']}] {rc['plain_english_explanation']} (Impact: {rc['relative_impact_percent']}%)")
            else:
                print(f"  Error {resp.status_code}: {resp.text}")
        except Exception as e:
            print(f"  Connection error: {e}")
        time.sleep(0.5)


if __name__ == "__main__":
    run_stream_simulation()
