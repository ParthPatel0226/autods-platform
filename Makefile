.PHONY: install run test lint format benchmark clean setup-data

# Install dependencies
install:
	pip install -r requirements.txt
	pip install -e .

install-dev:
	pip install -r requirements-dev.txt
	pip install -e .

# Run the Streamlit dashboard
run:
	streamlit run dashboard/app.py --server.port 8501

# Run the FastAPI prediction server
serve:
	uvicorn serving.api:app --host 0.0.0.0 --port 8000 --reload

# Run tests
test:
	pytest tests/unit/ -v --tb=short

test-integration:
	pytest tests/integration/ -v --tb=short -m integration

test-all:
	pytest tests/ -v --tb=short --cov=agents --cov=core --cov=data_connectors --cov-report=html

test-fast:
	pytest tests/unit/ -v --tb=short -x -q

# Code quality
lint:
	ruff check .
	mypy agents/ core/ --ignore-missing-imports

format:
	black .
	isort .
	ruff check --fix .

# Benchmarks
benchmark:
	python tests/benchmarks/run_benchmarks.py

# Download sample/benchmark datasets
setup-data:
	python scripts/download_sample_datasets.py

# Initialize databases
setup-db:
	python scripts/setup_database.py

# Full setup (first time)
setup: install setup-db setup-data
	@echo "AutoDS Platform setup complete!"
	@echo "Run 'make run' to start the dashboard."

# Clean generated files
clean:
	rm -rf __pycache__ */__pycache__ */*/__pycache__
	rm -rf .pytest_cache htmlcov .coverage
	rm -rf mlruns/*
	rm -rf logs/*
	rm -rf outputs/*
	rm -rf data/*.duckdb data/*.duckdb.wal
	rm -rf sessions/*.db sessions/chromadb
	find . -type f -name "*.pyc" -delete

# Generate demo GIF for README
demo:
	python scripts/generate_demo_gif.py
