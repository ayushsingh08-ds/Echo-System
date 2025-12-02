# api.py
"""
Flask ingest API for Zeus telemetry.

- POST /ingest
  Accepts a single telemetry sample or an array of samples.
  If header 'x-client-id' is missing: create a new client_id and return it.
  Stores documents in a MongoDB time-series collection 'gpu_metrics' with metadata.client_id.

- GET /metrics/recent?client_id=...&limit=200
- GET /predictions/recent?client_id=...&limit=100
- GET /health

Environment variables:
- MONGO_URI (required): MongoDB Atlas connection string
- MONGO_DB  (optional): database name (default 'zeus_multi')
- TTL_SECONDS (optional): integer seconds to keep telemetry (0 = disabled)
"""
import os
import secrets
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union

from dotenv import load_dotenv
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
from pymongo import MongoClient, ASCENDING, DESCENDING, errors

# Load environment variables from .env file
load_dotenv()

# --- Logging ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("zeus-flask-api")

# --- Configuration from env ---
MONGO_URI = os.getenv("MONGO_URI")
if not MONGO_URI:
    logger.error("MONGO_URI env var not set - exiting")
    raise RuntimeError("MONGO_URI environment variable is required")

MONGO_DB = os.getenv("MONGO_DB", "zeus_multi")
TTL_SECONDS = int(os.getenv("TTL_SECONDS", "0"))

# --- Flask app ---
app = Flask(__name__)
CORS(app)

# --- Mongo client & collections ---
mongo = MongoClient(MONGO_URI)
db = mongo[MONGO_DB]
clients_col = db["clients"]
metrics_col = db["gpu_metrics"]
predictions_col = db["predictions"]
ws_pub_col = db["ws_pub"]

# --- Ensure collections / indexes ---
def ensure_collections_and_indexes():
    try:
        if "gpu_metrics" not in db.list_collection_names():
            logger.info("Creating time-series collection 'gpu_metrics'")
            db.create_collection(
                "gpu_metrics",
                timeseries={"timeField": "timestamp", "metaField": "metadata", "granularity": "seconds"},
            )
        metrics_col.create_index([("metadata.client_id", ASCENDING), ("timestamp", DESCENDING)])
        predictions_col.create_index([("client_id", ASCENDING), ("timestamp", DESCENDING)])
        ws_pub_col.create_index([("client_id", ASCENDING), ("timestamp", DESCENDING)])
        clients_col.create_index([("client_id", ASCENDING)], unique=True)
        if TTL_SECONDS > 0:
            try:
                metrics_col.create_index("timestamp", expireAfterSeconds=TTL_SECONDS)
                logger.info(f"Created TTL index expireAfterSeconds={TTL_SECONDS}")
            except errors.OperationFailure as e:
                logger.warning("Could not create TTL index (maybe not supported on this tier): %s", e)
    except Exception as e:
        logger.exception("Error ensuring collections/indexes: %s", e)

ensure_collections_and_indexes()

# --- Helpers ---
def generate_client_id() -> str:
    return "c_" + secrets.token_urlsafe(16)

def parse_timestamp(value) -> datetime:
    """
    Accept datetime-like string or object. Return tz-aware datetime in UTC.
    """
    if value is None:
        return datetime.now(timezone.utc)
    # If already a datetime (rare because Flask parses JSON into dicts)
    try:
        from dateutil import parser as dateparser  # optional: only used if string parsing needed
    except Exception:
        dateparser = None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    if isinstance(value, str):
        if dateparser:
            try:
                dt = dateparser.parse(value)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                return dt.astimezone(timezone.utc)
            except Exception:
                pass
        # fallback naive parse: try fromisoformat
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.astimezone(timezone.utc)
        except Exception:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)

