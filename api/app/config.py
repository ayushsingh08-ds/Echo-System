import os

class Settings:
    MONGO_URI: str = os.getenv("MONGO_URI", "mongodb://localhost:27017")
    MONGO_DB: str = os.getenv("MONGO_DB", "pdm")
    MONGO_COLL: str = os.getenv("MONGO_COLL", "sensor_data")

settings = Settings()
