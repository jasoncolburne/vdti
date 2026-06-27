.PHONY: all lint-terminology lint-docs lint-drawings

# Phase 0 — only lint-terminology, lint-docs, and lint-drawings are meaningful.
# Additional targets (fmt, clippy, test, build, etc.) land alongside the Cargo
# workspace in Phase 1.

all: lint-terminology lint-docs lint-drawings

lint-terminology:
	@./scripts/lint-terminology.sh

lint-docs:
	@./scripts/check-doc-xrefs.py

lint-drawings:
	@./scripts/lint-drawings.py
