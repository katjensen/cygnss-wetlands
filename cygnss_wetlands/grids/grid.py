from abc import ABC, abstractmethod
from typing import Tuple, Union

import attrs
import pyproj

from cygnss_wetlands.enums import GridType


@attrs.define(slots=True)
class GenericGrid(ABC):
    """A generic Grid class, that includes shared attributes and functions used by various grid classes

    Args:
        name:    Name of the grid. Name as you wish
        epsg:    EPSG identifier
        x_min:   x-axis map coordinate of the outer edge of the upper-left pixel of the grid
        y_max:   y-axis map coordinate of the outer edge of the upper-left pixel of the grid
        res:     Resolution of the grid pixel (in units appropriate for EPSG)
        n_rows:  Number of Rows
        n_cols:  Number of Columns
    """

    name: str  # = attrs.field(kw_only=True)
    epsg: int
    x_min: Union[int, float]
    y_max: Union[int, float]
    res: Union[int, float]
    n_rows: int
    n_cols: int
    proj: pyproj.proj.Proj = attrs.field(init=False)

    def __attrs_post_init__(self):
        self.proj = pyproj.Proj(self.epsg)

    @abstractmethod
    def lonlat2rc(self, lon: float, lat: float) -> Tuple[int, int]:
        pass

    @abstractmethod
    def rc2lonlat(self, col: int, row: int) -> Tuple[float, float]:
        pass
