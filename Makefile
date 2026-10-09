.PHONY: all format lint type-check test parse reading-sample discover ontology label label-assisted prelabel cases eval-cases eval label-locked eval-locked

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

ontology:
	uv run python -m brownbox.ontology

label:
	uv run python -m brownbox.label

cases:
	uv run python -m brownbox.cases

label-assisted:
	uv run python -m brownbox.label --assisted

label-locked:
	uv run python -m brownbox.label --locked

prelabel:
	uv run python -m brownbox.prelabel

eval-cases:
	uv run python -m brownbox.evaluate cases

eval:
	uv run python -m brownbox.evaluate practice

eval-locked:
	uv run python -m brownbox.evaluate locked
