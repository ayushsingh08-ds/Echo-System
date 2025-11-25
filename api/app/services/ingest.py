from typing import List
from ..schemas import SensorPayload
from .db import get_collection

async def insert_batch(payloads: List[SensorPayload]) -> int:
    coll = get_collection()
    docs = [p.dict() for p in payloads]
    res = await coll.insert_many(docs)
    return len(res.inserted_ids)
