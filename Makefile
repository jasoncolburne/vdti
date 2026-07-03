.PHONY: all lint-terminology lint-docs lint-diagrams lint-diagrams-prune fmt-md fmt-md-check canon-tarball

# Phase 0 — lint-terminology, lint-docs, lint-diagrams, and fmt-md-check are the
# meaningful targets. Markdown formatting (prettier) is wired now; the Rust
# targets (cargo fmt/clippy/test/build) land alongside the Cargo workspace in
# Phase 1.

# Pinned so local `fmt-md` and CI `fmt-md-check` agree byte-for-byte. The canon
# under .working/ is exempt via .prettierignore (kept line-per-concept).
PRETTIER := npx --yes prettier@3.3.3

# Canon snapshot — the pressure-tested design canon (.working/) bundled into docs/design/ as an xz
# tarball (best text ratio). Byte-stable: a fixed mtime + sorted members make xz output depend only
# on the canon content, so re-running with no canon change is a no-op diff. Run + commit when the
# canon moves: `make canon-tarball`. NOT in `make all` — it's an explicit snapshot refresh.
CANON_DIR := .working
CANON_MTIME := 202001010000
CANON_TARBALL := docs/design/canon.tar.xz
CANON_FILES := vdti-invariants.md vdti-repair-completeness-proof.md \
	vdti-area-delegation.md vdti-area-document-policy.md vdti-area-federation-witnessing.md \
	vdti-area-iel.md vdti-area-kel.md vdti-area-multi-party-documents.md vdti-area-sel.md \
	vdti-area-vdtid-services.md vdti-federation-inception-reference.md vdti-implementation-notes.md

# Split from canon so canon.tar.xz stays canon-only: the working-surface snapshot
# (working.tar.xz) and the supplemental refs (docs/supplemental.tar.xz). Same .working/ source
# + deterministic mtime as canon-tarball.
WORKING_TARBALL := working.tar.xz
WORKING_FILES := 00-INDEX.md design-resume.md warm-resume.md vdti-1-roadmap.md
SUPP_TARBALL := docs/supplemental.tar.xz
SUPP_FILES := vdti-keri-acdc-comparison.md vdti-lib-storage-stub.md vdti-token-store-idea.md

all: lint-terminology lint-docs lint-diagrams fmt-md-check

lint-terminology:
	@./scripts/lint-terminology.sh

lint-docs:
	@./scripts/check-doc-xrefs.py

lint-diagrams:
	@./scripts/lint-diagrams.py

# Hygiene: delete isDeleted (soft-removed) elements Excalidraw leaves in the JSON.
# Byte-faithful via jq — touches nothing else, so it never changes a lint verdict.
lint-diagrams-prune:
	@./scripts/lint-diagrams.py --prune

# Refresh the committed canon snapshot (docs/design/canon.tar.xz) from .working/.
canon-tarball:
	@rm -rf .canon-stage && mkdir .canon-stage
	@cd $(CANON_DIR) && cp $(CANON_FILES) $(CURDIR)/.canon-stage/
	@touch -t $(CANON_MTIME) .canon-stage/*
	@COPYFILE_DISABLE=1 tar --no-mac-metadata -cJf $(CANON_TARBALL) -C .canon-stage $(sort $(CANON_FILES))
	@rm -rf .canon-stage
	@echo "wrote $(CANON_TARBALL): $$(wc -c < $(CANON_TARBALL) | tr -d ' ') bytes from $(words $(CANON_FILES)) canon files"

# Refresh the working-surface snapshot (working.tar.xz) from .working/.
working-tarball:
	@rm -rf .work-stage && mkdir .work-stage
	@cd $(CANON_DIR) && cp $(WORKING_FILES) $(CURDIR)/.work-stage/
	@touch -t $(CANON_MTIME) .work-stage/*
	@COPYFILE_DISABLE=1 tar --no-mac-metadata -cJf $(WORKING_TARBALL) -C .work-stage $(sort $(WORKING_FILES))
	@rm -rf .work-stage
	@echo "wrote $(WORKING_TARBALL): $$(wc -c < $(WORKING_TARBALL) | tr -d ' ') bytes from $(words $(WORKING_FILES)) working-surface files"

# Refresh the supplemental-refs snapshot (docs/supplemental.tar.xz) from .working/.
supplemental-tarball:
	@rm -rf .supp-stage && mkdir .supp-stage
	@cd $(CANON_DIR) && cp $(SUPP_FILES) $(CURDIR)/.supp-stage/
	@touch -t $(CANON_MTIME) .supp-stage/*
	@COPYFILE_DISABLE=1 tar --no-mac-metadata -cJf $(SUPP_TARBALL) -C .supp-stage $(sort $(SUPP_FILES))
	@rm -rf .supp-stage
	@echo "wrote $(SUPP_TARBALL): $$(wc -c < $(SUPP_TARBALL) | tr -d ' ') bytes from $(words $(SUPP_FILES)) supplemental files"

# Refresh all three snapshots.
tarballs: canon-tarball working-tarball supplemental-tarball

# Reflow human-read Markdown (docs/, root, .github/) to .prettierrc (100 cols).
fmt-md:
	@$(PRETTIER) --write '**/*.md'

# Gate / CI check — fails if any tracked Markdown isn't prettier-formatted.
fmt-md-check:
	@$(PRETTIER) --check '**/*.md'
