from typing import Tuple

import pyproj

from cygnss_wetlands.enums import GridType
from cygnss_wetlands.grids import GenericGrid

"""
    This code is inspired by 'easeconv-0.3' software, the EASE-Grid map transformation utilities developed and
    distributed by the National Snow & Ice Data Center (NSIDC), University of Colorado at Boulder. But instead of
    defining projections and grids "from scratch", the pyproj library and definition of grids from NSIDC [1] have
    been used.

    Works for EASE-Grid 2.0, should works also for EASE-Grid.

    MOTIVATION
        Get row and col coordinates corresponding to the pixel of EASE2 grid with given lon-lat coordinates.
    SUPPORTED GRIDS
        'EASE2_G1km',
        'EASE2_G3km', 'EASE2_N3km', 'EASE2_S3km',
        'EASE2_G3125km', 'EASE2_N3125km', 'EASE2_S3125km',
        'EASE2_G625km', 'EASE2_N625km', 'EASE2_S625km',
        'EASE2_G9km', 'EASE2_N9km', 'EASE2_S9km',
        'EASE2_G125km', 'EASE2_N125km', 'EASE2_S125km',
        'EASE_G125km', 'EASE_N125km', 'EASE_S125km',
        'EASE2_G25km', 'EASE2_N25km', 'EASE2_S25km',
        'EASE_G25km', 'EASE_N25km', 'EASE_S25km',
        'EASE2_G36km', 'EASE2_N36km', 'EASE2_S36km'
    TESTED GRIDS:
        EASE2-grids - 9km (N, S, G), 36km (N, G)
    NOT TESTED GRIDS
        EASE-grids - all.
        EASE2-grids - 1km, 3km, 3.125km, 6.25km and 25km
        If you can test this code on some of the not tested grids, I would appreciate if you do it and let me know :)
        Especially EASE grids.
    USAGE
        # define new grid by yourself
        grid = EASE2GRID(name='EASE2_G36km', epsg=6933, x_min=-17367530.45, y_max=7314540.83, res=36032.22,
                         n_cols=964, n_rows=406)
        # or using parameters taken from [1] and kept in SUPPORTED_GRIDS
        grid = EASE2GRID(name='EASE2_G36km', **SUPPORTED_GRIDS['EASE2_G36km'])
        # convert longitude and latitude to row and col indices
        point_lon = 17.4
        point_lat = 49.4
        # row should be 48, col should be 528
        col, row = grid.lonlat2cr(lon=point_lon, lat=point_lat)
        # get lon, lat of the center of the pixel
        pixel_center_lon, pixel_center_lat = grid.cr2lonlat(col=col, row=row)
    REFERENCES
        [1] https://nsidc.org/ease/ease-grid-projection-gt
"""


SUPPORTED_EASEGRIDS = {
    GridType.EASE2_G1km: {
        "epsg": 6933,
        "x_min": -17367530.45,
        "y_max": 7314540.83,
        "res": 1000.90,
        "n_cols": 34704,
        "n_rows": 14616,
    },
    GridType.EASE2_G3km: {
        "epsg": 6933,
        "x_min": -17367530.45,
        "y_max": 7314540.83,
        "res": 3002.69,
        "n_cols": 11568,
        "n_rows": 4872,
    },
    GridType.EASE2_N3km: {
        "epsg": 6931,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 3000.00,
        "n_cols": 6000,
        "n_rows": 6000,
    },
    GridType.EASE2_S3km: {
        "epsg": 6932,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 3000.00,
        "n_cols": 6000,
        "n_rows": 6000,
    },
    GridType.EASE2_G3125km: {
        "epsg": 6933,
        "x_min": -17367530.45,
        "y_max": 7307375.92,
        "res": 3128.16,
        "n_cols": 11104,
        "n_rows": 4672,
    },
    GridType.EASE2_N3125km: {
        "epsg": 6931,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 3125.00,
        "n_cols": 5760,
        "n_rows": 5760,
    },
    GridType.EASE2_S3125km: {
        "epsg": 6932,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 3125.00,
        "n_cols": 5760,
        "n_rows": 5760,
    },
    GridType.EASE2_G625km: {
        "epsg": 6933,
        "x_min": -17367530.45,
        "y_max": 7307375.92,
        "res": 6256.32,
        "n_cols": 5552,
        "n_rows": 2336,
    },
    GridType.EASE2_N625km: {
        "epsg": 6931,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 6250.00,
        "n_cols": 2880,
        "n_rows": 2880,
    },
    GridType.EASE2_S625km: {
        "epsg": 6932,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 6250.00,
        "n_cols": 2880,
        "n_rows": 2880,
    },
    GridType.EASE2_G9km: {
        "epsg": 6933,
        "x_min": -17367530.45,
        "y_max": 7314540.83,
        "res": 9008.05,
        "n_cols": 3856,
        "n_rows": 1624,
    },
    GridType.EASE2_N9km: {
        "epsg": 6931,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 9000.00,
        "n_cols": 2000,
        "n_rows": 2000,
    },
    GridType.EASE2_S9km: {
        "epsg": 6932,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 9000.00,
        "n_cols": 2000,
        "n_rows": 2000,
    },
    GridType.EASE2_G125km: {
        "epsg": 6933,
        "x_min": -17367530.45,
        "y_max": 7307375.92,
        "res": 12512.63,
        "n_cols": 2776,
        "n_rows": 1168,
    },
    GridType.EASE2_N125km: {
        "epsg": 6931,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 12500.00,
        "n_cols": 1440,
        "n_rows": 1440,
    },
    GridType.EASE2_S125km: {
        "epsg": 6932,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 12500.00,
        "n_cols": 1440,
        "n_rows": 1440,
    },
    GridType.EASE_G125km: {
        "epsg": 3410,
        "x_min": -17327927.35,
        "y_max": 7338516.48,
        "res": 12533.76,
        "n_cols": 2766,
        "n_rows": 1171,
    },
    GridType.EASE_N125km: {
        "epsg": 3408,
        "x_min": -9030574.08,
        "y_max": 9030574.08,
        "res": 12533.76,
        "n_cols": 1441,
        "n_rows": 1441,
    },
    GridType.EASE_S125km: {
        "epsg": 3409,
        "x_min": -9030574.08,
        "y_max": 9030574.08,
        "res": 12533.76,
        "n_cols": 1441,
        "n_rows": 1441,
    },
    GridType.EASE2_G25km: {
        "epsg": 6933,
        "x_min": -17367530.45,
        "y_max": 7307375.92,
        "res": 25025.26,
        "n_cols": 1388,
        "n_rows": 584,
    },
    GridType.EASE2_N25km: {
        "epsg": 6931,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 25000.00,
        "n_cols": 720,
        "n_rows": 720,
    },
    GridType.EASE2_S25km: {
        "epsg": 6932,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 25000.00,
        "n_cols": 720,
        "n_rows": 720,
    },
    GridType.EASE_G25km: {
        "epsg": 3410,
        "x_min": -17334193.54,
        "y_max": 7338516.48,
        "res": 25067.53,
        "n_cols": 1383,
        "n_rows": 586,
    },
    GridType.EASE_N25km: {
        "epsg": 3408,
        "x_min": -9036842.76,
        "y_max": 9036842.76,
        "res": 25067.53,
        "n_cols": 721,
        "n_rows": 721,
    },
    GridType.EASE_S25km: {
        "epsg": 3409,
        "x_min": -9036842.76,
        "y_max": 9036842.76,
        "res": 25067.53,
        "n_cols": 721,
        "n_rows": 721,
    },
    GridType.EASE2_G36km: {
        "epsg": 6933,
        "x_min": -17367530.45,
        "y_max": 7314540.83,
        "res": 36032.22,
        "n_cols": 964,
        "n_rows": 406,
    },
    GridType.EASE2_N36km: {
        "epsg": 6931,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 36000.00,
        "n_cols": 500,
        "n_rows": 500,
    },
    GridType.EASE2_S36km: {
        "epsg": 6932,
        "x_min": -9000000.0,
        "y_max": 9000000.0,
        "res": 36000.00,
        "n_cols": 500,
        "n_rows": 500,
    },
}


