# Reading the VDTI design — a guide for agents

This directory is the **canonical specification** of VDTI. If you are an LLM doing substantive work
here — answering a question, extending the design, composing an application — this file is how to
read the surface without misreading it. The repo-wide conventions are the root
[`AGENTS.md`](../../AGENTS.md); this file is scoped to working with the design tree itself.

## The two entry modes

- **First pass — read in order.** [`README.md`](README.md) is the narrative reading order, built
  bottom-up by layer with a one-line summary per doc. Use it when you are new to the surface or the
  task spans layers.
- **Task-directed — go straight to the section.** [`TOC.md`](TOC.md) lists **every file and its
  top-level sections** as anchor links (deeper subsections live under those). Use it to jump to the
  owning section for a concept instead of re-reading whole documents. It is generated
  (`scripts/generate-doc-toc.py`) — regenerate it if you change headings.

Whichever mode you enter by, keep [`glossary.md`](glossary.md) at hand: every load-bearing term has
a one-line definition and a pointer to the doc that owns it. When a term surprises you, the glossary
is faster and more reliable than inference.

## Rules for reading

- **Read; don't reconstruct.** Protocol semantics live in these files, and recall — yours or a
  summary's — is stale or mis-encoded more often than it feels. Before making a structural claim,
  open the owning section (TOC.md gets you there in one hop). When docs and your priors disagree,
  the docs win; when docs and code disagree, the **design is canonical**.
- **One concept, one home.** Every mechanism has exactly one owning section; everything else points
  at it. Follow the pointer to the owner before relying on a summary you found elsewhere — summaries
  at non-owning sites are deliberately thin.
- **Load the cross-cutting carriers with your topic.** The design is interlocking:
  [`protocol-doctrine.md`](protocol-doctrine.md) (the cross-primitive rules),
  [`residuals.md`](residuals.md) (what is deliberately not solved, and at what price),
  [`system-thesis.md`](system-thesis.md) (the posture every rule serves). A topic doc read without
  them supports confident wrong conclusions — a "gap" you spot may be a priced residual, and a
  "simplification" may break an invariant carried three files away.
- **Reason adversarially, conclude fail-secure.** Every rule here exists for the adversarial case.
  "Under valid input," "no codepath does X," and "in the normal case" are reasoning smells
  ([`system-thesis.md` §Adversarial-first posture](system-thesis.md#adversarial-first-posture)).
  When a question has no confident answer, the design's answer is refuse.
- **Compose; never invent.** New work builds from landed mechanisms. The
  [`example-applications/`](example-applications/) docs are seventeen worked proofs of that
  discipline — each cites every mechanism it leans on and states its limits honestly. Match their
  shape: if your design needs machinery no doc provides, you have found either a wrong decomposition
  or a real gap to raise — not a license to invent.
- **Mind the vocabulary.** Terminology is linted (`make lint-terminology`); retired and forbidden
  terms fail the build. Say what the glossary says, in the greenfield voice the tree uses — no
  transition language, no "previously X."
- **Verify your edits.** `make all` (from the repo root) must exit 0 — cross-references and anchors
  are checked, so a broken link or renamed heading fails loudly. `git add` new files first; the
  linters only see tracked files. Mermaid rendering is _not_ checked — validate changed diagrams
  with `mmdc` yourself.

## Building an application against this design

The [`/create-application`](../../.claude/skills/create-application/SKILL.md) skill walks the whole
path — requirement gathering, pressure-testing, deriving the composition, and landing the app's
design in its own directory beside this repo. The [`example-applications/`](example-applications/)
set is the case book it draws on: one application per distinct feature/primitive composition, each
doc a template for what a finished app design looks like.
