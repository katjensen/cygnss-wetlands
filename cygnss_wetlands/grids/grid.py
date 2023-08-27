from abc import ABC, abstractmethod
from pathlib import Path
from typing import Tuple, Union

import attrs
import numpy as np
import pyproj
import rasterio as rio
from affine import Affine
from rasterio.transform import from_origin

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
    transform: Affine = attrs.field(init=False)

    def __attrs_post_init__(self):
        self.proj = pyproj.Proj(self.epsg)
        self.transform = from_origin(west=self.x_min, north=self.y_max, xsize=self.res, ysize=self.res)

    @abstractmethod
    def lonlat2cr(self, lon: float, lat: float) -> Tuple[int, int]:
        pass

    @abstractmethod
    def cr2lonlat(self, col: int, row: int) -> Tuple[float, float]:
        pass

    def write_geotiff(
        self, array: np.ndarray, output_filepath: Path, nodata: Union[int, float] = -9999, compress: str = "lzw"
    ):
        """Write"""
        # ensure our input array is 2D, and match the expected dimensions for particular grid
        assert array.ndim == 2
        assert (array.shape[0] == self.n_rows) and (array.shape[1] == self.n_cols)

        output_profile = {
            "driver": "GTiff",
            "height": array.shape[0],
            "width": array.shape[1],
            "count": 1,
            "dtype": str(array.dtype),
            "crs": f"EPSG:{self.epsg}",
            "transform": self.transform,
            "nodata": nodata,
            "compress": compress,
        }

        # Mask any NaN values with given nodata value, write out
        array[np.isnan(array)] = nodata
        with rio.open(output_filepath, "w", **output_profile) as dst:
            dst.write(array, 1)

        print(f"Writing file: {output_filepath.name}")
