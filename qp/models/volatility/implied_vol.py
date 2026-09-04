from scipy.optimize import brentq
import numpy as np

from qp.utils.maps.options.vol_type import VolType
from qp.utils.maps.options.callput import CallPut
from qp.models.options.bachelier import bachelier
from qp.models.options.black76 import black76
from qp.models.option_type.intrinsic_value import compute_intrinsic_option_value


def implied_vol(
    prices: np.ndarray, F: np.ndarray, K: float, T: np.ndarray, option_type: CallPut, displacement: float, vol_type: VolType
) -> np.ndarray:

    if not (len(prices) == len(F) == len(T)):
        raise ValueError("prices, F and T must have the same length.")

    solved_vols = []

    for price, forward_price, time in zip(prices, F, T):
        if vol_type == VolType.SHIFTED_LOGNORMAL:
            solved_vol = implied_vol_black76(price, forward_price, K, time, option_type, displacement)
        elif vol_type == VolType.NORMAL:
            solved_vol = implied_vol_bachelier(price, forward_price, K, time, option_type)
        else:
            raise ValueError(f"Unsupported volatility type: {vol_type}")

        solved_vols.append(solved_vol)

    return np.array(solved_vols)
    


def implied_vol_bachelier(
    price: float, F: float, K: float, T: float, option_type: CallPut
) -> float:

    intrinsic_value = compute_intrinsic_option_value(F, K, option_type)

    if price < intrinsic_value:
        raise ValueError("No non-negative implied volatility exists for the supplied price and model inputs.")
    

    def objective_func(sigma: float) -> float:
        return (
            bachelier(
                np.array([F]),
                K,
                np.array([T]),
                sigma,
                option_type,
            )[0] - price
        )
    
    lower_vol = 0.0
    upper_vol = 0.1

    while objective_func(upper_vol) < 0:
        upper_vol *= 2

    return brentq(objective_func, lower_vol, upper_vol)

def implied_vol_black76(
    price: float, F: float, K: float, T: float, option_type: CallPut, displacement: float
) -> float:

    shifted_F = F + displacement
    shifted_K = K + displacement

    if shifted_F <= 0 or shifted_K <= 0:
        raise ValueError(
            "Forward and strike must be positive after displacement."
        )

    intrinsic_value = compute_intrinsic_option_value(F, K, option_type)

    if price < intrinsic_value:
        raise ValueError("No non-negative implied volatility exists for the supplied price and model inputs.")
    
    upper_price = shifted_F if option_type == CallPut.CALL else shifted_K

    if price >= upper_price:
        # As vol -> infinity, the Black-76 price approaches F + shift for a call and K + shift for a put
        # equality (i.e. price == upper_price) therefore implies infinite vol and a price above the bound has no solution
        raise ValueError("Option price is greater than finite Black-76 price range")

    def objective_func(sigma: float) -> float:
        return (
            black76(
                np.array([F]),
                K,
                np.array([T]),
                sigma,
                option_type,
                displacement
            )[0] - price
        )

    lower_vol = 0.0
    upper_vol = 0.1

    while objective_func(upper_vol) < 0:
        upper_vol *= 2

    return brentq(objective_func, lower_vol, upper_vol)