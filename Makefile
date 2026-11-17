.PHONY: data check serve ui ui-check

data:      ## simulate the synthetic dataset and build the analytics store
	uv run flowpilot generate

check:     ## lint, type-check and test
	uv run ruff check .
	uv run mypy src tests
	uv run pytest

serve:     ## run the API on http://localhost:8000
	uv run flowpilot serve

ui:        ## run the UI on http://localhost:5173 (needs `make serve` for live data)
	cd frontend && npm run dev

ui-check:  ## typecheck, lint, test and build the UI
	cd frontend && npm run typecheck && npm run lint && npm test && npm run build
