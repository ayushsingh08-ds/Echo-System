"""
Script to seed the database with sample sensor data for frontend testing
"""

import asyncio
import random
import datetime
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ServerSelectionTimeoutError

async def seed_data():
    """Add sample sensor data to MongoDB"""
    
    # Connect to MongoDB
    client = AsyncIOMotorClient("mongodb://localhost:27017")
    db = client["echo_system"]
    collection = db["sensors"]
    
    try:
        # Test connection
        await client.admin.command('ping')
        print("Connected to MongoDB successfully")
    except ServerSelectionTimeoutError:
        print("Error: Could not connect to MongoDB. Make sure MongoDB is running on localhost:27017")
        return
    
    # Device IDs to create data for
    device_ids = ["device_001", "device_002", "device_003", "pump_alpha", "motor_beta"]
    
    # Generate sample data for the last hour
    now = datetime.datetime.utcnow()
    documents = []
    
    for device_id in device_ids:
        # Create 60 data points (one per minute for the last hour)
        for i in range(60):
            timestamp = now - datetime.timedelta(minutes=59-i)
            
            # Generate realistic sensor data with some variation per device
            base_temp = 25.0 + (hash(device_id) % 10)  # Device-specific base temperature
            base_rpm = 1500 + (hash(device_id) % 500)  # Device-specific base RPM
            
            # Add some realistic patterns and noise
            time_factor = i / 60.0  # 0 to 1 over the hour
            
            # Some devices might be showing degradation patterns
            if device_id in ["pump_alpha", "motor_beta"]:
                # These devices show increasing temperature and vibration over time
                temp_trend = time_factor * 5  # Temperature rises 5°C over the hour
                vib_trend = time_factor * 0.3  # Vibration increases
            else:
                temp_trend = 0
                vib_trend = 0
            
            doc = {
                "device_id": device_id,
                "timestamp": timestamp.isoformat(),
                "temperature": base_temp + temp_trend + random.gauss(0, 1.5),
                "vibration": 0.2 + vib_trend + random.gauss(0, 0.05),
                "rpm": base_rpm + random.gauss(0, 50),
                "humidity": 60 + random.gauss(0, 5),
                # Optional metadata
                "location": f"Factory Floor {(hash(device_id) % 5) + 1}",
                "equipment_type": "Industrial Motor" if "motor" in device_id else "Pump" if "pump" in device_id else "Generic Sensor"
            }
            documents.append(doc)
    
    # Insert all documents
    try:
        result = await collection.insert_many(documents)
        print(f"Inserted {len(result.inserted_ids)} sensor readings")
        print(f"Sample devices: {device_ids}")
        
        # Show some stats
        for device_id in device_ids[:2]:  # Show stats for first 2 devices
            count = await collection.count_documents({"device_id": device_id})
            latest = await collection.find_one({"device_id": device_id}, sort=[("timestamp", -1)])
            print(f"  {device_id}: {count} records, latest temp: {latest['temperature']:.1f}°C")
            
    except Exception as e:
        print(f"Error inserting data: {e}")
    
    await client.close()
    print("Database seeding complete!")

if __name__ == "__main__":
    asyncio.run(seed_data())