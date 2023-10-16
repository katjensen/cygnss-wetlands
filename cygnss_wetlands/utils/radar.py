from typing import Union

import numpy as np

from cygnss_wetlands.utils.constants import CYGNSS_WAVELENGTH_M


def db2power(x):
    return np.power(10.0, x / 10.0)


def power2db(x):
    return 10.0 * np.log10(x)


def amplitude2db(x):
    return 20.0 * np.log10(x)


def get_along_track_size(
    incindence_angle_deg: Union[float, np.ndarray],
    r_rx: Union[float, np.ndarray],
    r_tx: Union[float, np.ndarray],
    D: float = CYGNSS_WAVELENGTH_M,
) -> Union[float, np.ndarray]:
    theta = np.deg2rad(90.0 - incindence_angle_deg)
    return 2 * (1.0 / np.sin(theta)) * np.power(r_rx * r_tx * D / (r_rx + r_tx), 0.5)


def get_cross_track_size(
    r_rx: Union[float, np.ndarray], r_tx: Union[float, np.ndarray], D: float = CYGNSS_WAVELENGTH_M
) -> Union[float, np.ndarray]:
    return 2 * np.power(r_rx * r_tx * D / (r_rx + r_tx), 0.5)
