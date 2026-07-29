.PHONY: all lint-terminology lint-docs fmt-md fmt-md-check toc toc-check working-tarball

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
WORKING_FILES := $(notdir $(wildcard $(WORKING_DIR)/*.md))

all: lint-tools lint-terminology lint-docs fmt-md-check toc-check

# grep-terms.pl once returned ZERO SILENTLY for any phrase containing a non-ASCII
# character (args arrive as bytes, files are read as characters), so sweeps for
# "≥ 2" or "(MINIMUM_PAGE_SIZE − 1)/2" read as clean when they were not. A silent
# wrong answer in a search tool is worse than a broken one, so assert it round-trips.
lint-tools:
	@./scripts/grep-terms.pl '≥ 2' -- docs/design/protocol-doctrine.md >/dev/null \
	  || { echo 'grep-terms.pl: non-ASCII phrase search is broken (see the decode_utf8 on @ARGV)'; exit 1; }

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

# Regenerate docs/design/TOC.md from the design tree's headings, then prettier-normalize
# so the committed TOC is the canonical (generator + prettier) form.
toc:
	@./scripts/generate-doc-toc.py
	@$(PRETTIER) --write docs/design/TOC.md >/dev/null

# Gate / CI check — regenerates the TOC and fails if it drifted from the committed copy.
toc-check: toc
	@git diff --exit-code -- docs/design/TOC.md \
	  || { echo "docs/design/TOC.md is out of date — run 'make toc' and commit the result." >&2; exit 1; }
