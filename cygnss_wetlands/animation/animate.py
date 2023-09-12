import datetime

import matplotlib.pyplot as plt

from cygnss_wetlands.cygnss.reader import CONFIG, CygnssL1Reader
from cygnss_wetlands.enums import GridType
from cygnss_wetlands.grids.ease import EASE2GRID

# Create our reader object

# Note: ingestion is a lot faster if we limit it to a smaller geopgraphic area of interest
# (this is optional! The default is the full extent of CYGNSS mission range)
PACAYA_SAMIRIA_BBOX = (-77, -7, -73, -3)  # xmin, ymin, xmax, ymax

reader = CygnssL1Reader(bbox=PACAYA_SAMIRIA_BBOX)

# Let's pick a grid we can aggregate/post our data to

# Here's a list of what is supported currently
# (custom grids can also be made! and more functionality is planned to be added!)
GridType.namelist()


def generateFigure(figureName, year, month, startDate, endDate, grid):
    d1 = datetime.datetime(year, month, startDate)
    d2 = datetime.datetime(year, month, endDate)

    snr = reader.aggregate(variable_name="ddm_snr", grid=grid, start_date=d1, end_date=d2)

    # Plot
    bbox_grid_xmin, bbox_grid_ymin = grid.lonlat2cr(reader.xmin, reader.ymin)
    bbox_grid_xmax, bbox_grid_ymax = grid.lonlat2cr(reader.xmax, reader.ymax)

    fig, ax = plt.subplots(figsize=(6, 6))
    pos = ax.imshow(snr)
    fig.colorbar(pos, ax=ax)
    ax.set_title(f"DDM_SNR {d1.strftime('%Y-%m-%d')} to {d2.strftime('%Y-%m-%d')} grid={grid.name}")
    ax.set_xlim(bbox_grid_xmin, bbox_grid_xmax)
    ax.set_ylim(bbox_grid_ymin, bbox_grid_ymax)
    plt.savefig(figureName)


def animate(year, startMonth, endMonth):
    import imageio

    frames = []

    # Starting with 9km grid, will parameterize later
    grid = EASE2GRID(GridType.EASE2_G9km)

    # Starting with 15 day intervals, will parameterize later
    intervals = [(1, 15), (15, 30)]
    monthlyIntervals = len(intervals)
    print(monthlyIntervals)

    for month in range(startMonth, endMonth + 1):
        for dateInterval in intervals:
            figName = (
                "DDM_SNR_"
                + str(year)
                + f"{month:02}"
                + f"{dateInterval[0]:02}"
                + "-"
                + str(year)
                + f"{month:02}"
                + f"{dateInterval[1]:02}"
                + ".png"
            )
            generateFigure(figName, year, month, dateInterval[0], dateInterval[1], grid)
            frames.append(figName)

    # frames = ["10120-11520.png","11520-13020.png"]

    # frames = ["DDM_SNR_20200101-20200115.png", "DDM_SNR_20200115-20200130.png"]
    images = []
    for file_name in frames:
        images.append(imageio.imread(file_name))

    gif_path = (
        "DDM_SNR_"
        + str(year)
        + f"{startMonth:02}"
        + "-"
        + str(year)
        + f"{endMonth:02}"
        + "_"
        + str(monthlyIntervals)
        + ".gif"
    )
    imageio.mimsave(gif_path, images)


# print(frames)
animate(2021, 4, 6)


# TODO:
# 1. Figure out why the second figure always uses a tight border
# 2. Determine max & min of data prior to generating figures & have that be common throughout the animation
# 3. Save to organized file structure
# 4. Read from file structure if the figure already exists & use if so
#
# Asks:
# 1. What do you think about these white pixels?
# 2. What file format would you prefer? GIF? MOV? MP4? Would be good to slow FPS, so maybe mp4
