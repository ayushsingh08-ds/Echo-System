# (optional place for DB-related constants / helper classes)
from typing import Dict, Any

def sensor_doc_from_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    # prepare Mongo-friendly document (convert datetimes if needed)
    doc = payload.copy()
    # Keep timestamp as-is (Motor will accept Python datetime)
    return doc
