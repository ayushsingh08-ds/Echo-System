# simulator.py
import json
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import uuid
import random
from tqdm import tqdm
import os

# Optional MongoDB
try:
    from pymongo import MongoClient
    MONGO_AVAILABLE = True
except Exception:
    MONGO_AVAILABLE = False

ROOT = os.path.dirname(__file__)
PROFILE_PATH = os.path.join(ROOT, 'device_profiles.json')

# --- config
with open(PROFILE_PATH, 'r') as f:
    PROFILE = json.load(f)

DEVICE_TYPES = PROFILE['device_types']
SAMPLING_INTERVAL_RANGE = PROFILE.get('sampling_interval_sec', [30,60])
MISSING_PROB = PROFILE.get('missing_prob', 0.03)
JITTER_SECONDS = PROFILE.get('jitter_seconds', 5)
FAIL_PROB_DAY = PROFILE.get('failure_probability_per_device_per_day', 0.02)

# simulation params
NUM_DEVICES = 200
DAYS = 7
START_TS = datetime.utcnow() - timedelta(days=DAYS)
END_TS = START_TS + timedelta(days=DAYS)

OUT_CSV = os.path.join(ROOT, 'simulated_sensor_data.csv')

# Mongo config (optional) - set MONGO_URI env var to use
MONGO_URI = os.getenv('MONGO_URI', None)
MONGO_DB = os.getenv('MONGO_DB', 'pdm_sim')
MONGO_COLL = os.getenv('MONGO_COLL', 'sensor_data')

def sample_interval():
    return random.randint(SAMPLING_INTERVAL_RANGE[0], SAMPLING_INTERVAL_RANGE[1])

def generate_device(device_id, device_type):
    """Generate timeseries for a single device with possible failure events."""
    rows = []
    ts = START_TS
    # decide if this device will have failure events
    # Poisson-like: chance per day
    will_fail = random.random() < (1 - (1 - FAIL_PROB_DAY)**DAYS)
    # choose a failure time if will_fail
    fail_time = None
    if will_fail:
        fail_time = START_TS + timedelta(seconds=random.randint(0, int((END_TS-START_TS).total_seconds())))
    while ts <= END_TS:
        interval = sample_interval()
        # jitter timestamp +/- JITTER_SECONDS
        jitter = random.randint(-JITTER_SECONDS, JITTER_SECONDS)
        ts_effective = ts + timedelta(seconds=jitter)
        # get base signals
        base_temp = device_type['temp_base']
        base_vib = device_type['vib_base']
        base_rpm = device_type['rpm_base']
        # add normal noise
        temp = np.random.normal(base_temp, 0.5)
        vib = np.abs(np.random.normal(base_vib, 0.02))
        rpm = max(0, np.random.normal(base_rpm, 50))
        humidity = np.clip(np.random.normal(40, 5), 10, 90)
        label = 0

        # if near failure, inject ramp signal (10-120 minutes before fail)
        if fail_time:
            delta = (fail_time - ts_effective).total_seconds()
            # pre-failure window: from 10 min to 2 hours (600 to 7200 sec)
            if 0 <= delta <= 7200:
                # ramp intensity depending on closeness
                factor = (7200 - delta) / 7200  # 0->1 as it approaches
                temp += 5 * factor + np.random.normal(0,0.3)
                vib += 0.5 * factor + np.random.normal(0,0.02)
                rpm -= 300 * factor + np.random.normal(0,20)
                # mark pre-failure label (1 == pre-failure within horizon)
                label = 1
            # if exactly failure time, label fail event
            if abs(delta) < interval:
                label = 2  # actual failure event

        # apply missingness
        if random.random() < MISSING_PROB:
            # make one of the sensors missing at random
            choice = random.choice(['temp','vib','rpm','humidity'])
            if choice == 'temp': temp = np.nan
            if choice == 'vib': vib = np.nan
            if choice == 'rpm': rpm = np.nan
            if choice == 'humidity': humidity = np.nan

        row = {
            'device_id': device_id,
            'device_type': device_type['name'],
            'timestamp': ts_effective.isoformat(),
            'temperature': float(temp) if not np.isnan(temp) else None,
            'vibration': float(vib) if not np.isnan(vib) else None,
            'rpm': float(rpm) if not np.isnan(rpm) else None,
            'humidity': float(humidity) if not np.isnan(humidity) else None,
            'label': label  # 0 normal, 1 pre-failure, 2 failure
        }
        rows.append(row)
        ts = ts + timedelta(seconds=interval)
    return rows

def main(save_csv=True, push_mongo=False, pretty_progress=True):
    all_rows = []
    device_ids = []
    # create devices
    for i in range(NUM_DEVICES):
        dt = random.choice(DEVICE_TYPES)
        dev_id = f"{dt['name']}_{i}_{str(uuid.uuid4())[:8]}"
        device_ids.append((dev_id, dt))

    iterator = device_ids
    if pretty_progress:
        iterator = tqdm(device_ids, desc='Simulating devices')

    for dev_id, dtype in iterator:
        rows = generate_device(dev_id, dtype)
        all_rows.extend(rows)

    df = pd.DataFrame(all_rows)
    # sort by timestamp
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(['device_id', 'timestamp']).reset_index(drop=True)

    if save_csv:
        df.to_csv(OUT_CSV, index=False)
        print(f"Saved {len(df):,} rows -> {OUT_CSV}")

    if push_mongo and MONGO_AVAILABLE and MONGO_URI:
        client = MongoClient(MONGO_URI)
        coll = client[MONGO_DB][MONGO_COLL]
        # convert timestamps to ISODate
        records = df.to_dict('records')
        for r in records:
            r['timestamp'] = pd.to_datetime(r['timestamp'])
        coll.insert_many(records)
        print(f"Pushed {len(records):,} docs to {MONGO_URI}/{MONGO_DB}/{MONGO_COLL}")

    return df

if __name__ == "__main__":
    df = main(save_csv=True, push_mongo=False)
