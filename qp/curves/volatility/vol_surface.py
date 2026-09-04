import numpy as np

from qp.curves.volatility.vol_smile import VolSmile
from qp.time.date.daycount import Daycount
from qp.utils.maps.options.vol_type import VolType
from qp.utils.math.interpolation import InterpolationMethod, Interpolator


class VolSurface:
    
    def __init__(
        self,
        smiles: list[VolSmile],
        extrapolate: bool = False,
    ):
        self._smiles = sorted(smiles, key = lambda smile: smile._expiry )
        self._expiries = np.array([smile.expiry for smile in self._smiles])
        self._extrapolate = extrapolate

        self._validate()
    
    @property
    def smiles(self):
        return self._smiles
    
    @property
    def expiries(self):
        return self._expiries
    
    @property
    def extrapolate(self):
        return self._extrapolate
    
    def _validate(self):

        vol_dc_conventions = np.array([smile.vol_dc_convention for smile in self._smiles])
        vol_types = np.array([smile.vol_type for smile in self._smiles])
        displacements = np.array([smile.displacement for smile in self._smiles])
        interpolation_methods = np.array([smile.interpolation_method for smile in self._smiles])

        if not np.all(vol_dc_conventions == vol_dc_conventions[0]):
            raise ValueError("All volatility smiles must have the same daycount convention")
        
        if not np.all(vol_types == vol_types[0]):
            raise ValueError("All volatility smiles must have the same vol type")
        
        if not np.all(displacements == displacements[0]):
            raise ValueError("All volatility smiles must have the same displacement")
        
        if not np.all(interpolation_methods == interpolation_methods[0]):
            raise ValueError("All volatility smiles must have the same interpolation method")
        