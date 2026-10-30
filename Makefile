# Development workflow adapted from MuJoCo Menagerie; see UPSTREAM.md.
.PHONY: help install sync check test web-test all
MUJOCO_GL ?= egl
WEB := src/menagerie_x/workbench/web

help:
	@echo "make install  Install Python development and Workbench dependencies"
	@echo "make sync     Refresh native model and scene entrypoints"
	@echo "make check    Check generated native entrypoints"
	@echo "make test     Run Python and native scene regression checks"
	@echo "make web-test Run Workbench JavaScript tests"
	@echo "make all      Run all verification"

install:
	uv sync --extra dev
	npm ci --prefix $(WEB)

sync:
	uv run --extra dev python scripts/sync-menagerie.py

check:
	uv run --extra dev python scripts/sync-menagerie.py --check

test:
	MUJOCO_GL=$(MUJOCO_GL) uv run --extra dev python -m unittest discover -s tests

web-test:
	node --test $(WEB)/*.test.js

all: check test web-test
