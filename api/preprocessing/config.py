# simple config
DATA_CSV = "../../simulator/simulated_sensor_data.csv"   # input from simulator
OUT_DIR = "./artifacts"
RESAMPLE_RULE = "1T"   # 1 minute
WINDOW_SIZE = 60       # 60 timesteps (for LSTM/AE)
MIN_VALID_RATIO = 0.8  # minimum non-missing ratio per window
AGG_FEATURES = ["temperature","vibration","rpm","humidity"]
