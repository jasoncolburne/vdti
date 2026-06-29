.PHONY: all lint-terminology lint-docs lint-drawings fmt-md fmt-md-check

# Phase 0 — lint-terminology, lint-docs, lint-drawings, and fmt-md-check are the
# meaningful targets. Markdown formatting (prettier) is wired now; the Rust
# targets (cargo fmt/clippy/test/build) land alongside the Cargo workspace in
# Phase 1.

# Pinned so local `fmt-md` and CI `fmt-md-check` agree byte-for-byte. The canon
# under .working/ is exempt via .prettierignore (kept line-per-concept).
PRETTIER := npx --yes prettier@3.3.3

all: lint-terminology lint-docs lint-drawings fmt-md-check

lint-terminology:
	@./scripts/lint-terminology.sh

lint-docs:
	@./scripts/check-doc-xrefs.py

lint-drawings:
	@./scripts/lint-drawings.py

# Reflow human-read Markdown (docs/, root, .github/) to .prettierrc (100 cols).
fmt-md:
	@$(PRETTIER) --write '**/*.md'

# Gate / CI check — fails if any tracked Markdown isn't prettier-formatted.
fmt-md-check:
	@$(PRETTIER) --check '**/*.md'