def resolve_or_create_client(x_client_id: Optional[str]) -> str:
    """
    If x_client_id provided:
      - if exists -> return it
      - else -> abort 401 (avoid silent creation for typos)
    If not provided:
      - create new client doc and return the id
    """
    if x_client_id:
        if clients_col.find_one({"client_id": x_client_id}):
            return x_client_id
        abort(401, description="Invalid client_id")
    # create
    new_id = generate_client_id()
    clients_col.insert_one({"client_id": new_id, "created_at": datetime.now(timezone.utc)})
    logger.info("Created new client_id %s", new_id)
    return new_id

# --- Routes ---
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "time": datetime.now(timezone.utc).isoformat()})

@app.route("/ingest", methods=["POST"])
def ingest():
    # Accept a single dict or a list of dicts
    x_client_id = request.headers.get("x-client-id")
    client_id = resolve_or_create_client(x_client_id)
    payload = request.get_json(force=True, silent=True)
    if payload is None:
        abort(400, description="Invalid JSON payload")
    samples: List[Dict[str, Any]] = []
    if isinstance(payload, list):
        samples = payload
    elif isinstance(payload, dict):
        samples = [payload]
    else:
        abort(400, description="Payload must be object or array of objects")

    docs = []
    for s in samples:
        ts = parse_timestamp(s.get("timestamp") if isinstance(s, dict) else None)
        md = s.get("metadata", {}) if isinstance(s, dict) else {}
        metrics = s.get("metrics", {}) if isinstance(s, dict) else {}
        try:
            gpu_id = int(md.get("gpu_id", 0)) if md.get("gpu_id", None) is not None else 0
        except Exception:
            gpu_id = 0
        doc = {
            "timestamp": ts,
            "metadata": {
                "client_id": client_id,
                "host": md.get("host", "unknown"),
                "gpu_id": gpu_id,
                "gpu_name": md.get("gpu_name"),
            },
            "metrics": metrics,
        }
        docs.append(doc)

    if docs:
        try:
            # insert_many expects dicts with proper datetime objects
            result = metrics_col.insert_many(docs)
            inserted = len(result.inserted_ids)
        except Exception as e:
            logger.exception("DB insert error: %s", e)
            abort(500, description="Database insert error")
    else:
        inserted = 0

    return jsonify({"ok": True, "client_id": client_id, "inserted": inserted})

@app.route("/metrics/recent", methods=["GET"])
def metrics_recent():
    client_id = request.args.get("client_id")
    if not client_id:
        abort(400, description="Missing client_id")
    if not clients_col.find_one({"client_id": client_id}):
        abort(404, description="Unknown client_id")
    try:
        limit = int(request.args.get("limit", "200"))
        limit = max(1, min(limit, 2000))
    except ValueError:
        limit = 200
    cursor = metrics_col.find({"metadata.client_id": client_id}).sort("timestamp", DESCENDING).limit(limit)
    out = []
    for d in cursor:
        d["_id"] = str(d["_id"])
        d["timestamp"] = d.get("timestamp").isoformat() if d.get("timestamp") else None
        out.append(d)
    return jsonify({"metrics": out})

@app.route("/predictions/recent", methods=["GET"])
def predictions_recent():
    client_id = request.args.get("client_id")
    if not client_id:
        abort(400, description="Missing client_id")
    if not clients_col.find_one({"client_id": client_id}):
        abort(404, description="Unknown client_id")
    try:
        limit = int(request.args.get("limit", "100"))
        limit = max(1, min(limit, 2000))
    except ValueError:
        limit = 100
    cursor = predictions_col.find({"client_id": client_id}).sort("timestamp", DESCENDING).limit(limit)
    out = []
    for d in cursor:
        d["_id"] = str(d["_id"])
        d["timestamp"] = d.get("timestamp").isoformat() if d.get("timestamp") else None
        out.append(d)
    return jsonify({"predictions": out})

# --- Main entrypoint for development ---
if __name__ == "__main__":
    # Local debug server (not for production on Render)
    # For production on Render, use: gunicorn api:app -c gunicorn.conf.py
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8000")), debug=True)
