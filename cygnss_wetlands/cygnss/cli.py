import datetime
import os
from pathlib import Path

import click

from cygnss_wetlands import __version__
from cygnss_wetlands.cygnss.download import http_download_by_date
from cygnss_wetlands.enums import CygnssProductLevel


@click.group()
@click.version_option(__version__)
@click.pass_context
def main(
    ctx,
):
    # we can pass context object info to subcommands here if we want?
    # e.g. ctx.obj["start_time"] = datetime.datetime.utcnow()
    pass


def callback_datetime(ctx, param, value) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d")
    except ValueError as e:
        raise click.BadParameter(str(e))


def callback_product_level(ctx, param, value) -> CygnssProductLevel:
    try:
        return CygnssProductLevel.from_str(value)
    except ValueError as e:
        raise click.BadParameter(str(e))


@main.command(help="Download local copies of CYGNSS data products from NASA PODAAC HTTP site (not s3 - for now)")
@click.option(
    "--product_level",
    required=True,
    type=click.Choice(
        [
            "L1",
        ]
    ),
    callback=callback_product_level,
    help="Data product level",
)
@click.option(
    "--product_version",
    type=click.Choice(["v2.1", "v3.0", "v3.1"]),
    default="v3.1",
    show_default=True,
    help="Product version",
)
@click.option(
    "--start_date",
    callback=callback_datetime,
    required=True,
    help="Start date for records to download, YYYY-MM-DD format",
)
@click.option(
    "--end_date",
    callback=callback_datetime,
    required=True,
    help="End date (inclusive) for records to download, YYYY-MM-DD format",
)
@click.option(
    "--dest_dir",
    type=click.Path(exists=True, path_type=Path),
    required=True,
    help="Destination parent directory. Files will download to nested location within this parent directory, following: "
    "PRODUCT_LEVEL / PRODUCT_VERSION / YYYY / MM / DD ",
)
@click.option(
    "--overwrite",
    type=click.BOOL,
    is_flag=True,
    default=False,
    show_default=True,
    help="Flag for overwriting existing files",
)
@click.pass_context
def download(
    ctx,
    product_level: str,
    product_version: Path,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    dest_dir: Path,
    overwrite: bool,
):

    # Iterate over each date
    date_list = [start_date + datetime.timedelta(days=x) for x in range((end_date - start_date).days + 1)]

    for date in date_list:

        # Organize destination subfolder, change current work directory to this
        dest_subdir = dest_dir.joinpath(
            product_level.name, product_version, str(date.year), "{:02d}".format(date.month), "{:02d}".format(date.day)
        )

        if not dest_subdir.exists():
            os.makedirs(dest_subdir)

        # Download all files from this date
        successFileList, failedFileList = http_download_by_date(product_level, date, dest_subdir, overwrite)

    print(f"Successfully downloaded: {successFileList}")
    print(f"Failed to download: {failedFileList}")


def entry():
    # pass in an empty context dictionary -- this allows us to pass attributes to sub-commands!
    main(obj={})
