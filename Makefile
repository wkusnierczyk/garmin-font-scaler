PYTHON := python3
PIP := pip

.PHONY: all clean install test build perf lint format

# Default target: install dependencies, lint code, and run tests
all: install lint test

install:
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]
	$(PIP) install pytest pytest-mock ruff

build:
	$(PIP) install build
	$(PYTHON) -m build

test:
	pytest tests/test_unit.py tests/test_integration.py -v

perf:
	pytest tests/test_performance.py -s

# Check for issues (does not modify files)
lint:
	ruff check .
	ruff format --check .

# Fix issues and reformat code (modifies files)
format:
	ruff check --fix .
	ruff format .

clean:
	rm -rf dist/ build/ .pytest_cache
	find . -name "*.egg-info" -type d -exec rm -rf {} +
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "resources-round-*" -type d -exec rm -rf {} +