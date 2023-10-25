import calendar
import datetime
from pathlib import Path

import imageio
import matplotlib.pyplot as plt
import numpy as np

from cygnss_wetlands.cygnss.reader import CONFIG, CygnssL1Reader
from cygnss_wetlands.enums import GridType
from cygnss_wetlands.grids.ease import EASE2GRID

# Animation script currently only supports Pacaya Samiria
PACAYA_SAMIRIA_BBOX = (-77, -7, -73, -3)  # xmin, ymin, xmax, ymax
reader = CygnssL1Reader(bbox=PACAYA_SAMIRIA_BBOX)


def genDistribution(data, filename: str, variable_name: str):
    """
    Generates a histogram distribution of the variable name in provided data

    Args:
        data:
        filename (str): Name of ouptut file
        variable_name (str): Name of variable to generate the distribution of from the data variable

    Returns:
        None: Saves histogram figure to filename
    """
    print(f"Generating distribution of {variable_name}")
    plt.hist(data, bins=30)
    plt.title("Histogram")
    plt.xlabel(variable_name)
    plt.ylabel("Frequency")
    plt.savefig(filename)


def generateAnimationFileStructure(destination_dir: Path = Path("./")):
    """
    Generates the file structure for animations. This includes a directory 'animations' to store the outputted animations and
    a hidden directory '.figures' for individual frames

    Args:
        destination_dir (Path): Root directory for the file structure (default='./')

    Returns:
        figure_root_path (Path): Path from destination_dir to the hidden figure directory
        animation_root_path (Path): Path from destination_dir to the animation directory

    Example:
        >>> print(generateAnimationFileStructure())
        (PosixPath('.figures'), PosixPath('animations'))
    """
    figure_dir = Path(".figures")
    animation_dir = Path("animations")

    figure_root_path = Path.joinpath(destination_dir, figure_dir)
    animation_root_path = Path.joinpath(destination_dir, animation_dir)

    if not figure_root_path.exists():
        figure_root_path.mkdir()
    if not animation_root_path.exists():
        animation_root_path.mkdir()

    return figure_root_path, animation_root_path


def getMonthFilePath(year: int, month: int, figure_path: Path):
    """
    Returns the year, month directory path.

    If the path does not already exist, generates a year, month directory file structure for a given year, month
    combination within the hidden .figures directory.

    Args:
        year (int): Year of the figure for this path
        month (int): Month of the figure for this path

    Returns:
        figure_month_path (Path): Path rooted from figure_path to the year, month directory

    Example:
        >>> print(getMonthFilePath(2022, 1, Path("./.figures")))
        (PosixPath('.figures'), PosixPath('animations'))
    """
    figure_year_path = Path.joinpath(figure_path, Path(str(year)))
    figure_month_path = Path.joinpath(figure_year_path, Path(str(month)))

    if not figure_path.exists():
        generateAnimationFileStructure()
    if not figure_year_path.exists():
        figure_year_path.mkdir()
    if not figure_month_path.exists():
        figure_month_path.mkdir()

    return figure_month_path


def createMonthlyIntervals(year: int, month: int, numIntervals: int):
    """
    Outputs a list of intervals for the given month

    Args:
        year (int): The year you wish to create monthly intervals for
        month (int): The month you wish to create monthly intervals for
        numIntervals (int): The number of intervals you want in the month

    Returns:
        list of tuples: A list of tuples of length numIntervals containing non-overlapping dates for the given month

    Example:
        >>> intervals = createMonthlyIntervals(year=2023, month=1, numIntervals=2)
        >>> print(intervals)
        [(1, 15), (16, 31)]
    """
    monthIntervals = []
    numDays = calendar.monthrange(year, month)[1]
    daysPerInterval = numDays // numIntervals
    for i in range(numIntervals):
        intervalStart = 1 + (i * daysPerInterval)
        intervalEnd = (i + 1) * daysPerInterval
        if i == numIntervals - 1:
            intervalEnd += numDays % numIntervals
        monthIntervals.append((intervalStart, intervalEnd))
    return monthIntervals


def generateFigure(
    figureName: str, year: int, month: int, startDate: int, endDate: int, grid: GridType, max: float, min: float
):
    """
    Creates and saves a figure to figureName for the given year, month, and date range on the prescribed grid.

    Args:
        figureName (str): The filename to save the figure to
        year (int): The year in numerical format the figure is representing
        month (int): The month in numerical format the figure is representing
        startDate (int): The start date of the month in numerical format the figure is representing
        endDate (int): The end date of the month in numerical format the figure is representing
        grid (GridType): The EASE2 GridType to bin data in for the figure
        max (float): The maximum value of the colorbar
        min (float): The minimum value of the colorbar

    Returns:
        None: Saves figure to figureName
    """
    d1 = datetime.datetime(year, month, startDate)
    d2 = datetime.datetime(year, month, endDate)

    # TODO: Parameterize variable_name
    snr = reader.aggregate(variable_name="ddm_snr", grid=grid, start_date=d1, end_date=d2)

    # Plot
    bbox_grid_xmin, bbox_grid_ymin = grid.lonlat2cr(reader.xmin, reader.ymin)
    bbox_grid_xmax, bbox_grid_ymax = grid.lonlat2cr(reader.xmax, reader.ymax)

    fig, ax = plt.subplots(figsize=(6, 6))

    cmap = plt.get_cmap("viridis")
    no_data_color = "gray"
    cmap.set_bad(color=no_data_color)

    pos = ax.imshow(snr, cmap=cmap, vmin=min, vmax=max)
    plt.colorbar(pos, ax=ax, label="DDM SNR")

    # Create a legend for missing data
    handles = [plt.Rectangle((0, 0), 1, 1, color="gray")]
    labels = ["No Data"]
    plt.legend(handles, labels)

    ax.set_title(f"DDM_SNR {d1.strftime('%Y-%m-%d')} to {d2.strftime('%Y-%m-%d')} grid={grid.name}")
    ax.set_xlim(bbox_grid_xmin, bbox_grid_xmax)
    ax.set_ylim(bbox_grid_ymin, bbox_grid_ymax)

    # Convert EASE2.0 coordinates to Lat/Long
    latitudes = [latitude for latitude in range(int(reader.ymin), int(reader.ymax) + 1)]
    longitudes = [longitude for longitude in range(int(reader.xmin), int(reader.xmax) + 1)]

    y_ticks = [grid.lat2r(lat) for lat in latitudes]
    x_ticks = [grid.lon2c(lon) for lon in longitudes]

    yticks = []
    for latitude in latitudes:
        if latitude > 0:
            yticks.append(f"{abs(latitude)}°N")
        elif latitude < 0:
            yticks.append(f"{abs(latitude)}°S")
        else:
            yticks.append(f"{abs(latitude)}°")

    xticks = []
    for longitude in longitudes:
        if latitude > 0:
            xticks.append(f"{abs(longitude)}°E")
        elif latitude < 0:
            xticks.append(f"{abs(longitude)}°W")
        else:
            xticks.append(f"{abs(longitude)}°")

    # Set the ticks on the X & Y axis to be the representative long/lat coordinates
    ax.set_xticks(x_ticks, xticks)
    ax.set_yticks(y_ticks, yticks)

    plt.savefig(figureName)


