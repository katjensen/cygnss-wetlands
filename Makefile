install:
	@echo "Installing..."
	poetry install
	poetry run pip install --upgrade pip
	poetry run pre-commit install

activate:
	@echo "Activating virtual environment"
	poetry shell