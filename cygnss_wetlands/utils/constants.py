CYGNSS_WAVELENGTH_M = 0.19  # meters

EARTH_RADIUS_KM = 6371  # average radius of Earth, km

# standard CYGNSS data output rate is 1 Hz resulting in surface integration of ~6 km in the along track direction due to satellite motion
# this is well-established in the literature (see: CYGNSS Handbook, or e.g. https://www.mdpi.com/2072-4292/12/8/1317#)
CYGNSS_DISTANCE_TRAVELLED_IT_KM = 6

# distance threshold, km, for inverse distance weighting -- this is a bit arbitrary and impacts need to be better investigated
CYGNSS_IDW_DISTANCE_THRESHOLD_KM = 8

DEFAULT_CYGNSS_BBOX = (-180, -38, 180, 38)  # (xmin, ymin, xmax, ymax), full coverage of CYGNSS
