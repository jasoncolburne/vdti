.PHONY: all lint-terminology lint-docs

# Phase 0 — only lint-terminology and lint-docs are meaningful. Additional
# targets (fmt, clippy, test, build, etc.) land alongside the Cargo workspace
# in Phase 1.

all: lint-terminology lint-docs

lint-terminology:
	@./scripts/lint-terminology.sh

lint-docs:
	@./scripts/check-doc-xrefs.py
