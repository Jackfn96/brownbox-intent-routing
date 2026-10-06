.PHONY: all format lint type-check test parse reading-sample discover

# Run after every change: format, lint, type-check, tests.
all: format lint type-check test

format:
	uv run ruff format .

lint:
	uv run ruff check .

type-check:
	uv run mypy src tests

test:
	uv run pytest -q

parse:
	uv run python -m brownbox.parse

reading-sample:
	uv run python -m brownbox.reading_sample

discover:
	uv run python -m brownbox.discover
