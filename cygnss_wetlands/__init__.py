import importlib.metadata

from .credentials import Credentials

# import package version from root 'pyproject.toml' file
__version__ = importlib.metadata.version("cygnss-wetlands")

# initialize credentials objects for easy access
creds = Credentials()
