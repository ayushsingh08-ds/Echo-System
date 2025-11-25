# training/train_ae.py
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import numpy as np
from tensorflow.keras.models import Model
from tensorflow.keras.layers import Input, LSTM, RepeatVector, TimeDistributed, Dense
from tensorflow.keras.callbacks import EarlyStopping, ModelCheckpoint
from training.utils import load_windows_labels, reshape_for_model
OUT = "models/ae_model.h5"
os.makedirs(os.path.dirname(OUT), exist_ok=True)

def build_autoencoder(timesteps, features, latent_dim=32):
    inputs = Input(shape=(timesteps, features))
    # Encoder
    x = LSTM(128, return_sequences=True)(inputs)
    x = LSTM(64)(x)
    z = Dense(latent_dim, activation="relu")(x)
    # Decoder
    x = RepeatVector(timesteps)(z)
    x = LSTM(64, return_sequences=True)(x)
    x = LSTM(128, return_sequences=True)(x)
    outputs = TimeDistributed(Dense(features))(x)
    model = Model(inputs, outputs)
    model.compile(optimizer="adam", loss="mse")
    return model

def main():
    X, y = load_windows_labels()
    # select healthy windows only
    mask = (y == 0)
    X_h = X[mask]
    
    # Use only a subset for faster training (10k samples)
    subset_size = min(10000, X_h.shape[0])
    indices = np.random.choice(X_h.shape[0], subset_size, replace=False)
    X_h = X_h[indices]
    
    X_h = reshape_for_model(X_h)
    print("AE training on healthy windows subset:", X_h.shape)
    if X_h.shape[0] < 10:
        raise RuntimeError("Not enough healthy windows to train AE")

    model = build_autoencoder(X_h.shape[1], X_h.shape[2], latent_dim=32)
    cb = EarlyStopping(monitor="val_loss", patience=8, restore_best_weights=True)
    chk = ModelCheckpoint(OUT, monitor="val_loss", save_best_only=True, verbose=1)
    # split manually small validation
    idx = int(0.9 * X_h.shape[0])
    X_tr, X_val = X_h[:idx], X_h[idx:]
    model.fit(X_tr, X_tr, validation_data=(X_val, X_val),
              epochs=2, batch_size=128, callbacks=[cb, chk])
    print("Saved AE to", OUT)

if __name__ == "__main__":
    main()
