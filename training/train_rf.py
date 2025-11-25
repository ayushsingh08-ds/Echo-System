# training/train_rf.py
import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, roc_auc_score

OUT = "models/rf_model.joblib"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

def create_aggregated_features(windows, labels):
    """Create aggregated features from time series windows for Random Forest"""
    print("Creating aggregated features from windows...")
    n_samples, window_len, n_features = windows.shape
    
    # Feature names
    feature_names = ["temperature", "vibration", "rpm", "humidity"]
    
    # Initialize feature matrix
    agg_features = []
    
    # Compute aggregated statistics for each window
    for i in range(n_samples):
        window = windows[i]  # shape: (window_len, n_features)
        
        features = []
        for f in range(n_features):
            series = window[:, f]
            # Remove NaN values for calculation
            valid_series = series[~np.isnan(series)]
            
            if len(valid_series) > 0:
                # Statistical features
                features.extend([
                    np.mean(valid_series),      # mean
                    np.std(valid_series),       # std
                    np.min(valid_series),       # min
                    np.max(valid_series),       # max
                    np.median(valid_series),    # median
                ])
            else:
                # If all values are NaN, use zeros
                features.extend([0.0, 0.0, 0.0, 0.0, 0.0])
        
        agg_features.append(features)
    
    # Create column names
    stat_names = ["mean", "std", "min", "max", "median"]
    columns = []
    for feat_name in feature_names:
        for stat_name in stat_names:
            columns.append(f"{feat_name}_{stat_name}")
    
    # Convert to DataFrame
    df = pd.DataFrame(agg_features, columns=columns)
    df["label"] = labels
    
    print(f"Created {len(columns)} aggregated features from {n_samples} windows")
    return df

def main():
    # Load preprocessed data
    print("Loading preprocessed data...")
    windows = np.load("api/preprocessing/artifacts/windows.npy")
    labels = np.load("api/preprocessing/artifacts/labels.npy")
    
    print(f"Loaded windows: {windows.shape}, labels: {labels.shape}")
    
    # Use a subset for faster training (50k samples)
    subset_size = min(50000, len(windows))
    indices = np.random.choice(len(windows), subset_size, replace=False)
    windows_subset = windows[indices]
    labels_subset = labels[indices]
    
    print(f"Using subset of {subset_size} samples for training")
    
    # Create aggregated features
    df = create_aggregated_features(windows_subset, labels_subset)
    
    # Prepare features and target
    ignore = ["label"]
    X_cols = [c for c in df.columns if c not in ignore]
    
    # Binary target (failure vs normal)
    y = (df["label"] > 0).astype(int)
    X = df[X_cols].fillna(0)
    
    print(f"Feature matrix shape: {X.shape}")
    print(f"Label distribution: {np.bincount(y)}")
    
    # Train-test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, stratify=y, random_state=42)
    
    # Train Random Forest
    print("Training Random Forest...")
    clf = RandomForestClassifier(n_estimators=100, n_jobs=-1, class_weight="balanced", random_state=42)
    clf.fit(X_train, y_train)
    
    # Evaluate
    preds = clf.predict_proba(X_test)[:,1]
    print(f"AUC: {roc_auc_score(y_test, preds):.4f}")
    print(classification_report(y_test, (preds>0.5).astype(int)))
    
    # Feature importance
    feature_importance = pd.DataFrame({
        'feature': X_cols,
        'importance': clf.feature_importances_
    }).sort_values('importance', ascending=False)
    
    print("\nTop 10 most important features:")
    print(feature_importance.head(10))
    
    # Save model
    joblib.dump(clf, OUT)
    print(f"Saved RF to {OUT}")

if __name__ == "__main__":
    main()
