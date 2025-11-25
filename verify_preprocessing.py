import numpy as np
import matplotlib.pyplot as plt

# Load the preprocessed data
print("Loading preprocessed data...")
w = np.load("api/preprocessing/artifacts/windows.npy")
labels = np.load("api/preprocessing/artifacts/labels.npy")

print("Windows shape:", w.shape)
print("Label distribution:", np.unique(labels, return_counts=True))

# Print some additional info
print(f"\nData summary:")
print(f"- Total windows: {w.shape[0]:,}")
print(f"- Window length: {w.shape[1]} timesteps") 
print(f"- Features per timestep: {w.shape[2]}")
print(f"- Total data points: {w.size:,}")
print(f"- Memory usage: {w.nbytes / (1024**3):.2f} GB")

# Check for any NaN values
nan_count = np.isnan(w).sum()
print(f"- NaN values: {nan_count}")

# Show label meanings
label_counts = np.unique(labels, return_counts=True)
label_names = {0: "Normal", 1: "Pre-failure", 2: "Failure"}
print(f"\nLabel breakdown:")
for label, count in zip(label_counts[0], label_counts[1]):
    percentage = (count / len(labels)) * 100
    print(f"- {label_names.get(label, f'Unknown({label})')}: {count:,} ({percentage:.1f}%)")

# Plot a sample window
print(f"\nPlotting sample window (first window)...")
plt.figure(figsize=(12, 8))

feature_names = ["Temperature", "Vibration", "RPM", "Humidity"]
colors = ['red', 'blue', 'green', 'orange']

for i, (name, color) in enumerate(zip(feature_names, colors)):
    plt.subplot(2, 2, i+1)
    plt.plot(w[0][:, i], color=color, linewidth=1.5)
    plt.title(f"{name} (Window 0, Label: {label_names.get(labels[0], 'Unknown')})")
    plt.xlabel("Timestep")
    plt.ylabel("Scaled Value")
    plt.grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig("sample_window_plot.png", dpi=150, bbox_inches='tight')
plt.show()

print("Verification complete! Sample plot saved as 'sample_window_plot.png'")