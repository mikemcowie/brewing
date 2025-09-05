_:
	echo "make what?" && exit 1

lint-fix:
	uv run ruff format
	uv run ruff check --fix --unsafe-fixes
