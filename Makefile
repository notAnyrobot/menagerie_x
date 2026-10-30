# Development workflow adapted from MuJoCo Menagerie; see UPSTREAM.md.
.PHONY: help install check test legacy-test web-test all
WEB := src/menagerie_x/workbench/web

help:
	@echo "make install     Install native Python development dependencies"
	@echo "make check       Check native family layout and XML style"
	@echo "make test        Load, step, and copy native models and scenes"
	@echo "make all         Run native acceptance checks (also run in CI)"
	@echo "make legacy-test Run deferred CLI/Workbench/URDF Python tests"
	@echo "make web-test    Run deferred Workbench JavaScript tests"

install:
	uv sync --locked --extra dev

check:
	uv run --locked --extra dev python -m unittest discover -s test -p '*_dir_test.py'

test:
	uv run --locked --extra dev python -m unittest discover -s test -p 'model_test.py'

legacy-test:
	uv run --locked --extra dev python -m unittest discover -s tests

web-test:
	node --test $(WEB)/*.test.js

all: check test