class EASE2GRID(GenericGrid):
    """Definition of EASE-grid 2.0. Enable to convert from geographic coordinates (longitude, latitude) to one of EASE2
    map projection (azimuthal equal-area or cylindrical equal-area) x, y coordinates or grid coordinates (row, col)
    and vice versa using PROJ (https://proj.org).
    EASE-Grid 2.0:
        Northern Hemisphere, Lambert Azimuthal ​(EPSG: 6931)
        Southern Hemisphere, Lambert Azimuthal ​(EPSG: 6932)
        Global, Equal-Area ​(EPSG: 6933)
    EASE-Grid:
        Northern Hemisphere, Lambert Azimuthal ​(EPSG: 3408)
        Southern Hemisphere, Lambert Azimuthal ​(EPSG: 3409)
        Global, Equal-Area ​(EPSG: 3410)
    """

    def __init__(self, grid_type: GridType):
        super().__init__(name=grid_type.name, **SUPPORTED_EASEGRIDS[grid_type])

    def lonlat2cr(self, lon: float, lat: float) -> Tuple[int, int]:
        """
        Convert given geographic coordinates (longitude, latitude) to EASE-grid 2.0 coordinates (col, row)
        """
        x, y = self.proj(lon, lat)
        col = int(abs(x - self.x_min) / self.res)
        row = int(abs(y - self.y_max) / self.res)

        # check max and min row (col) values
        assert col <= self.n_cols, f"col-coordinate in {self.name} grid should be less then {self.n_cols}"
        assert row <= self.n_rows, f"row-coordinate in {self.name} grid should be less then {self.n_rows}"

        return col, row

    def cr2lonlat(self, col: int, row: int) -> Tuple[float, float]:
        """
        Convert given EASE-grid 2.0 coordinates (col, row) to geographic coordinates
            (longitude, latitude) - center of pixel
        """
        # calculate x, y coordinates
        x = self.x_min + col * self.res + self.res / 2
        y = self.y_max - row * self.res - self.res / 2

        lon, lat = self.proj(x, y, inverse=True)

        # check max and min longitude (latitude) values
        assert (lon >= -180.0) & (lon <= 180.0), f"longitude in {self.name} grid should be between -180 and 180"

        if self.epsg in [6933, 3410]:
            assert (lat >= -90.0) & (lat <= 90.0), f"latitude in {self.name} grid should be between -90 and 90"
        elif self.epsg in [6931, 3408]:
            assert (lat >= 0.0) & (lat <= 90.0), f"latitude in {self.name} grid should be between 0 and 90"
        elif self.epsg in [6932, 3409]:
            assert (lat >= -90.0) & (lat <= 0.0), f"latitude in {self.name} grid should be between -90 and 0"

        return lon, lat
