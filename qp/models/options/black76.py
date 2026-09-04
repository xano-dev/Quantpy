import numpy as np
from scipy.stats import norm

from qp.models.options.intrinsic_value import compute_intrinsic_option_value
from qp.utils.maps.options.callput import CallPut


def black76(
    F: np.ndarray, K: float, T: np.ndarray, sigma: float, option_type: CallPut, displacement: float
) -> np.ndarray:
    
    shifted_F = F + displacement
    shifted_K = K + displacement

    if np.any(shifted_F <= 0):
        raise ValueError("F + displacement must be greater than zero.")

    if shifted_K <= 0:
        raise ValueError("K + displacement must be greater than zero.")
    
    if sigma < 0:
        raise ValueError("Volatility cannot be negative.")
    
    if np.any(T <= 0):
        raise ValueError("Time to expiry must be greater than zero.")

    if sigma == 0:
        return compute_intrinsic_option_value(F, K, option_type)

    d2 = (np.log(shifted_F / shifted_K) - (sigma**2 / 2) * T) / (sigma * np.sqrt(T))

    d1 = d2 + (sigma * np.sqrt(T))

    return (
        shifted_F * norm.cdf(d1) - shifted_K * norm.cdf(d2)
        if option_type == CallPut.CALL
        else shifted_K * norm.cdf(-d2) - shifted_F * norm.cdf(-d1)
    )
