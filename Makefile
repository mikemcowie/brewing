_:
	echo "make what?" && exit 1

lint-fix:
	uv run ruff format
	uv run ruff check --fix --unsafe-fixes

.PHONY: docs


docs-sync:
	uv sync --exact --all-groups

docs: docs-sync
	uv run mkdocs serve

docs-build: docs-sync
	uv run mkdocs build
