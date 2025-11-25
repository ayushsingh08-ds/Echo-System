from fastapi import APIRouter, HTTPException
from typing import List
from .schemas import SensorPayload, IngestResponse
from .services.ingest import insert_batch
from .services.db import get_collection
from .config import settings
from fastapi import Body
from typing import Dict, Any
from app.services.predict import predict_from_window_and_agg

router = APIRouter()

@router.get("/health")
async def health():
    try:
        coll = get_collection()
        await coll.database.command("ping")
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest", response_model=IngestResponse)
async def ingest(payloads: List[SensorPayload]):
    if not payloads:
        raise HTTPException(status_code=400, detail="Empty payload")
    count = await insert_batch(payloads)
    return {"inserted_count": count}

@router.get("/devices")
async def get_devices():
    """Get list of unique device IDs from the database"""
    try:
        coll = get_collection()
        devices = await coll.distinct("device_id")
        return devices
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/latest/{device_id}")
async def latest(device_id: str):
    coll = get_collection()
    doc = await coll.find_one({"device_id": device_id}, sort=[("timestamp", -1)])
    if not doc:
        raise HTTPException(status_code=404, detail="Not found")
    doc["_id"] = str(doc["_id"])
    return doc
# new endpoint: predict fusion from one window + aggregate
@router.post("/predict/fusion")
async def predict_fusion_endpoint(payload: Dict[str, Any] = Body(...)):
    """
    payload = {
      "window": [[...], ...],   # shape (60, num_features)
      "agg": { ... }            # numeric aggregate features row (dict)
    }
    returns fused scores
    """
    try:
        window = payload.get("window")
        agg = payload.get("agg")
        if window is None or agg is None:
            raise HTTPException(status_code=400, detail="Both 'window' and 'agg' required")
        res = predict_from_window_and_agg(window, agg)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# add small convenience endpoint for LSTM only
@router.post("/predict/lstm")
async def predict_lstm_only(payload: Dict[str, Any] = Body(...)):
    window = payload.get("window")
    if window is None:
        raise HTTPException(status_code=400, detail="window required")
    try:
        from fusion.fusion import lstm_predict_prob
        return {"failure_prob_lstm": lstm_predict_prob(window)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))