.PHONY: dev test lint build docker-up

dev:
	uvicorn main:app --reload --app-dir backend

test:
	python -m pytest

lint:
	ruff check backend tests
	mypy backend

build:
	cd frontend && npm run build

docker-up:
	docker compose up --build
