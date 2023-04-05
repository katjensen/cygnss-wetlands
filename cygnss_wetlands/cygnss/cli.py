import datetime
from pathlib import Path

import click

from cygnss_wetlands import __version__


@click.group()
@click.version_option(__version__)
@click.pass_context
def main(
    ctx,
):
    # we can pass context object info to subcommands here if we want?
    # e.g. ctx.obj["start_time"] = datetime.datetime.utcnow()
    pass


def callback_datetime(value: str) -> datetime.datetime:
    try:
        return datetime.datetime.strptime(value, "%Y-%m-%d")
    except ValueError as e:
        raise click.BadParameter(str(e))


@main.command(help="Download local copies of CYGNSS data products from NASA PODAAC HTTP site (not s3 - for now)")
@click.option(
    "--level",
    required=True,
    type=click.Choice(
        [
            "L1",
        ]
    ),
    help="Data product level",
)
@click.option(
    "--version",
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
    help="Destination path for output files(s)",
)
@click.pass_context
def download(
    ctx,
    level: str,
    version: Path,
    start_date: datetime.datetime,
    end_date: datetime.datetime,
    output_dir: Path,
):
    pass


def entry():
    # pass in an empty context dictionary -- this allows us to pass attributes to sub-commands!
    main(obj={})
