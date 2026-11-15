"""
Pydantic Schemas for High-Performance Fraud Detection FastAPI Backend.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class TransactionInput(BaseModel):
    id: Optional[str] = Field(default="TXN_001", description="Unique transaction ID")
    Amount: float = Field(..., ge=0.0, description="Transaction monetary value in currency units")
    
    # Latent PCA attributes V1 through V28
    V1: float = 0.0
    V2: float = 0.0
    V3: float = 0.0
    V4: float = 0.0
    V5: float = 0.0
    V6: float = 0.0
    V7: float = 0.0
    V8: float = 0.0
    V9: float = 0.0
    V10: float = 0.0
    V11: float = 0.0
    V12: float = 0.0
    V13: float = 0.0
    V14: float = 0.0
    V15: float = 0.0
    V16: float = 0.0
    V17: float = 0.0
    V18: float = 0.0
    V19: float = 0.0
    V20: float = 0.0
    V21: float = 0.0
    V22: float = 0.0
    V23: float = 0.0
    V24: float = 0.0
    V25: float = 0.0
    V26: float = 0.0
    V27: float = 0.0
    V28: float = 0.0

    # Optional Spatio-Temporal and behavioral attributes
    user_id: Optional[str] = Field(default=None, description="Cardholder identifier")
    timestamp: Optional[str] = Field(default=None, description="ISO timestamp of transaction")
    lat: Optional[float] = Field(default=None, description="Terminal latitude")
    lon: Optional[float] = Field(default=None, description="Terminal longitude")
    distance_prev_km: Optional[float] = Field(default=0.0, description="Geodesic distance to cardholder's prior transaction")
    time_delta_sec: Optional[float] = Field(default=3600.0, description="Elapsed time in seconds since prior transaction")
    velocity_cnt_1h: Optional[float] = Field(default=1.0, description="Transaction frequency in past 1 hour")
    velocity_amt_1h: Optional[float] = Field(default=None, description="Total spend in past 1 hour")
    velocity_cnt_24h: Optional[float] = Field(default=1.0, description="Transaction frequency in past 24 hours")
    velocity_amt_24h: Optional[float] = Field(default=None, description="Total spend in past 24 hours")


class TransactionBatchInput(BaseModel):
    transactions: List[TransactionInput]


class ReasonCodeResponse(BaseModel):
    rank: int
    feature: str
    feature_value: float
    shap_attribution: float
    relative_impact_percent: float
    reason_code: str
    plain_english_explanation: str


class PredictionResponse(BaseModel):
    transaction_id: str
    fraud_probability: float
    decision: str
    recommendation: str
    status_color: str
    unsupervised_anomaly_score: float
    base_model_probabilities: Dict[str, float]
    spatio_temporal_audit: Optional[Dict[str, Any]] = None
    reason_codes: Optional[List[ReasonCodeResponse]] = None
    inference_latency_ms: float


class BatchPredictionResponse(BaseModel):
    total_processed: int
    flagged_declines: int
    step_up_challenges: int
    frictionless_approved: int
    predictions: List[PredictionResponse]


class DriftReportResponse(BaseModel):
    overall_status: str
    max_psi: float
    requires_retraining_alert: bool
    drift_summary: str
    drifted_features: List[str]
    moderate_features: List[str]
    feature_metrics: Dict[str, Any]
