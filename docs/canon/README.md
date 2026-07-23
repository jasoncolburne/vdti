# `docs/canon/` — working notes not yet encoded

The machine-oriented design canon that once lived here is **retired**: every encoded area note and
the invariants doc were propagated into the landed design docs and then removed. Their full
decision history — dated decisions, dropped alternatives, superseded vocabulary — remains browsable
at the git tag **`canon-final`**.

**The design surface is [`../design/`](../design/)** — prose, greenfield (it states the current
model, not its history), no jargon. Humans and LLMs alike should work from there, starting at
[`../design/README.md`](../design/README.md).

What remains in this directory is the **not-yet-encoded** working set, still line-per-concept and
prettier-exempt:

- [`vdti-area-vdtid-services.md`](vdti-area-vdtid-services.md) — the services / architecture area
  (the design's leading edge; no landed counterpart yet).
- [`vdti-implementation-notes.md`](vdti-implementation-notes.md) — build-shaping decisions that
  are deliberately not doctrine (storage, transport, locking).
- [`supplemental/`](supplemental/) — ideas and external-comparison reference notes.

When an area here is encoded into [`../design/`](../design/), its note gets the same treatment:
delete it, and let git history carry the trail.
