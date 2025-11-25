# fusion/fusion.py
import numpy as np
import pandas as pd
import joblib
from tensorflow.keras.models import load_model
from sklearn.ensemble import RandomForestClassifier

# paths (adjust if different)
LSTM_PATH = "models/lstm_model.h5"
AE_PATH = "models/ae_model.h5"
RF_PATH = "models/rf_model.joblib"
IMPUTER_PATH = "api/preprocessing/artifacts/imputer.joblib"
SCALER_PATH = "api/preprocessing/artifacts/scaler.joblib"

# weights used in paper
W_LSTM = 0.6
W_RF = 0.3
W_AE = 0.1

# load once
_lstm = None
_ae = None
_rf = None
_imputer = None
_scaler = None

def load_all():
    global _lstm, _ae, _rf, _imputer, _scaler
    try:
        if _lstm is None:
            _lstm = load_model(LSTM_PATH, compile=False)
        if _ae is None:
            _ae = load_model(AE_PATH, compile=False)
        if _rf is None:
            _rf = joblib.load(RF_PATH)
        if _imputer is None:
            _imputer = joblib.load(IMPUTER_PATH)
        if _scaler is None:
            _scaler = joblib.load(SCALER_PATH)
    except Exception as e:
        print(f"Warning: Could not load some models: {e}")
        return None, None, _rf, _imputer, _scaler
    return _lstm, _ae, _rf, _imputer, _scaler

def lstm_predict_prob(window):
    """
    window: numpy array shape (T,F) or (1,T,F)
    returns prob_failure (0..1)
    """
    model, *_ = load_all()
    w = np.asarray(window)
    if w.ndim == 2:
        w = w[None, ...]
    p = model.predict(w, verbose=0)
    return float(np.squeeze(p))

def ae_anomaly_score(window):
    """
    returns reconstruction MSE (mean across timesteps/features)
    """
    _, ae, _, _, _ = load_all()
    w = np.asarray(window)
    if w.ndim == 2:
        w = w[None, ...]
    recon = ae.predict(w, verbose=0)
    mse = np.mean((w - recon)**2, axis=(1,2))
    return float(mse[0])

def rf_prob_failure(agg_row):
    """
    agg_row: dict-like of numeric features (same columns used in training)
    returns prob_failure (0..1)
    """
    *_, rf, imputer, scaler = load_all()
    if rf is None:
        return 0.5  # fallback if model not loaded
    
    # Create expected feature names (same as in training)
    feature_names = []
    sensor_names = ["temperature", "vibration", "rpm", "humidity"]
    stat_names = ["mean", "std", "min", "max", "median"]
    for sensor in sensor_names:
        for stat in stat_names:
            feature_names.append(f"{sensor}_{stat}")
    
    # Create feature vector from agg_row
    features = []
    for feat_name in feature_names:
        features.append(agg_row.get(feat_name, 0.0))
    
    X = np.array([features])
    
    try:
        prob = rf.predict_proba(X)[0, 1]
        return float(prob)
    except Exception as e:
        print(f"RF prediction error: {e}")
        return 0.5  # fallback

def predict_fusion(window, agg_row):
    """
    Returns dict: { failure_prob_lstm, prob_failure_rf, ae_score, health_score, fused_risk }
    """
    p_lstm = lstm_predict_prob(window)
    p_rf = rf_prob_failure(agg_row)
    ae_score = ae_anomaly_score(window)
    # scale AE score into 0..1 range (simple heuristic): sigmoid-like mapping
    # you may replace with percentile mapping from validation set
    ae_scaled = 1 / (1 + np.exp(- (ae_score - 0.01) * 100))  # adjust shift/scale if needed
    # health_score is 1 - RF failure prob (so high means healthy)
    health_score = 1.0 - p_rf
    fused = W_LSTM * p_lstm + W_RF * (1 - health_score) + W_AE * ae_scaled
    return {
        "failure_prob_lstm": p_lstm,
        "prob_failure_rf": p_rf,
        "ae_score": ae_score,
        "ae_scaled": float(ae_scaled),
        "health_score": float(health_score),
        "fused_risk": float(fused)
    }

if __name__ == "__main__":
    # quick smoke test (requires models present)
    dummy_win = np.random.randn(60,4).astype("float32")
    # Create realistic dummy aggregated features
    dummy_agg = {
        "temperature_mean": 25.5, "temperature_std": 2.1, "temperature_min": 20.0, "temperature_max": 30.0, "temperature_median": 25.0,
        "vibration_mean": 0.5, "vibration_std": 0.1, "vibration_min": 0.2, "vibration_max": 0.8, "vibration_median": 0.5,
        "rpm_mean": 1500.0, "rpm_std": 100.0, "rpm_min": 1200.0, "rpm_max": 1800.0, "rpm_median": 1500.0,
        "humidity_mean": 60.0, "humidity_std": 5.0, "humidity_min": 50.0, "humidity_max": 70.0, "humidity_median": 60.0
    }
    print("Testing fusion model...")
    try:
        result = predict_fusion(dummy_win, dummy_agg)
        print(f"Fusion prediction: {result}")
    except Exception as e:
        print("Fusion test failed:", e)
