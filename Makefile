_:
	echo "make what?" && exit 1

lint-fix:
	uv run ruff format
	uv run ruff check --fix --unsafe-fixes

.PHONY: docs

docs:
	uv sync --group docs
	uv run --group docs mkdocs build
	uv run --group docs mkdocs serve
