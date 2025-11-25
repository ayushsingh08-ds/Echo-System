from fastapi import FastAPI
from .routes import router

app = FastAPI(title="ECHO SYSTEM Ingestion API (Local)")

app.include_router(router, prefix="/api")

@app.get("/")
async def root():
    return {"msg": "ECHO SYSTEM API running"}
