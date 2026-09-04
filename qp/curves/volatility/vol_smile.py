import numpy as np

from qp.time.date.daycount import Daycount
from qp.utils.maps.options.vol_type import VolType
from qp.utils.math.interpolation import InterpolationMethod, Interpolator

class VolSmile:
    
    def __init__(
        self,
        strikes: np.ndarray,
        expiry: float,
        vols: np.ndarray,
        vol_dc_convention: Daycount,
        vol_type: VolType = VolType.SHIFTED_LOGNORMAL,
        displacement: float = 0.0,
        interpolation_method: InterpolationMethod = InterpolationMethod.LOG_LINEAR,
        extrapolate: bool = False,
    ):
        self._strikes = strikes
        self._expiry = expiry
        self._vols = vols
        self._vol_dc_convention = Daycount(vol_dc_convention)
        self._vol_type = VolType(vol_type)
        self._displacement = displacement
        self._interpolation_method = interpolation_method
        self._extrapolate = extrapolate

        self._validate()

        self._interpolator = self._generate_interpolator()
    
    @property
    def strikes(self):
        return self._strikes
    
    @property
    def expiry(self):
        return self._expiry

    @property
    def vols(self):
        return self._vols
    
    @property
    def vol_dc_convention(self):
        return self._vol_dc_convention
    
    @property
    def vol_type(self):
        return self._vol_type
    
    @property
    def displacement(self):
        return self._displacement
    
    @property
    def interpolation_method(self):
        return self._interpolation_method
    
    @property
    def extrapolate(self):
        return self._extrapolate
    
    def _validate(self):
        if self._displacement != 0 and self._vol_type == VolType.NORMAL:
            raise ValueError("Displacement is only valid for shifted lognormal volatility")
        
        if len(self._strikes) != len(self._vols):
            raise ValueError("Strikes and vols must be the same length")
        
        if self._expiry <= 0:
            raise ValueError("Expiry must be greater than zero")
        
        if np.any(self._vols < 0):
            raise ValueError("Volatilities cannot be negative")

    def _generate_interpolator(self):
        return Interpolator(
            self._strikes,
            self._vols,
            self._interpolation_method,
            self._extrapolate,
        )
    
    def get_vols(self, strikes: float | np.ndarray) -> float | np.ndarray:
        return self._interpolator.interpolate(strikes)