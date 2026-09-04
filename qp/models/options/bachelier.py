import numpy as np
from scipy.stats import norm

from qp.utils.maps.options.callput import CallPut


def bachelier(
    F: np.ndarray, K: float, T: np.ndarray, sigma: float, option_type: CallPut
) -> np.ndarray:

    if sigma < 0:
        raise ValueError("Volatility cannot be negative.")
    
    if np.any(T <= 0):
        raise ValueError("Time to expiry must be greater than zero.")

    if sigma == 0:
        return (
            np.maximum(F - K, 0)
            if option_type == CallPut.CALL
            else np.maximum(K - F, 0)
        )
    
    std_dev = sigma * np.sqrt(T)
    d = (F - K) / std_dev

    moneyness_value = (F - K) * norm.cdf(d) if option_type == CallPut.CALL else (K - F) * norm.cdf(-d)
    option_value = moneyness_value + std_dev * norm.pdf(d)

    return option_value
