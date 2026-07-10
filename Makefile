.PHONY: install test lint type cov reproduce clean docker

install:
	pip install -e ".[dev]"
	pre-commit install

test:
	python -m pytest -q

cov:
	python -m pytest --cov=hdleval --cov-report=term-missing --cov-report=html

lint:
	ruff check src tests scripts
	ruff format --check src tests scripts

type:
	mypy src/hdleval

reproduce:
	python reproduce.py

benchmarks:
	python scripts/build_benchmarks.py

docker:
	docker build -t hdleval . && docker run --rm hdleval

clean:
	rm -rf .pytest_cache .mypy_cache htmlcov .coverage build dist *.egg-info
