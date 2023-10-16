# cygnss-wetlands
A repo dedicated to investigating global inundation patterns with NASA CYGNSS observations and other supporting data sources.

---
## Installation

This project's dependencies are managed with Poetry. Learm more about its [basic usage](https://python-poetry.org/docs/basic-usage/)

### 1. Clone Repo
```bash
git clone git@github.com:katjensen/cygnss-wetlands.git
```

### 2. Install Poetry (if not already installed on system) 
```bash
curl -sSL https://install.python-poetry.org | python3 -
```

### 3. Set up Python environmentment
Two options here:

(a) Create and activate a fresh, new python environment using your Python environment manager of choice (e.g conda). This project requires Python version 3.9 or greater.

```bash
conda create -n cygnss-wetlands python=3.9
conda activate cygnss-wetlands
```

 or 

(b) Instruct Poetry to use an existing conda (or pyenv, etc) python version as it's base. A new virtual env will be created and managed by Poetry directly. You'll need to point it at the python executable. For example:  

```bash
poetry env use /opt/homebrew/Caskroom/miniconda/base/envs/base-python-3.9/bin/python3
```

If you are not using conda, you might want to enable the `virtualenvs.in-project option` for this project (optional) by running in the project root directory:
```
 poetry config virtualenvs.in-project true
```

This will cause Poetry to create new environments in $project_root/.venv/. If you rename the project directory the environment should continue to work.

### 4. Install package

You can install project dependencies, along with pre-commit git hooks, by:
```bash
make install
```

### 5. Activate your environment
If you are NOT using conda to manage your environment, when working on this project (now and in the future), activate your environment by:
```bash
poetry shell
```
This command creates a child process that inherits from the parent Shell but will not alter its environment. It encapsulates and restrict any modifications you will perform to your project environment.

If you want, you may install this `cygnss-wetlands` library in editable mode once dependencies have been installed (and your environment is activated) by:
```bash
pip install -e .
```

### 6. Some additional tips about Poetry
To add a package to your project using poetry CLI,
```bash
poetry add "[your_package]"
```

You can also manually update `pyproject.toml` to include a new dependency (or change Python verions or existing dependency versions) manually. This will require you to recreate the `poetry.lock` file in the project, which you can do by following the command below. 
```bash
poetry update
```

---
## Credentials and Environment Variables
If using the download tool, you will need NASA Earthdata account credentials either stored in a `.env` file in this project's root folder or added to your local environment:

```
EARTHDATA_USERNAME=XXXXXXX
EARTHDATA_PASSWORD=XXXXXXX
```

---
## CLI Tools

### Download CYGNSS data
A little command line tool can help you download files from PODAAC HTTP site. Only currently supports L1 products.
TODO: Upgrade the downloader to pull from S3 bucket -- at the time of development, this was only accessible in AWS region aws-west-2

For example, to download one month's worth of L1 files from Jan 2020, you can run :
```
cygnss download --product_level=L1 --start_date=2020-01-01 --end_date=2020-01-31 --dest_dir=/path/to/cygnss/data
```

### Aggregating L1 to Grid
Not Implemented: Aggregating CYGNSS L1 data to a regular grid and write to file

---
## Remaining To-Do List
There are components of previous work that are still being added here - plus some valuable upgrades - in the works!

1. Logging and unit testing
2. Custom DDM observables derived from BRCS (e.g. leading and trailing edge slope)
3. Upgrade Download tool to pull from HTTP site to AWS S3 and Reader infrastructure to read from the cloud (switch to using xarray !) - this would help us not have to download all data files locally (but last I checked-- this was still only available to users in aws-west-2 region)
4. Add support for additional grid types (e.g. UTM, Geographic Coordinates) - currently only support EASEGRIDs
5. Add CLI support to aggregate() for writing out to file
6. Sentinel-1 and PALSAR-2 support -- needs scoping !