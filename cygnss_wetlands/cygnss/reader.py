import datetime
import glob
import os
from pathlib import Path
from typing import Dict, Tuple, Union

import numpy as np
import pandas as pd
import yaml
from netCDF4 import Dataset
from shapely.geometry import box
from tqdm import tqdm

from cygnss_wetlands.grids import GenericGrid
from cygnss_wetlands.utils.constants import CYGNSS_WAVELENGTH_M, DEFAULT_CYGNSS_BBOX
from cygnss_wetlands.utils.radar import amplitude2db

# Ingest Cygnss config file
config_path = Path(__file__).resolve().parent / "config.yaml"
with open(config_path) as f:
    CONFIG = yaml.load(f, Loader=yaml.FullLoader)


# Try to define parent CYGNSS data path - if store in env variables
try:
    CYGNSS_DATA_DIR = Path(os.environ["CYGNSS_DATA_PATH"])

except KeyError:
    CYGNSS_DATA_DIR = None
    print(
        "Consider saving CYGNSS_DATA_PATH as an environment variable! Otherwise must specify when initiaizing reader objects"
    )


class CygnssL1Reader:
    _product_level = "L1"
    _product_version = CONFIG["L1"]["product_version"]

    def __init__(
        self,
        data_dir: Union[str, Path, None] = CYGNSS_DATA_DIR,
        bbox: Union[Tuple[float, float, float, float], None] = None,
        near_land: bool = False,
    ):
        """
        Args:
            data_dir: Path to parent directory for CYGNSS data files
                        Data files are expected to nest below this parent directory, following:
                        PRODUCT_LEVEL / PRODUCT_VERSION / YEAR / MONTH / DAY / XXX.nc

            bbox: (optional), geographic bounding box to constrain data ingestion, formatted as a tuple (xmin,ymin,xmax,ymax)
                        Must be in geographic coordinates (ie. lon / lat)

        """
        self.data_path = Path(data_dir).joinpath(self._product_level, self._product_version)
        self.quality_flags = CONFIG[self._product_level]["quality_flags"]
        self.near_land = near_land

        if bbox:
            self.bbox = box(*bbox)
        else:
            self.bbox = box(*DEFAULT_CYGNSS_BBOX)

        self.xmin = min(self.bbox.boundary.xy[0])
        self.ymin = min(self.bbox.boundary.xy[1])
        self.xmax = max(self.bbox.boundary.xy[0])
        self.ymax = max(self.bbox.boundary.xy[1])

        # Check if local path exists? Throw a warning
        if not self.data_path.exists():
            raise Warning(
                "Expected product and version sub-folders do not exist in CYGNSS_DATA_PATH. Please follow: "
                "[CYGNSS_DATA_PATH] / [PRODUCT LEVEL] / [VERSION]"
            )

    def read_file(self, file_path: Union[str, Path]):
        """
        Read in entire file - format into a 2D array and filter out:
            - Invalid data
            - (if specified) within provided geopgraphic contraints
            - TODO; (if specified) only measurements over or near land

        TODO:Once we can read directly from S3 -- we can extract points based on geography on the fly!
            ... and do not need to read all data in !!

        """
        try:
            nc_fid = Dataset(file_path, "r")
            # print(f"READING: {file_path.name}")

            sample_ids = self.read_variable(nc_fid, "sample")  # this is a vector of each sample ID
            ddm_ids = self.read_variable(nc_fid, "ddm")  # this will always be len=4, (0, 1, 2, 3)

            # Ultimately, we want to collapse our data into a 2D array (Rows= Sample x Cols= Attribute)
            # There are 4 DDMs associated with each sample
            #  Here we opt to collapse that dimension "columnwise" / F-order
            #   e.g. [Sample0_DDM0 , Sample1_DDM0 , .. SampleK_DDM0, Sample0_DDM1, ...
            #       SampleK_DDM2, Sample0_DDM3, Sample1_DDM3 ... SampleK_DDM3]
            # Why not use the default C-order (row-wise) collapsing method?
            #  --> Retaining sequential sample order will help with some additional derivation down the road!
            #   (e.g. orbit direction)
            data = {}
            data["sample_id"] = np.repeat(sample_ids[:, np.newaxis], len(ddm_ids), axis=1).ravel(order="F")
            data["ddm_id"] = np.repeat(ddm_ids, len(sample_ids))

            # Per-sample variables
            # We need to broadcast/repeat these values x4 for each DDM, and collapse
            for variable in CONFIG[self._product_level]["per_sample_attributes"]:
                array = self.read_variable(nc_fid, variable)
                data[variable] = np.repeat(array[:, np.newaxis], len(ddm_ids), axis=1).ravel(order="F")

            # Per-DDM variables
            # These are natively read in as 2D arrays (Sample x DDM), collapse columnwise to 1D
            for variable in CONFIG[self._product_level]["per_ddm_attributes"]:
                data[variable] = self.read_variable(nc_fid, variable).ravel(order="F")

            # Convert dict to dataframe, reduce records to specular points within geogrpahic bbox
            data = pd.DataFrame(data)
            bbox_mask = (
                (data["sp_lon"] >= self.xmin)
                & (data["sp_lon"] <= self.xmax)
                & (data["sp_lat"] >= self.ymin)
                & (data["sp_lat"] <= self.ymax)
            )
            data = data[bbox_mask].reset_index(drop=True)

            # Check if any data available (may not be any after bbox filtering !)
            if np.sum(bbox_mask) > 0:

                # Per-bin variables (if deriving custom metrics)
                # TODO: Add support for deriving TES, LES, etc from brcs

                # Quality Flags - convert bit values to True/False masks for each quality attribute and save in dataframes
                # There are two sets of quality indicators, need to repeat steps for both
                quality_bit_values1 = self.read_variable(nc_fid, "quality_flags").ravel(order="F")[bbox_mask]
                quality_bit_values2 = self.read_variable(nc_fid, "quality_flags_2").ravel(order="F")[bbox_mask]

                quality_flags1 = self.get_quality_flags(
                    qf_values=quality_bit_values1, qf_config=CONFIG[self._product_level]["quality_flags"][1]
                )

                quality_flags2 = self.get_quality_flags(
                    qf_values=quality_bit_values2, qf_config=CONFIG[self._product_level]["quality_flags"][2]
                )

                # Concat all our data ! And close netcdf file
                data = pd.concat([data, quality_flags1, quality_flags2], axis=1)
                nc_fid.close()

                # Screen out poor quality data (based on flags set to TRUE in config)
                flags_to_screen = [
                    flag
                    for flag in CONFIG[self._product_level]["quality_flags"][1]
                    if CONFIG[self._product_level]["quality_flags"][1][flag]
                ] + [
                    flag
                    for flag in CONFIG[self._product_level]["quality_flags"][2]
                    if CONFIG[self._product_level]["quality_flags"][2][flag]
                ]
                data["poor_quality_for_analysis"] = data[flags_to_screen].sum(axis=1) > 0
                data = data[~data.poor_quality_for_analysis].reset_index(drop=True)

                # Retain only data over (or near) land -- if specified
                if self.near_land:
                    land_mask = data.sp_over_land | data.sp_very_near_land | data.sp_near_land
                    data = data[land_mask].reset_index(drop=True)

            return data

        except FileNotFoundError:
            raise Exception("Specified filepath does not exist")

    def read_variable(self, nc_fid, variable_name) -> np.ndarray:
        try:
            array = nc_fid.variables[variable_name][:]

            # Quick check- rescale any longitude variables to be -180 to 180 !
            if "_lon" in variable_name:
                array = self.rescale_longitude(array)

            return array

        except KeyError:
            raise Exception(f"Variable '{variable_name}' not found in NetCDF file {Path(nc_fid.filepath()).name}")

    @staticmethod
    def read_binary_flags(qf_value: int, nflags: int) -> np.ndarray:
        flags = []

        for i in range(nflags):
            flag = (qf_value >> i) & 1
            flags.append(flag)

        return flags

    def get_quality_flags(self, qf_values: np.ndarray, qf_config: Dict) -> pd.DataFrame:
        quality_flags = []

        for qa_value in qf_values:
            quality_flags.append(self.read_binary_flags(qa_value, len(qf_config)))

        return pd.DataFrame(np.array(quality_flags).astype("bool"), columns=qf_config.keys())

    @staticmethod
    def rescale_longitude(lon: np.ndarray) -> np.ndarray:
        """Rescale longitude (0 to 360) --> (-180 to 180)"""
        mask = lon > 180
        lon[mask] = lon[mask] - 360.0
        return lon

    def apply_snr_correction(self, ddm_snr, range_rx, range_tx, power_tx, gain_rx, gain_tx):
        """
        Correction to ddm_snr observable - derived from coherent component of bistatic radar equation
        (see: Rodriguez et al 2019 https://www.mdpi.com/2072-4292/11/9/1053 )
        """
        return (
            ddm_snr
            - power_tx
            - gain_rx
            - gain_tx
            - amplitude2db(CYGNSS_WAVELENGTH_M)
            + amplitude2db(range_tx + range_rx)
            + amplitude2db(4.0 * np.pi)
        )

    def daily_filelist(self, date: datetime.datetime):
        daily_subdir = self.data_path.joinpath(str(date.year), "{:02d}".format(date.month), "{:02d}".format(date.day))
        return daily_subdir.glob("*.nc")

    def aggregate(
        self,
        variable_name: str,
        grid: GenericGrid,
        start_date: datetime.datetime,
        end_date: datetime.datetime,
    ) -> np.ndarray:
        """
        For now, implement "drop in the bucket" style aggregation over specified date range

        Returns:
            2D np.ndarray gridded representation of specified DDM observable values over a period of time

        TODO: Add inverse-distance weighted (IDW) implementation

        TODO: Add option to write out as GeoTIFF ?

        TODO: Add additiional constraints of interest? (e.g. restrict to certain spacecraft? )
        """

        # Read all data over all dates (inclusive of end_date)
        all_data = []
        date_list = [start_date + datetime.timedelta(days=x) for x in range((end_date - start_date).days + 1)]

        file_list = [filename for date in date_list for filename in self.daily_filelist(date)]
        for filename in tqdm(file_list):
            df = self.read_file(filename)
            if not df.empty:
                all_data.append(df)
        """
        for date in date_list:

            # Find all files associated with a given date
            for filename in self.daily_filelist(date):
                df = self.read_file(filename)
                if not df.empty:
                    all_data.append(df)
        """

        # Concatenate data from all spacecrafts over all dates in window
        all_data = pd.concat(all_data, ignore_index=True)

        # Get row, cols for grid
        col_row = all_data.apply(lambda x: grid.lonlat2cr(x.sp_lon, x.sp_lat), axis=1).values
        all_data[["col", "row"]] = pd.DataFrame(col_row.tolist(), index=all_data.index)

        # do fancy bucketting by
        _, idx, inv, counts = np.unique(col_row, return_index=True, return_inverse=True, return_counts=True)
        unique_coords = col_row[idx]
        unique_col, unique_row = zip(*unique_coords)

        # now sum the values of s0 corresponding to each inv index value
        sum_values = np.bincount(inv, weights=all_data[variable_name])

        sum_grid = np.full((grid.n_rows, grid.n_cols), np.nan, dtype=np.float32)
        sum_grid[unique_row, unique_col] = sum_values

        count_grid = np.full((grid.n_rows, grid.n_cols), np.nan, dtype=np.float32)
        count_grid[unique_row, unique_col] = counts

        # return aggregated grid values !
        return sum_grid / count_grid
