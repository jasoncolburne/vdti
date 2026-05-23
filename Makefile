.PHONY: all lint-terminology

# Phase 0 — only lint-terminology is meaningful. Additional targets
# (fmt, clippy, test, build, etc.) land alongside the Cargo workspace
# in Phase 1.

all: lint-terminology

lint-terminology:
	@./scripts/lint-terminology.sh
