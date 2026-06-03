from scipy.stats import norm
import numpy as np
from qp.utils.maps.options.callput import CallPut


def black76(
    F: np.ndarray, K: float, T: np.ndarray, sigma: float, option_type: CallPut
) -> float:

    if sigma == 0:
        return (
            np.maximum(F - K, 0)
            if option_type == CallPut.CALL
            else np.maximum(K - F, 0)
        )

    d2 = (np.log(F / K) - (sigma**2 / 2) * T) / (sigma * np.sqrt(T))

    d1 = d2 + (sigma * np.sqrt(T))

    return (
        F * norm.cdf(d1) - K * norm.cdf(d2)
        if option_type == CallPut.CALL
        else K * norm.cdf(-d2) - F * norm.cdf(-d1)
    )
