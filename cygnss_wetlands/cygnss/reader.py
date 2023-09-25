import datetime
import glob
import os
from pathlib import Path
from typing import Dict, Iterable, Tuple, Union

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
import yaml
from netCDF4 import Dataset
from tqdm import tqdm

from cygnss_wetlands.cygnss.aggregate import AGGREGATION_METHODS
from cygnss_wetlands.enums import AggregationMethod
from cygnss_wetlands.grids import GenericGrid
from cygnss_wetlands.utils.constants import (
    CYGNSS_DISTANCE_TRAVELLED_IT_KM,
    CYGNSS_WAVELENGTH_M,
    DEFAULT_CYGNSS_BBOX,
    EARTH_RADIUS_KM,
)
from cygnss_wetlands.utils.radar import (
    amplitude2db,
    get_along_track_size,
    get_cross_track_size,
)

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
            self.bbox = shapely.geometry.box(*bbox)
        else:
            self.bbox = shapely.geometry.box(*DEFAULT_CYGNSS_BBOX)

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

            spacecraft_num = int(nc_fid.variables["spacecraft_num"][:].item())
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
            data["spacecraft_num"] = np.repeat(spacecraft_num, len(sample_ids) * len(ddm_ids))
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

            # Estimate DDM footprint geometries
            data["along_track_m"] = data.apply(
                lambda x: get_along_track_size(
                    incindence_angle_deg=x.sp_inc_angle, r_rx=x.rx_to_sp_range, r_tx=x.tx_to_sp_range
                ),
                axis=1,
            ).astype("float32")

            data["cross_track_m"] = data.apply(
                lambda x: get_cross_track_size(r_rx=x.rx_to_sp_range, r_tx=x.tx_to_sp_range), axis=1
            ).astype("float32")

            data["semimajor_axis"] = np.rad2deg(
                ((data["along_track_m"] + CYGNSS_DISTANCE_TRAVELLED_IT_KM * 1000) / 2) / (EARTH_RADIUS_KM * 1000)
            )
            data["semiminor_axis"] = np.rad2deg((data["cross_track_m"] / 2.0) / (EARTH_RADIUS_KM * 1000))
            data["bearing"] = self.estimate_ddm_bearing(data)
            data["footprint"] = data.apply(lambda x: self._calculate_ellipse_footprint(x), axis=1)

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

    @staticmethod
    def get_bearing(lat1, lon1, lat2, lon2):
        """Estimate bearing (degrees) between two points"""
        lat1, lon1, lat2, lon2 = map(np.deg2rad, (lat1, lon1, lat2, lon2))
        x = np.cos(lat2) * np.sin(lon2 - lon1)
        y = np.cos(lat1) * np.sin(lat2) - np.sin(lat1) * np.cos(lat2) * np.cos(lon2 - lon1)
        return np.rad2deg(np.arctan2(x, y))

    @staticmethod
    def _calculate_ellipse_footprint(x):
        """For a given point - get footprint ellipse geometry based on:
        - centroid (specular point)
        - semi-axes (major and minor)
        - angle of rotation (degrees)
        """
        try:
            # 1st elem = center point (x,y) coordinates
            # 2nd elem = the two semi-axis values (along x, along y)
            # 3rd elem = angle in degrees between x-axis of the Cartesian base
            #            and the corresponding semi-axis
            ellipse = ((x.sp_lon, x.sp_lat), (x.semimajor_axis, x.semiminor_axis), x.bearing)
            circ = shapely.geometry.Point(ellipse[0]).buffer(1)

            # Let create the ellipse along x and y:
            ell = shapely.affinity.scale(circ, ellipse[1][0], ellipse[1][1])

            # And rotate - clockwise along an upward pointing x axis:
            return shapely.affinity.rotate(ell, 90 - ellipse[2])

        except:
            print(f"Error forming ellipse: {ellipse}")
            return None

    def estimate_ddm_bearing(self, data: pd.DataFrame) -> np.ndarray:
        """Estimate the angle (degrees) at which a given DDM footprint"""
        bearing = np.zeros(len(data), dtype="float32")  # intialize an empty array

        # Adjust track_id so that is unique for each file
        data["track_id"] += data["spacecraft_num"] * 1000

        # Iterate over each unique track
        for track in data.track_id.unique():
            track_mask = data.track_id == track

            # We need at least two points inside a track to estimate the direction of movement
            if np.sum(track_mask) > 1:
                orbit_id = self.determine_orbit_id(data.sp_lat[track_mask].values)
                unique_orbits = np.unique(orbit_id)
                track_bearing = np.full(np.sum(track_mask), 0, dtype="float32")

                # Iterate over each ascending and descending pass (orbit) within track
                for orb in unique_orbits:
                    orbit_mask = orbit_id == orb
                    sub_bearing = np.full(np.sum(orbit_mask), 0, dtype="float32")

                    # Get best guess for end points
                    sub_bearing[0] = self.get_bearing(
                        lat1=data.sp_lat[track_mask][orbit_mask].iloc[0],
                        lon1=data.sp_lon[track_mask][orbit_mask].iloc[0],
                        lat2=data.sp_lat[track_mask][orbit_mask].iloc[1],
                        lon2=data.sp_lon[track_mask][orbit_mask].iloc[1],
                    )
                    sub_bearing[-1] = self.get_bearing(
                        lat1=data.sp_lat[track_mask][orbit_mask].iloc[-2],
                        lon1=data.sp_lon[track_mask][orbit_mask].iloc[-2],
                        lat2=data.sp_lat[track_mask][orbit_mask].iloc[-1],
                        lon2=data.sp_lon[track_mask][orbit_mask].iloc[-1],
                    )

                    # Estimate all points in between based on previous and following pt
                    lat1 = data.sp_lat[track_mask][orbit_mask].iloc[:-2].values
                    lon1 = data.sp_lon[track_mask][orbit_mask].iloc[:-2].values
                    lat2 = data.sp_lat[track_mask][orbit_mask].iloc[2:].values
                    lon2 = data.sp_lon[track_mask][orbit_mask].iloc[2:].values

                    sub_bearing[1:-1] = self.get_bearing(lat1, lon1, lat2, lon2)
                    track_bearing[orbit_mask] = sub_bearing

                bearing[track_mask] = track_bearing

            # otherwise, not enough points to estimate bearing
            else:
                bearing[track_mask] = np.nan

        return bearing

    @staticmethod
    def write_footprint_to_geojson(
        data: pd.DataFrame, out_filepath: Path, cols_to_write: Iterable = ["ddm_snr", "geometry"]
    ):
        # Convert dataframe to geodataframe
        gdf = gpd.GeoDataFrame(data, geometry=data.footprint, crs="EPSG:4326")

        # Write out to file
        gdf[cols_to_write].to_file(out_filepath, index=False)

    @staticmethod
    def determine_orbit_id(latitude: np.ndarray):
        orbit_id = np.zeros(latitude.shape, dtype=np.int8)

        # Define starting pass direction
        o = 0
        if latitude[0] < latitude[1]:
            prev_pass = "asc"
        else:
            prev_pass = "dsc"

        # Iterate over each spacecraft lat, and check if +/- previous one
        for s in range(len(latitude) - 1):
            if latitude[s] < latitude[s + 1]:
                current_pass = "dsc"
            else:
                current_pass = "asc"

            if prev_pass != current_pass:  # Orbit complete
                o += 1
                prev_pass = current_pass

            orbit_id[s] = o

        orbit_id[-1] = np.max(orbit_id)
        return orbit_id

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
        method: AggregationMethod = AggregationMethod.InverseDistance,
    ) -> np.ndarray:
        """
        For now, implement "drop in the bucket" style aggregation over specified date range

        Returns:
            2D np.ndarray gridded representation of specified DDM observable values over a period of time

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

        # Concatenate data from all spacecrafts over all dates in window
        all_data = pd.concat(all_data, ignore_index=True)

        # Apply aggregation method and get gridded array !
        aggregated_grid = AGGREGATION_METHODS[method](data=all_data, grid=grid, variable_name=variable_name)

        return aggregated_grid
