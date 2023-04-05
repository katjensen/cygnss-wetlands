from pathlib import Path

import yaml

# Import config params
config_path = Path(__file__).resolve().parent / "config.yaml"
with open(config_path) as f:
    config_dict = yaml.load(f, Loader=yaml.FullLoader)
