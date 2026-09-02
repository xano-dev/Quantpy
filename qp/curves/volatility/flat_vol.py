from qp.time.date.daycount import Daycount
from qp.utils.maps.options.vol_type import VolType


class FlatVol:
    
    def __init__(
        self,
        vol: float,
        vol_dc_convention: Daycount,
        vol_type: VolType = VolType.SHIFTED_LOGNORMAL,
        displacement: float = 0.0
    ):
        self._vol = vol
        self._vol_dc_convention = Daycount(vol_dc_convention)
        self._vol_type = VolType(vol_type)
        self._displacement = displacement
        
        self._validate()
        
        pass

    @property
    def vol(self):
        return self._vol
    
    @property
    def vol_dc_convention(self):
        return self._vol_dc_convention
    
    @property
    def vol_type(self):
        return self._vol_type
    
    @property
    def displacement(self):
        return self._displacement
    
    def _validate(self):
        if self._displacement != 0 and self._vol_type == VolType.NORMAL:
            raise ValueError("Displacement is only valid for shifted lognormal volatility")