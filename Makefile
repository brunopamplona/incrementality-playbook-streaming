.PHONY: install test stage1 economics data clean

install:
	pip install -e ".[dev]"

test:
	pytest -q

# Stage 1+2: simulate data, compare naive attribution vs. ground truth
stage1:
	python scripts/run_stage1.py

data:
	python scripts/export_datasets.py

economics:
	python scripts/run_economics.py

clean:
	rm -rf data/*.csv.gz docs/img build *.egg-info .pytest_cache
