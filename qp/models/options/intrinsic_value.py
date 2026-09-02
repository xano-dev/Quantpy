import numpy as np

from qp.utils.maps.options.callput import CallPut


def compute_intrinsic_option_value(
    F: float | np.ndarray, K: float, option_type: CallPut,
) -> float | np.ndarray:
    return (
            np.maximum(F - K, 0)
            if option_type == CallPut.CALL
            else np.maximum(K - F, 0)
        )