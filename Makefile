# AlphaMo Makefile — convenience wrappers around the canonical CLI surface.
#
# Sprint 16: the canonical answer to "how do I launch AlphaMo?" is now
# recorded in this file plus the README quickstart. Every target below
# is equivalent to a one-line command you could also run by hand; the
# Makefile exists for muscle memory and discoverability, not because
# anything inside it is privileged.

.PHONY: help install install-dev test doctor run harvest clean

help:  ## Print this help.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

install:  ## Install runtime dependencies (no dev extras).
	pip install -e .

install-dev:  ## Install runtime + dev dependencies (pytest, etc.).
	pip install -e '.[dev]'

test:  ## Run the full test suite.
	pytest -q

doctor:  ## Pre-flight env check — verify .env, dependencies, paths.
	alphamo doctor

run:  ## Launch a 30-generation production run with default HP.
	alphamo run --generations 30

harvest:  ## Build the handoff document for the most recent completed run.
	alphamo harvest

clean:  ## Remove caches, build artifacts, and SQLite WAL files.
	find . -type d -name __pycache__ -prune -exec rm -rf {} + ;
	find . -type d -name '.pytest_cache' -prune -exec rm -rf {} + ;
	find . -type d -name '*.egg-info' -prune -exec rm -rf {} + ;
	find . -type f -name '*.db-journal' -delete ;
