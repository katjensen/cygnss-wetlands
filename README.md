# cygnss-wetlands
A repo dedicated to investigating global inundation patterns with NASA CYGNSS observations and other supporting data sources.

---
## Installation

This project's environment is managed with Poetry. Learm more about its [basic usage](https://python-poetry.org/docs/basic-usage/)

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

(b) Instruct Poetry to use a conda (or pyenv, etc) python version as it's base. A new virtual env will be created and managed by Poetry directly. You'll need to point it at the python executable. For example:  

```bash
poetry env use /opt/homebrew/Caskroom/miniconda/base/envs/base-python-3.9/bin/python3
```

### 4. Install package

You can install project dependencies, along with pre-commit git hooks, by:
```bash
make install
```

If you want, you may install this `cygnss-wetlands` library in editable mode by:
```bash
pip install -e .
```

### 5. Some additional tips about Poetry
To add a package to your project using poetry CLI,
```bash
poetry add "[your_package]"
```

You can also manually update `pyproject.toml` to include a new dependency (or change Python verions or existing dependency versions) manually. This will require you to recreate the `poetry.lock` file in the project, which you can do by following the command below. 
```bash
poetry update
```