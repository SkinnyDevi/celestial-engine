import math
import numpy as np

def safe_float(val, default: float = 0.0) -> float:
    """Safely converts value to float, handling None, masked arrays, Astropy Quantities, and NaN."""
    if val is None:
        return default
    if hasattr(val, 'mask') and bool(np.any(val.mask)):
        return default
    if np.ma.is_masked(val):
        return default
    # Handle Astropy Quantity / MaskedQuantity
    if hasattr(val, 'value'):
        val = val.value
        if hasattr(val, 'mask') and bool(np.any(val.mask)):
            return default
    try:
        f = float(val)
        return default if math.isnan(f) else f
    except (ValueError, TypeError):
        return default