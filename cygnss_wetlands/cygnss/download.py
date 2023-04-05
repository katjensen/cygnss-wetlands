import base64
import datetime
import json
from pathlib import Path
from typing import Dict

import requests

from cygnss_wetlands import creds
from cygnss_wetlands.cygnss import config
from cygnss_wetlands.enums import CygnssProductLevel

### NOTE: S3 Access only works from AWS region aws-west-2
# For now - let's just use old-fashioned HTTP download links


def get_s3_credentials(s3_endpoint: str = "https://archive.podaac.earthdata.nasa.gov/s3credentials") -> Dict:
    """
    Makes the Oauth calls to authenticate with EDS and return a set of s3
        same-region, read-only credntials.
    """
    login_resp = requests.get(s3_endpoint, allow_redirects=False)
    login_resp.raise_for_status()

    auth = f"{creds.EARTH_DATA_USERNAME}:{creds.EARTH_DATA_PASSWORD}"
    encoded_auth = base64.b64encode(auth.encode("ascii"))

    auth_redirect = requests.post(
        login_resp.headers["location"],
        data={"credentials": encoded_auth},
        headers={"Origin": s3_endpoint},
        allow_redirects=False,
    )
    auth_redirect.raise_for_status()

    final = requests.get(auth_redirect.headers["location"], allow_redirects=False)

    results = requests.get(s3_endpoint, cookies={"accessToken": final.cookies["accessToken"]})
    results.raise_for_status()

    return json.loads(results.content)


def http_download_by_date(product_level: CygnssProductLevel, datetime: datetime.datetime, dest_dir: Path):
    """
    Download CYGNSS data files to local from PODAAC HTTP site

    Args:
        product_level (str): _description_
        datetime (datetime.datetime): _description_
        dest_dir (Path): _description_
    """
