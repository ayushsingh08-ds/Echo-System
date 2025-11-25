# preprocess.py
import os
from pathlib import Path
import numpy as np
import pandas as pd
import joblib
from tqdm import tqdm
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler, RobustScaler
from config import DATA_CSV, OUT_DIR, RESAMPLE_RULE, WINDOW_SIZE, MIN_VALID_RATIO, AGG_FEATURES

os.makedirs(OUT_DIR, exist_ok=True)

def load_data(csv_path):
    print("Loading CSV:", csv_path)
    df = pd.read_csv(csv_path, parse_dates=["timestamp"])
    # ensure types
    df = df.sort_values(["device_id","timestamp"]).reset_index(drop=True)
    return df

def resample_device(df_dev, resample_rule=RESAMPLE_RULE):
    # set timestamp index for resampling
    df_dev = df_dev.set_index("timestamp")
    # keep device_id and device_type columns by filling forward later
    numeric = df_dev[AGG_FEATURES].resample(resample_rule).mean()
    # preserve device_type and device_id as columns
    numeric["device_id"] = df_dev["device_id"].iloc[0]
    numeric["device_type"] = df_dev["device_type"].iloc[0]
    # label: any label>0 in the window -> keep max
    if "label" in df_dev.columns:
        numeric["label"] = df_dev["label"].resample(resample_rule).max().fillna(0).astype(int)
    else:
        numeric["label"] = 0
    return numeric.reset_index()

def interpolate_and_limit(df_resampled, limit=5):
    # linear interpolate with limit (max consecutive NaNs to fill)
    return df_resampled.interpolate(method="linear", limit=limit, limit_direction="both")

def extract_windows(df_device, window_size=WINDOW_SIZE, min_valid_ratio=MIN_VALID_RATIO):
    """
    Returns:
      windows: numpy array (n_windows, window_size, n_features)
      window_labels: array with label: 0 normal, 1 pre-failure, 2 failure (max in window)
    """
    features = AGG_FEATURES
    arr = df_device[features].values
    labels = df_device["label"].values if "label" in df_device.columns else np.zeros(len(df_device), dtype=int)
    n = len(arr)
    windows = []
    win_labels = []
    for start in range(0, n - window_size + 1):
        window = arr[start:start+window_size]
        lab = labels[start:start+window_size].max()
        # valid ratio
        valid_ratio = np.count_nonzero(~np.isnan(window)) / (window_size * window.shape[1])
        if valid_ratio >= min_valid_ratio:
            windows.append(window)
            win_labels.append(int(lab))
    if not windows:
        return np.empty((0,window_size,len(features))), np.array([])
    return np.stack(windows), np.array(win_labels)

def aggregate_features(df_device):
    """
    Compute aggregated features per window for RandomForest:
    mean, std, min, max, median, skew, kurtosis for each sensor over a window
    Output: DataFrame with one row per resampled timestep (we'll later align to windows)
    """
    # rolling window aggregate (window of WINDOW_SIZE)
    roll = df_device[AGG_FEATURES].rolling(window=WINDOW_SIZE, min_periods=int(WINDOW_SIZE*0.5))
    agg = pd.concat([
        roll.mean().add_suffix("_mean"),
        roll.std().add_suffix("_std"),
        roll.min().add_suffix("_min"),
        roll.max().add_suffix("_max"),
        roll.median().add_suffix("_median")
    ], axis=1)
    agg = agg.reset_index()
    # include device_id, device_type, label
    agg["device_id"] = df_device["device_id"].iloc[0]
    agg["device_type"] = df_device["device_type"].iloc[0]
    if "label" in df_device.columns:
        agg["label"] = df_device["label"].values
    else:
        agg["label"] = 0
    return agg

def main():
    df = load_data(DATA_CSV)
    devices = df["device_id"].unique()
    all_windows = []
    all_labels = []
    agg_rows = []
    # scalers/imputer fit on training set (we fit on concatenated device resampled data)
    concat_for_scaler = []

    for dev in tqdm(devices, desc="Devices"):
        df_dev = df[df["device_id"] == dev].copy()
        df_res = resample_device(df_dev)
        df_res = interpolate_and_limit(df_res, limit=5)
        concat_for_scaler.append(df_res[AGG_FEATURES])
        # extract windows for this device
        windows, win_labels = extract_windows(df_res)
        if windows.size:
            all_windows.append(windows)
            all_labels.append(win_labels)
        # aggregates for RF
        agg = aggregate_features(df_res)
        agg_rows.append(agg)

    if not concat_for_scaler:
        raise RuntimeError("No data loaded for scaler fitting")

    concat_df = pd.concat(concat_for_scaler, axis=0)
    # imputer + scaler (fit jointly)
    imputer = SimpleImputer(strategy="median")
    scaler = RobustScaler()

    concat_imp = imputer.fit_transform(concat_df)
    scaler.fit(concat_imp)

    # save artifacts
    joblib.dump(imputer, os.path.join(OUT_DIR, "imputer.joblib"))
    joblib.dump(scaler, os.path.join(OUT_DIR, "scaler.joblib"))
    print("Saved imputer and scaler to", OUT_DIR)

    # stack windows & labels
    if all_windows:
        windows_arr = np.concatenate(all_windows, axis=0)
        labels_arr = np.concatenate(all_labels, axis=0)
    else:
        windows_arr = np.empty((0, WINDOW_SIZE, len(AGG_FEATURES)))
        labels_arr = np.array([])

    # apply imputation + scaling per timestep feature-wise
    nsamples, wlen, nfeat = windows_arr.shape
    windows_reshaped = windows_arr.reshape(-1, nfeat)
    windows_imp = imputer.transform(windows_reshaped)
    windows_scaled = scaler.transform(windows_imp)
    windows_scaled = windows_scaled.reshape(nsamples, wlen, nfeat)

    np.save(os.path.join(OUT_DIR, "windows.npy"), windows_scaled)
    np.save(os.path.join(OUT_DIR, "labels.npy"), labels_arr)
    print("Saved windows:", windows_scaled.shape, "labels:", labels_arr.shape)

    # save aggregated features for RF (concatenate all devices)
    agg_df = pd.concat(agg_rows, axis=0, ignore_index=True)
    # impute + scale numeric cols in agg_df
    numcols = [c for c in agg_df.columns if any(s in c for s in AGG_FEATURES)]
    agg_df[numcols] = imputer.transform(agg_df[numcols])
    agg_df[numcols] = scaler.transform(agg_df[numcols])
    agg_out = os.path.join(OUT_DIR, "aggregates.csv")
    agg_df.to_csv(agg_out, index=False)
    print("Saved aggregates ->", agg_out)

if __name__ == "__main__":
    main()
