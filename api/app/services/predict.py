"""
Prediction service for Echo System
Integrates with fusion model for ML predictions
"""

import sys
import os
import numpy as np
from pathlib import Path

# Add the project root to the path so we can import fusion
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from fusion.fusion import predict_fusion
except ImportError as e:
    print(f"Warning: Could not import fusion module: {e}")
    predict_fusion = None

def predict_from_window_and_agg(window_data, agg_data):
    """
    Wrapper function to call the fusion model
    
    Args:
        window_data: List of lists representing time series window (60 x 4)
        agg_data: Dictionary of aggregated features
    
    Returns:
        Dictionary with prediction results
    """
    if predict_fusion is None:
        return {
            "error": "Fusion model not available",
            "failure_prob_lstm": 0.5,
            "prob_failure_rf": 0.5,
            "ae_score": 0.5,
            "ae_scaled": 0.5,
            "health_score": 0.5,
            "fused_risk": 0.5
        }
    
    try:
        # Convert window_data to numpy array
        window_array = np.array(window_data, dtype=np.float32)
        
        # Ensure we have the right shape (60, 4)
        if window_array.shape != (60, 4):
            # Pad or truncate as needed
            if len(window_array) < 60:
                # Pad with zeros
                padding = np.zeros((60 - len(window_array), 4), dtype=np.float32)
                window_array = np.vstack([padding, window_array])
            elif len(window_array) > 60:
                # Take the last 60 samples
                window_array = window_array[-60:]
        
        # Call the fusion model
        result = predict_fusion(window_array, agg_data)
        return result
        
    except Exception as e:
        print(f"Error in prediction: {e}")
        # Return safe defaults
        return {
            "error": str(e),
            "failure_prob_lstm": 0.5,
            "prob_failure_rf": 0.5,
            "ae_score": 1.0,
            "ae_scaled": 0.5,
            "health_score": 0.5,
            "fused_risk": 0.5
        }