def animate(
    startDate: datetime,
    endDate: datetime,
    monthlyIntervals: int = 2,
    frameDuration: int = 1000,
    gridType: GridType = GridType.EASE2_G9km,
    generateDistribution: bool = False,
):
    """
    Creates and saves a GIF animation by creating monthlyIntervals of figures per month from the startDate to endDate.

    Args:
        startDate (datetime): Start date of animation. Animation will begin at the beginning of the selected month.
        endDate (datetime): End date of animation. Animation will end at the end of the selected month.
        monthlyIntervals (int): Number of frames per month of animation (default=2)
        frameDuration (int): ms between frames (default=1000)
        gridType (GridType): EASE2 GridType describing size of pixel footprint (default=EASE2_G9km)
        generateDistribution (bool): Boolean to generate a histogram of the dataset (default=False)

    Returns:
        None: Saves GIF animation to DDM_SNR_YYYYMMDD(start)-YYYMMDD(end)_gridResolutioN.gif
    """

    figures = []
    grid = EASE2GRID(gridType)
    plotVariable = "ddm_snr"

    figurePath, animationPath = generateAnimationFileStructure()

    file_base = (
        plotVariable.upper()
        + "_"
        + str(startDate.year)
        + f"{startDate.month:02}"
        + "-"
        + str(endDate.year)
        + f"{endDate.month:02}"
        + "_"
        + str(int(grid.res))
        + "_"
        + str(monthlyIntervals)
    )

    gif_name = file_base + ".gif"
    gif_path = Path.joinpath(animationPath, gif_name)

    if not gif_path.exists():
        print(f"Generating Animation {gif_name}")

        # Collect metadata on the requested variable
        print(f"Calculating metadata for {plotVariable}")
        metadata = reader.metadata(variable_name=plotVariable, grid=grid, start_date=startDate, end_date=endDate)
        min = 0
        # Select only the top 99% of data to extract outliers; used for the colorbar max
        max = round(np.nanpercentile(metadata["data"], 99))

        if generateDistribution:
            distribution_file = file_base + "_dist.png"
            genDistribution(metadata["data"], distribution_file, plotVariable)

        currentDate = startDate
        # Iterate through each month of the animation
        while currentDate < endDate:
            monthIntervals = createMonthlyIntervals(currentDate.year, currentDate.month, monthlyIntervals)

            # Create a figure for each interval of the month
            for dateInterval in monthIntervals:
                figName = (
                    plotVariable.upper()
                    + "_"
                    + str(currentDate.year)
                    + f"{currentDate.month:02}"
                    + f"{dateInterval[0]:02}"
                    + "-"
                    + str(currentDate.year)
                    + f"{currentDate.month:02}"
                    + f"{dateInterval[1]:02}"
                    + "_"
                    + f"{str(int(grid.res))}"
                    + "_max-"
                    + f"{str(int(max))}"
                    + ".png"
                )
                monthPath = getMonthFilePath(currentDate.year, currentDate.month, figurePath)
                figPath = Path.joinpath(monthPath, figName)
                if not figPath.exists():
                    print(f"Generating Figure {figName}")
                    generateFigure(
                        figPath, currentDate.year, currentDate.month, dateInterval[0], dateInterval[1], grid, max, min
                    )
                else:
                    print(f"Figure Previously Generated {figName}")
                figures.append(figPath)

            # Increment the current month
            if currentDate.month == 12:
                currentDate = datetime.datetime(currentDate.year + 1, 1, 1)
            else:
                currentDate = datetime.datetime(currentDate.year, currentDate.month + 1, 1)

        # Create frames of animation
        frames = []
        frameDurations = []
        for file_name in figures:
            frames.append(imageio.v3.imread(file_name))
            frameDurations.append(frameDuration)
        # Save gif
        imageio.mimsave(gif_path, frames, duration=frameDurations)
        print(f"Animation saved to {gif_path}")
    else:
        print(f"Animation Previously Generated {gif_path}")


# startDate = datetime.datetime(2023, 1, 1)
# endDate = datetime.datetime(2023, 2, 28)
# animate(startDate, endDate, gridType=GridType.EASE2_G9km)

# TODO:
# 1. Run via command line
# 2. Notebook version --- hardcode animations and figures to go to root of cygnss_wetlands
