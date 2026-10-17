import math
import numpy as np

def safe_float(val, default:float=0.0) -> float:
    """Safely converts value to float, handling None, masked arrays, and NaN."""
    if val is None or np.ma.is_masked(val):
        return default
    try:
        f = float(val)
        return default if math.isnan(f) else f
    except (ValueError, TypeError):
        return default