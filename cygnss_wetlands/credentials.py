import os
from pathlib import Path

from dotenv import load_dotenv

# should not fail if '.env' doesn't exist, we just fall back on user env vars
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(env_path, override=False)


class Credentials:
    """Load credentials information"""

    # For now assuming we can read from project root '.env' file or env vars to pass in credentials

    try:
        EARTHDATA_USERNAME = os.environ["EARTHDATA_USERNAME"]
        EARTHDATA_PASSWORD = os.environ["EARTHDATA_PASSWORD"]

    except KeyError:
        EARTHDATA_USERNAME = None
        EARTHDATA_PASSWORD = None

        raise Warning("EARTHDATA login information could not be found in environment variables")
