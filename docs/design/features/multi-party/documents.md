# Multi-party documents

_Forthcoming._ The full multi-party-documents feature lands here — a document several parties
co-author, whose membership and sharing evolve under a creator, fully end-verifiable. It composes
the SAD + SEL primitives with the document layer
([`../../primitives/policy/documents.md`](../../primitives/policy/documents.md)); credentials are
the contrast (issuer/issuee, fixed membership). This stub carries the structure diagram ahead of the
prose.

## The construct

A multi-party document is a DAG of **attributed version SADs** under a **creator-governed,
per-period access list**. **V0** (the constitution) derives the doc prefix. The creator governs
membership on a **governance SEL**: a `Gnt` (tier 2, `Ath`-anchored, `t_authorize`) names a gated
**grant-doc `G`** listing `editors` / `commenters` and their `from` validity-period starts; a
per-period **rescission** (`{Icp, Trm}`, keyed `hash(G | said_b)` — `said_b` the nonce'd grant-entry
SAID) closes a period. Its `bound` rides **gated content**, not a public `manifest.bound` (a bound
SAID is participant-identifying by matching). Each **version** is a custody-attributed SAD on its
**own version SEL** (`{Icp, Pin}`, `derive(owner, DOC_TOPIC, version_said)`): the `Icp`'s `data`
names the version SAD, and its serial-1 `Pin` (v1) is anchored by the author's IEL `Ixn` at position
`V_x`. Versions chain via `ancestors[]` into a multi-parent DAG rooted at V0. A version by X at
`V_x` is **honored iff** its grant names a period `[F_x, B_x]` with `F_x ≤ V_x ≤ B_x` — an
intra-chain, append-only, clock-free membership test.

```mermaid
flowchart BT
  vM["vM — merge"]:::doc
  V0["V0 — constitution SAD"]:::doc
  vA1["vA1"]:::doc
  vB1["vB1"]:::doc
  vA["version SEL A: Icp"]:::sel
  vB["version SEL B: Icp"]:::sel
  gGnt["governance SEL: Gnt"]:::sel
  G["grant-doc G (gated)"]:::doc
  Resc["rescission SEL: {Icp, Trm}"]:::sel
  gGnt -.->|manifest.grant| G
  gGnt -. rescind .-> Resc
  vA -.->|data| vA1
  vB -.->|data| vB1
  V0 -->|ancestor of| vA1
  V0 -->|ancestor of| vB1
  vA1 -->|ancestor of| vM
  vB1 -->|ancestor of| vM
  classDef sel fill:#122a44,stroke:#1971c2,color:#fff
  classDef doc fill:#3d2f12,stroke:#f08c00,color:#fff
```

Nodes are colour-coded (SEL blue, referenced SADs / grant-doc orange). Dotted arrows are manifest
references (`grant`, `data`) and the governance→rescission relation; solid arrows are the
`ancestors[]` version DAG, drawn **ancestor → descendant** (see the note). Each version SEL is
`{Icp, Pin}` — its `Icp`'s `data` names the version SAD, the serial-1 `Pin` floors it to the
author's IEL tip.

> **Note — the lineage arrows run against the usual convention.** Everywhere else in these docs an
> arrow points **along the reference**: the field that holds a SAID points at what it commits. The
> `ancestors[]` link is the same shape — it lives on a version and points **back** to its ancestor
> (`vA1 → V0`, `vM → vA1`). This diagram draws those arrows **reversed** (`ancestor of`, ancestor →
> descendant) for one reason: mermaid derives a flowchart's layout **from** its arrow directions, so
> the linkage-faithful arrows would either stand the version DAG on its head (V0 at the top) or lift
> each version SEL above the document it anchors. The build-up layout (constitution at the base,
> merge on top; each doc above its SEL) and the linkage-faithful arrow direction cannot both be
> expressed in mermaid — that would need a renderer decoupling arrows from layout (e.g. Graphviz
> `constraint=false`), which would clash with every other diagram here. So the solid arrows in this
> one diagram read as **lineage**, not as `ancestors[]` pointers.
