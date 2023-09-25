import itertools
from typing import Tuple, Union

import numpy as np
import pandas as pd

from cygnss_wetlands.enums import AggregationMethod
from cygnss_wetlands.grids import GenericGrid
from cygnss_wetlands.utils.constants import (
    CYGNSS_IDW_DISTANCE_THRESHOLD_KM,
    EARTH_RADIUS_KM,
)


def drop_in_bucket(data: pd.DataFrame, grid: GenericGrid, variable_name: str) -> np.ndarray:
    """
    "Drop in the Bucket" aggregating algorithm - the simplest method !

    Each point is assigned to its nearest gridcell.  There is no attempt to assign weights
        by where in the box the point occurs.  If there is more than one point that falls
        within a gridcell, the mean value is used. There is no consideration of where the
        data points occur with respect to the gridcell boundary

    """
    # Get row, cols for grid
    col_row = data.apply(lambda x: grid.lonlat2cr(x.sp_lon, x.sp_lat), axis=1).values
    data[["col", "row"]] = pd.DataFrame(col_row.tolist(), index=data.index)

    # do fancy bucketting by
    _, idx, inv, counts = np.unique(col_row, return_index=True, return_inverse=True, return_counts=True)
    unique_coords = col_row[idx]
    unique_col, unique_row = zip(*unique_coords)

    # now sum the values corresponding to each inverse index value
    sum_values = np.bincount(inv, weights=data[variable_name])

    sum_grid = np.full((grid.n_rows, grid.n_cols), np.nan, dtype=np.float32)
    sum_grid[unique_row, unique_col] = sum_values

    count_grid = np.full((grid.n_rows, grid.n_cols), np.nan, dtype=np.float32)
    count_grid[unique_row, unique_col] = counts

    # return aggregated mean grid values !
    return sum_grid / count_grid


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Estimate distance between two points (lon/lat), given coordinates in degrees

    Returns:
        distance, in meters
    """
    # convert all latitudes/longitudes from decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(np.radians, (lat1, lon1, lat2, lon2))
    delta_lat = lat2 - lat1
    delta_lon = lon2 - lon1
    a = np.square(np.sin(delta_lat / 2.0)) + np.cos(lat1) * np.cos(lat2) * np.square(np.sin(delta_lon / 2.0))
    return 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a)) * EARTH_RADIUS_KM * 1000


def get_nearby_gridcells(grid: GenericGrid, r: int, c: int) -> Tuple[np.ndarray, np.ndarray]:
    n_neighbors = int(np.ceil(grid.res / (CYGNSS_IDW_DISTANCE_THRESHOLD_KM * 1000)))

    rows = [r]
    cols = [c]

    for n in range(1, n_neighbors + 1):
        # handles rows
        if r == 0:
            rows.append(r + n)
        elif r == grid.n_rows - 1:
            rows.append(r - n)
        else:
            rows.append(r + n)
            rows.append(r - n)

        # handle cols
        if c == 0:
            cols.append(grid.n_cols - n)
            cols.append(c + n)
        elif c == grid.n_cols - 1:
            cols = cols.append(n - 1)
            cols.append(c - n)
        else:
            cols.append(c + n)
            cols.append(c - n)

    rows_comb, cols_comb = zip(*itertools.product(rows, cols))
    return np.array(rows_comb).astype(np.int16), np.array(cols_comb).astype(np.int16)


def inverse_distance(data: pd.DataFrame, grid: GenericGrid, variable_name: str) -> np.ndarray:
    """
    This algorithm finds the nearest neighbors in all 8-directions. The values are weighted
        by distance, and can use a linear, squared, or other weighting to apply greater
        weights to points close to the grid intersection.

    Caveats:
        - For now, we ONLY support squared weights
        - Only supports grid CRS that has meters as base unit
    """
    # Ensure selected grid CRS units is meters
    try:
        assert grid.proj.crs.axis_info[0].unit_name == "metre"
    except AssertionError:
        raise Exception(
            "Need to either add support for other units - or add ability accept different spellings, "
            "meter / metre / m  for given CRS?)"
        )

    # to populate a gridcell, only consider values within this distance threshold
    dist_threshold_m = CYGNSS_IDW_DISTANCE_THRESHOLD_KM * 1000  # in meters

    # Get row, cols for grid
    col_row = data.apply(lambda x: grid.lonlat2cr(x.sp_lon, x.sp_lat), axis=1).values
    data[["col", "row"]] = pd.DataFrame(col_row.tolist(), index=data.index)

    # initialize empty grids to start with
    sum_grid = np.full((grid.n_rows, grid.n_cols), 0, dtype=np.float32)
    count_grid = np.full((grid.n_rows, grid.n_cols), 0, dtype=np.float32)

    # iterate over each data value - find neighbors, accumulate weighted values and counts
    # todo: is there a more efficient way to do this?
    for idx, row in data.iterrows():
        neighbors_row, neighbors_col = get_nearby_gridcells(grid, row.row, row.col)
        neighbors_lon, neighbors_lat = zip(
            *[grid.cr2lonlat(neighbors_col[i], neighbors_row[i]) for i in range(len(neighbors_row))]
        )
        dist_to_swathpt = haversine(
            lat1=neighbors_lat,
            lon1=neighbors_lon,
            lat2=np.repeat(row.sp_lat, len(neighbors_lat)),
            lon2=np.repeat(row.sp_lon, len(neighbors_lon)),
        )
        mask = dist_to_swathpt < dist_threshold_m
        sum_grid[neighbors_row[mask], neighbors_col[mask]] += row[variable_name] / (dist_to_swathpt[mask] ** 2)
        count_grid[neighbors_row[mask], neighbors_col[mask]] += 1.0 / (dist_to_swathpt[mask] ** 2)

    aggregated_grid = sum_grid / count_grid
    aggregated_grid[aggregated_grid == 0] = np.nan  # convert 0 --> NaN
    return aggregated_grid


AGGREGATION_METHODS = {
    AggregationMethod.DropInBucket: drop_in_bucket,
    AggregationMethod.InverseDistance: inverse_distance,
}
