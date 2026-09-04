import numpy as np
from scipy.stats import norm

from qp.utils.maps.options.callput import CallPut
from qp.models.option_type.intrinsic_value import compute_intrinsic_option_value

def bachelier(
    F: np.ndarray, K: float, T: np.ndarray, sigma: float, option_type: CallPut
) -> np.ndarray:

    if sigma < 0:
        raise ValueError("Volatility cannot be negative.")
    
    if np.any(T <= 0):
        raise ValueError("Time to expiry must be greater than zero.")

    if sigma == 0:
        return compute_intrinsic_option_value(F, K, option_type)
    
    std_dev = sigma * np.sqrt(T)
    d = (F - K) / std_dev

    moneyness_value = (F - K) * norm.cdf(d) if option_type == CallPut.CALL else (K - F) * norm.cdf(-d)
    option_value = moneyness_value + std_dev * norm.pdf(d)

    return option_value
