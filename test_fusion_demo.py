#!/usr/bin/env python3
"""
Demo script showing how to use the fusion model for predictive maintenance
"""

import numpy as np
import pandas as pd
from fusion.fusion import predict_fusion

def create_sample_data():
    """Create sample sensor data for testing"""
    
    # Simulate 60 timesteps of 4 sensor readings (normal operation)
    normal_window = np.array([
        [25 + np.random.normal(0, 1), 0.3 + np.random.normal(0, 0.05), 1500 + np.random.normal(0, 50), 60 + np.random.normal(0, 3)]
        for _ in range(60)
    ], dtype=np.float32)
    
    # Simulate anomalous data (equipment degradation)
    anomalous_window = np.array([
        [30 + np.random.normal(0, 2), 0.8 + np.random.normal(0, 0.1), 1200 + np.random.normal(0, 100), 80 + np.random.normal(0, 5)]
        for _ in range(60)
    ], dtype=np.float32)
    
    return normal_window, anomalous_window

def calculate_aggregates(window):
    """Calculate aggregated features from window data"""
    sensor_names = ["temperature", "vibration", "rpm", "humidity"]
    aggregates = {}
    
    for i, sensor in enumerate(sensor_names):
        data = window[:, i]
        aggregates[f"{sensor}_mean"] = float(np.mean(data))
        aggregates[f"{sensor}_std"] = float(np.std(data))
        aggregates[f"{sensor}_min"] = float(np.min(data))
        aggregates[f"{sensor}_max"] = float(np.max(data))
        aggregates[f"{sensor}_median"] = float(np.median(data))
    
    return aggregates

def main():
    print("Echo System Fusion Model Demo")
    print("=" * 40)
    
    # Generate test data
    normal_data, anomalous_data = create_sample_data()
    
    # Test 1: Normal operation
    print("\n1. Testing Normal Operation:")
    print(f"   Temperature: {normal_data[:, 0].mean():.1f}°C ± {normal_data[:, 0].std():.1f}")
    print(f"   Vibration: {normal_data[:, 1].mean():.2f} ± {normal_data[:, 1].std():.2f}")
    print(f"   RPM: {normal_data[:, 2].mean():.0f} ± {normal_data[:, 2].std():.0f}")
    print(f"   Humidity: {normal_data[:, 3].mean():.1f}% ± {normal_data[:, 3].std():.1f}")
    
    normal_agg = calculate_aggregates(normal_data)
    normal_result = predict_fusion(normal_data, normal_agg)
    
    print(f"\n   Results:")
    print(f"   - LSTM Failure Prob: {normal_result['failure_prob_lstm']:.1%}")
    print(f"   - RF Failure Prob: {normal_result['prob_failure_rf']:.1%}")
    print(f"   - Anomaly Score: {normal_result['ae_score']:.1%}")
    print(f"   - Health Score: {normal_result['health_score']:.1%}")
    print(f"   - **FUSED RISK: {normal_result['fused_risk']:.1%}**")
    
    # Test 2: Anomalous operation
    print("\n2. Testing Anomalous Operation:")
    print(f"   Temperature: {anomalous_data[:, 0].mean():.1f}°C ± {anomalous_data[:, 0].std():.1f}")
    print(f"   Vibration: {anomalous_data[:, 1].mean():.2f} ± {anomalous_data[:, 1].std():.2f}")
    print(f"   RPM: {anomalous_data[:, 2].mean():.0f} ± {anomalous_data[:, 2].std():.0f}")
    print(f"   Humidity: {anomalous_data[:, 3].mean():.1f}% ± {anomalous_data[:, 3].std():.1f}")
    
    anomalous_agg = calculate_aggregates(anomalous_data)
    anomalous_result = predict_fusion(anomalous_data, anomalous_agg)
    
    print(f"\n   Results:")
    print(f"   - LSTM Failure Prob: {anomalous_result['failure_prob_lstm']:.1%}")
    print(f"   - RF Failure Prob: {anomalous_result['prob_failure_rf']:.1%}")
    print(f"   - Anomaly Score: {anomalous_result['ae_score']:.1%}")
    print(f"   - Health Score: {anomalous_result['health_score']:.1%}")
    print(f"   - **FUSED RISK: {anomalous_result['fused_risk']:.1%}**")
    
    # Risk assessment
    print(f"\n3. Risk Assessment:")
    normal_risk = normal_result['fused_risk']
    anomaly_risk = anomalous_result['fused_risk']
    
    def risk_level(risk_score):
        if risk_score < 0.3:
            return "LOW", "🟢"
        elif risk_score < 0.6:
            return "MEDIUM", "🟡"
        else:
            return "HIGH", "🔴"
    
    normal_level, normal_icon = risk_level(normal_risk)
    anomaly_level, anomaly_icon = risk_level(anomaly_risk)
    
    print(f"   Normal Operation: {normal_icon} {normal_level} RISK ({normal_risk:.1%})")
    print(f"   Anomalous Operation: {anomaly_icon} {anomaly_level} RISK ({anomaly_risk:.1%})")
    
    print(f"\n4. Model Performance Summary:")
    print(f"   - LSTM Weight: 60% (time series patterns)")
    print(f"   - Random Forest Weight: 30% (statistical features)")
    print(f"   - Autoencoder Weight: 10% (anomaly detection)")
    print(f"   - Ensemble provides robust failure prediction")

if __name__ == "__main__":
    main()