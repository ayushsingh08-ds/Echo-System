# Data and Model Files

**Note**: Large data files and trained models are not included in the repository due to GitHub's file size limits.

## 🔄 **To Regenerate Data and Models**

### **1. Generate Sensor Data**
```bash
cd simulator
python simulator.py
```
This creates `simulated_sensor_data.csv` (332MB) with 2M+ sensor readings.

### **2. Preprocess Data**  
```bash
cd api
python -m preprocessing.preprocess
```
This creates:
- `api/preprocessing/artifacts/windows.npy` (3.6GB) - Time series windows
- `api/preprocessing/artifacts/imputer.joblib` - Data imputation model
- `api/preprocessing/artifacts/scaler.joblib` - Data scaling model
- `api/preprocessing/artifacts/aggregates.csv` - Statistical features

### **3. Train ML Models**
```bash
# Train LSTM model
python training/train_lstm.py

# Train Autoencoder  
python training/train_autoencoder.py

# Train Random Forest
python training/train_rf.py
```
This creates:
- `models/lstm_model.h5` - LSTM time series model
- `models/ae_model.h5` - Autoencoder anomaly detection model  
- `models/rf_model.joblib` - Random Forest classifier

### **4. Test Fusion Model**
```bash
python fusion/fusion.py
```

## ⚡ **Quick Setup Script**

Run this to regenerate all data and models:

```bash
# Generate data
python simulator/simulator.py

# Preprocess 
python -m api.preprocessing.preprocess

# Train models
python training/train_lstm.py
python training/train_autoencoder.py  
python training/train_rf.py

# Test fusion
python fusion/fusion.py
```

## 📊 **Expected File Sizes**
- `simulated_sensor_data.csv`: ~333MB
- `windows.npy`: ~3.6GB  
- `lstm_model.h5`: ~1.5MB
- `ae_model.h5`: ~2.9MB
- `rf_model.joblib`: ~724KB

## 🚀 **Running the System**

Once data is generated:

```bash
# Terminal 1: Start API
cd api && python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2: Start Frontend  
cd Frontend && npm run dev
```

Access dashboard at: `http://localhost:3000`