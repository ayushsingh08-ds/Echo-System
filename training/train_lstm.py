# training/train_lstm.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense, Dropout, BatchNormalization
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from tensorflow.keras.optimizers import Adam
import numpy as np
from training.utils import load_windows_labels, reshape_for_model, split_train_val

OUT = "models/lstm_model.h5"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

def build_lstm(input_shape):
    model = Sequential([
        LSTM(128, input_shape=input_shape, return_sequences=True),
        BatchNormalization(),
        Dropout(0.2),
        LSTM(64),
        BatchNormalization(),
        Dropout(0.2),
        Dense(32, activation="relu"),
        Dense(1, activation="sigmoid")
    ])
    model.compile(optimizer=Adam(learning_rate=1e-3), loss="binary_crossentropy", metrics=["AUC"])
    return model

def main():
    X, y = load_windows_labels()
    # construct binary labels: failure (label>0) -> 1, else 0
    y_bin = (y > 0).astype(int)
    X = reshape_for_model(X)
    X_train, X_val, y_train, y_val = split_train_val(X, y_bin, test_size=0.2)
    print("Shapes:", X_train.shape, X_val.shape, y_train.shape, y_val.shape)

    model = build_lstm(input_shape=(X.shape[1], X.shape[2]))
    cb_early = EarlyStopping(monitor="val_auc", patience=8, mode="max", restore_best_weights=True)
    cb_chk = ModelCheckpoint(OUT, monitor="val_auc", mode="max", save_best_only=True, verbose=1)
    model.fit(X_train, y_train, validation_data=(X_val, y_val),
              epochs=1, batch_size=128, callbacks=[cb_early, cb_chk])
    print("Saved LSTM to", OUT)

if __name__ == "__main__":
    main()
