.PHONY: help install install-dev lint format test precommit docker-build docker-up docker-down docker-logs api-train api-up up down logs clean

help:
	@echo "up            - start api + frontend in docker (set TRAIN=1 to train models first)"
	@echo "down          - stop api + frontend (and trainer if running)"
	@echo "logs          - tail api + frontend logs"
	@echo "install       - install runtime dependencies"
	@echo "install-dev   - install dev dependencies and pre-commit hooks"
	@echo "lint          - run ruff lint on src/ and tests/"
	@echo "format        - auto-format with ruff"
	@echo "test          - run pytest"
	@echo "precommit     - run all pre-commit hooks on all files"
	@echo "docker-build  - build all docker images"
	@echo "docker-up     - start JupyterLab container on :8888"
	@echo "docker-down   - stop all containers"
	@echo "docker-logs   - tail JupyterLab logs"
	@echo "api-train     - train models locally (no docker) and persist to models/"
	@echo "api-up        - run FastAPI server locally (no docker) on :8000"
	@echo "clean         - remove caches"

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt
	pre-commit install

lint:
	ruff check src/ tests/

format:
	ruff format src/ tests/
	ruff check --fix src/ tests/

test:
	pytest

precommit:
	pre-commit run --all-files

docker-build:
	docker compose --profile train --profile jupyter build

docker-up:
	docker compose --profile jupyter up -d jupyter
	@echo "JupyterLab -> http://localhost:8888"

docker-down:
	docker compose --profile train --profile jupyter down

docker-logs:
	docker compose logs -f jupyter

up:
ifneq ($(strip $(TRAIN)),)
	docker compose --profile train run --rm --build trainer
endif
	docker compose up -d --build api frontend
	@echo "API      -> http://localhost:8000"
	@echo "Frontend -> http://localhost:3000"

down:
	docker compose --profile train down

logs:
	docker compose logs -f api frontend

api-train:
	python -m scripts.train_and_save --ticker ^GSPC --start 2010-01-01 --end 2024-12-31

api-up:
	uvicorn src.api.main:app --reload --port 8000

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
