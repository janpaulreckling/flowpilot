.PHONY: data check serve ui ui-check demo

data:      ## simulate the synthetic dataset, build the analytics store, run the monitor
	uv run flowpilot generate
	uv run flowpilot monitor

check:     ## lint, type-check and test
	uv run ruff check .
	uv run mypy src tests scripts
	uv run pytest

serve:     ## run the API on http://localhost:8000
	uv run flowpilot serve

ui:        ## run the UI on http://localhost:5173 (needs `make serve` for live data)
	cd frontend && npm run dev

ui-check:  ## typecheck, lint, test and build the UI
	cd frontend && npm run typecheck && npm run lint && npm test && npm run build

demo:      ## export the static demo and run the end-to-end journey on it
	uv run python scripts/export_demo.py
	cd frontend && npm run build:demo && npm run e2e
