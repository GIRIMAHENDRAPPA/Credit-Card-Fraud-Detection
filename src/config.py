"""
Configuration module for Intelligent Credit Card Fraud Detection.
Contains system-wide hyperparameter presets, financial cost matrix defaults,
and operational thresholds.
"""
from pathlib import Path
from pydantic import BaseModel, Field

# Base Directory Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR
MODEL_DIR = BASE_DIR / "saved_models"
LOGS_DIR = BASE_DIR / "logs"

MODEL_DIR.mkdir(parents=True, exist_ok=True)
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class CostMatrixConfig(BaseModel):
    """
    Financial Cost Matrix Parameters (INR).
    FN_cost: Cost of missing a fraudulent transaction (Chargeback loss + processing penalty fee in INR).
    FP_cost: Cost of falsely blocking a legitimate cardholder (Customer friction, contact center verification cost in INR).
    TP_cost: Automated step-up / SMS OTP verification cost in INR.
    TN_cost: Frictionless legitimate transaction processing cost (₹0).
    """
    fn_chargeback_multiplier: float = Field(default=1.0, description="Multiplier for transaction amount lost on False Negative")
    fn_fixed_fee: float = Field(default=1500.0, description="Fixed chargeback processing penalty fee in INR")
    fp_friction_cost: float = Field(default=450.0, description="Customer friction and contact center verification cost in INR")
    tp_investigation_cost: float = Field(default=25.0, description="Automated step-up / SMS OTP verification cost in INR")
    tn_friction_cost: float = Field(default=0.0, description="Zero cost for clean automated pass-through")


class SpatioTemporalConfig(BaseModel):
    """Spatio-Temporal & Travel Velocity Limits."""
    earth_radius_km: float = 6371.0
    impossible_speed_kmh: float = 850.0  # Commercial flight maximum speed threshold
    teleportation_time_sec: float = 300.0  # Time window where distant transactions indicate card cloning
    suspicious_speed_kmh: float = 120.0  # High vehicular speed threshold


class ModelPipelineConfig(BaseModel):
    """Pipeline model hyperparameters and training configs."""
    random_state: int = 42
    test_size: float = 0.2
    val_size: float = 0.1
    
    # Isolation Forest
    iso_n_estimators: int = 150
    iso_contamination: float = 0.01
    
    # Resampling Strategy
    resampling_strategy: str = "smote_undersample"  # 'smote', 'undersample', 'smote_undersample', 'class_weight'
    smote_sampling_strategy: float = 0.25
    undersample_sampling_strategy: float = 0.5
    
    # Stacking
    cv_folds: int = 5
    meta_regularization_c: float = 1.0


class PSIConfig(BaseModel):
    """Population Stability Index (PSI) drift monitoring thresholds."""
    num_bins: int = 10
    stable_threshold: float = 0.10
    moderate_drift_threshold: float = 0.25


# Global instances
COST_CONFIG = CostMatrixConfig()
SPATIO_CONFIG = SpatioTemporalConfig()
MODEL_CONFIG = ModelPipelineConfig()
PSI_CONFIG = PSIConfig()
