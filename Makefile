.PHONY: all lint-terminology lint-docs fmt-md fmt-md-check working-tarball

# Phase 0 — lint-terminology, lint-docs, and fmt-md-check are the
# meaningful targets. Markdown formatting (prettier) is wired now; the Rust
# targets (cargo fmt/clippy/test/build) land alongside the Cargo workspace in
# Phase 1.

# Pinned so local `fmt-md` and CI `fmt-md-check` agree byte-for-byte. The canon
# under docs/canon/ (+ the .working/ surface) is exempt via .prettierignore (kept line-per-concept).
PRETTIER := npx --yes prettier@3.3.3

# Working surface snapshot
WORKING_DIR := .working
WORKING_MTIME := 202001010000
WORKING_TARBALL := working.tar.xz
# Snapshot every live .working/*.md, minus the exclusions below. The non-recursive
# glob already skips .working/archived/ — demote consumed reviews / landed PR bodies
# there and they drop out of the snapshot with no edit to this file.
WORKING_EXCLUDE := jason-notes.md
WORKING_FILES := $(filter-out $(WORKING_EXCLUDE),$(notdir $(wildcard $(WORKING_DIR)/*.md)))

all: lint-terminology lint-docs fmt-md-check

lint-terminology:
	@./scripts/lint-terminology.sh

lint-docs:
	@./scripts/check-doc-xrefs.py

# Refresh the working-surface snapshot (working.tar.xz) from .working/.
working-tarball:
	@rm -rf .work-stage && mkdir .work-stage
	@cd $(WORKING_DIR) && cp $(WORKING_FILES) $(CURDIR)/.work-stage/
	@touch -t $(WORKING_MTIME) .work-stage/*
	@COPYFILE_DISABLE=1 tar --no-mac-metadata -cJf $(WORKING_TARBALL) -C .work-stage $(sort $(WORKING_FILES))
	@rm -rf .work-stage
	@echo "wrote $(WORKING_TARBALL): $$(wc -c < $(WORKING_TARBALL) | tr -d ' ') bytes from $(words $(WORKING_FILES)) working-surface files"

# Reflow human-read Markdown (docs/, root, .github/) to .prettierrc (100 cols).
fmt-md:
	@$(PRETTIER) --write '**/*.md'

# Gate / CI check — fails if any tracked Markdown isn't prettier-formatted.
fmt-md-check:
	@$(PRETTIER) --check '**/*.md'
