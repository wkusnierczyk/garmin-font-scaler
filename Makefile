PYTHON := python3
PIP := pip

.PHONY: all clean install test build perf

all: install test

install:
	$(PIP) install --upgrade pip
	$(PIP) install -e .[dev]
	$(PIP) install pytest pytest-mock

build:
	$(PIP) install build
	$(PYTHON) -m build

test:
	pytest tests/test_unit.py tests/test_integration.py -v

perf:
	pytest tests/test_performance.py -s

clean:
	rm -Rf dist/ build/ *.egg-info */*.egg-info .pytest_cache
	find . -name "*.egg-info" -type d -exec rm -rf {} +
	find . -name "__pycache__" -type d -exec rm -rf {} +
	find . -name "resources-round-*" -type d -exec rm -rf {} +