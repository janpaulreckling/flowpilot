.PHONY: data check serve

data:      ## simulate the synthetic dataset and build the analytics store
	uv run flowpilot generate

check:     ## lint, type-check and test
	uv run ruff check .
	uv run mypy src tests
	uv run pytest

serve:     ## run the API on http://localhost:8000
	uv run flowpilot serve
