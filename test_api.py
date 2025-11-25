"""
Simple test API server to verify frontend integration
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import random
import datetime

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health():
    return {"status": "ok"}

@app.get("/api/devices")
async def get_devices():
    return ["device_001", "device_002", "device_003", "pump_alpha", "motor_beta"]

@app.get("/api/latest/{device_id}")
async def get_latest(device_id: str):
    # Generate fake sensor data for testing
    now = datetime.datetime.now().isoformat()
    return {
        "_id": "test_id",
        "device_id": device_id,
        "timestamp": now,
        "temperature": 25 + random.gauss(0, 2),
        "vibration": 0.3 + random.gauss(0, 0.1), 
        "rpm": 1500 + random.gauss(0, 100),
        "humidity": 60 + random.gauss(0, 5)
    }

@app.post("/api/predict/fusion")
async def predict_fusion(payload: dict):
    # Return fake fusion predictions for testing
    return {
        "failure_prob_lstm": random.uniform(0.01, 0.8),
        "prob_failure_rf": random.uniform(0.01, 0.6),
        "ae_score": random.uniform(100, 50000),
        "ae_scaled": random.uniform(0.1, 1.0),
        "health_score": random.uniform(0.8, 1.0),
        "fused_risk": random.uniform(0.1, 0.7)
    }

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)