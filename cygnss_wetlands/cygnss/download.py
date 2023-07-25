import base64
import datetime
import json
import shutil
import urllib
from http.cookiejar import CookieJar
from pathlib import Path
from typing import Dict, List

import numpy as np
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

    auth = f"{creds.EARTHDATA_USERNAME}:{creds.EARTHDATA_PASSWORD}"
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


def http_download_by_date(
    product_level: CygnssProductLevel, date: datetime.datetime, dest_dir: Path, overwrite: bool = False
) -> List:
    """
    Download CYGNSS data files to local from PODAAC HTTP site

    Args:
        product_level (CygnssProductLevel):
        datetime (datetime.datetime)
        dest_dir (Path): Destination download directory
    """
    password_manager = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    password_manager.add_password(
        None, "https://urs.earthdata.nasa.gov", creds.EARTHDATA_USERNAME, creds.EARTHDATA_PASSWORD
    )

    # Create a cookie jar for storing cookies. This is used to store and return
    # the session cookie given to use by the data server (otherwise it will just
    # keep sending us back to Earthdata Login to authenticate).  Ideally, we
    # should use a file based cookie jar to preserve cookies between runs. This
    # will make it much more efficient.

    cookie_jar = CookieJar()

    # Install all the handlers
    opener = urllib.request.build_opener(
        urllib.request.HTTPBasicAuthHandler(password_manager), urllib.request.HTTPCookieProcessor(cookie_jar)
    )
    urllib.request.install_opener(opener)

    version_int = int(config[product_level.name]["product_version"].replace("v", "").replace(".", ""))
    spacecraft_id_list = np.arange(1, 8 + 1)

    success_download_list = []

    # Attempt to download file for given spacecraft
    # (not all spacecrafts necessarily have data for every day )
    for spacecraft_id in spacecraft_id_list:

        filename = (
            "cyg"
            + "{:02d}".format(spacecraft_id)
            + f".ddmi.s{date.strftime('%Y%m%d')}-000000-e{date.strftime('%Y%m%d')}-235959.{product_level.name.lower()}."
            f"power-brcs.a{version_int}.d{version_int + 1}.nc"
        )

        complete_filepath = dest_dir.joinpath(filename)

        if not complete_filepath.exists() or (complete_filepath.exists() and overwrite):

            url = f'{config["download"]["http"]}/CYGNSS_{product_level.name}_{config[product_level.name]["product_version"].upper()}/{filename}'

            try:
                # Create and submit the request. There are a wide range of exceptions that
                # can be thrown here, including HTTPError and URLError. These should be
                # caught and handled.
                request = urllib.request.Request(url)

                # save the file
                with urllib.request.urlopen(request) as response, open(complete_filepath, "wb") as f:
                    print(f"Downloading: {filename}")
                    shutil.copyfileobj(response, f)
                    success_download_list.append(dest_dir.joinpath(filename))

            except requests.exceptions.HTTPError as e:

                # handle any errors here
                print(f"Could not download file: {filename}, error: {e}")

        else:
            print(f"Skipping {filename}, local copy exists and overwrite not flagged")

    return success_download_list
