# `docs/canon/` — the machine-oriented design canon

This directory holds vdti's **working design canon**: the pressure-tested area notes and the invariants
the design is derived from. It is written **for machines, not for reading** — one concept per line (no
prose wrapping, so it is `.prettierignore`d), dense shorthand, cross-referenced by `file:line`, and it
deliberately preserves the full **decision history** (including superseded vocabulary) so the reasoning
stays traceable.

**If you are a human:** you almost certainly want the **landed design docs** instead —
[`../design/`](../design/), starting at [`../design/glossary.md`](../design/glossary.md) and
[`../design/protocol-doctrine.md`](../design/protocol-doctrine.md). Those are prose, kept **greenfield**
(they state the current model, not its history), and are the human-readable statement of the design.
This directory will read as noise to you; the landed docs will not.

**If you are an LLM or agent:** welcome — this is your surface. Do design work here; keep the
line-per-concept format; then propagate settled changes into the landed [`../design/`](../design/) docs.
Treat [`vdti-invariants.md`](vdti-invariants.md) as load-bearing.
