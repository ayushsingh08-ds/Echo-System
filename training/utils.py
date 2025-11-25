# training/utils.py
import numpy as np
import joblib
from sklearn.model_selection import train_test_split

def load_windows_labels(path_windows="api/preprocessing/artifacts/windows.npy",
                        path_labels="api/preprocessing/artifacts/labels.npy"):
    X = np.load(path_windows)  # shape (N, T, F)
    y = np.load(path_labels)   # shape (N,)
    return X, y

def reshape_for_model(X):
    # ensures float32 and shapes ok
    return X.astype("float32")

def load_scalers(imputer_path="api/preprocessing/artifacts/imputer.joblib",
                 scaler_path="api/preprocessing/artifacts/scaler.joblib"):
    imputer = joblib.load(imputer_path)
    scaler = joblib.load(scaler_path)
    return imputer, scaler

def split_train_val(X, y, test_size=0.2, random_state=42, stratify=True):
    if stratify:
        return train_test_split(X, y, test_size=test_size, random_state=random_state, stratify=(y>0).astype(int))
    return train_test_split(X, y, test_size=test_size, random_state=random_state)
