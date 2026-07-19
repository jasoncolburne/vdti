# vdti — area note: Authored DAG (the multi-writer content-graph primitive)

**Status: FIRST CUT — lifted 2026-07-19 (Jason) from the chat-lane / document-version DAG into one named
primitive.** Round-3 exchange review found the chat lane (cold **F4**) had **no stated monotonicity and no
fork rule** — the only `previous`-linked structure on the surface without a fork story — leaving a standing
self-lane backdate capability and an ordering ambiguity for honest readers. The fork/monotonicity discipline is
the same shape a document's multi-parent version DAG needs, so it is lifted to a primitive both the exchange
feature (chat lanes) and shared-documents (version graphs) compose. Design-doc twin:
[`../design/primitives/protocols/authored-dag.md`](../design/primitives/protocols/authored-dag.md).

**What it is in one line:** a **per-writer, append-only content DAG** — nodes are SADs, each authored and
signed by one member, attributed by **lane/branch** (not a sender field), **monotone** along any authored path,
with a **variant-specific fork rule** (single-parent: a fork is equivocation; multi-parent: branch + merge are
legitimate).

**Layering:** the SAD primitive (nodes are SADs; a document version node rides the custody direct-anchor) →
**authored-dag** (attribution + order + fork rule) → {exchange (chat lanes), shared-documents (version graphs)}
features → apps. Gated by [membership](vdti-area-membership.md) (who may append); bodies keyed by
[group-key](vdti-area-group-key.md).

**Invariants:** [inv 16] attribution by prefix (the writer at a path's root, inherited via the backward link),
[inv 19] signatures over the fully-compacted SAID (each node bound to its writer), [inv 17] keep-all-data (fork
siblings surface on propagation → a single-parent fork is data-local provable once both reach a reader), [inv 8] the writer's key-state is
current-as-of-authoring (the feature's sender-key-currency bound). A **multi-parent** node is additionally
witnessed via its **custody anchor** ([inv 14], [inv 16] the anchored write); a **single-parent** chat node is a
store-and-forward blob, **not** individually witnessed — fork detection is **propagation + signature**, not
receipts.

## The shared core (both variants)

- **Append-only backward links.** A node names its **predecessor(s)** — never successors — so the graph grows
  append-only and a writer commits only to existing nodes.
- **Attribution is the lane/branch, not a field.** No `sender` field: the writer is named **only where a path
  roots** (a chat lane's first message carries the writing device's KEL prefix; a document version's editor is
  its custody `owner`) and **inherited** along the backward link. A mid-graph node can never claim an author
  other than the path it descends from.
- **Authority is the signature under a current key-state.** Each node carries the writer's signature over its
  SAID (adjacent, the universal rule), verified against the writer's key-state **as of authoring** — the feature
  supplies the currency bound (a witnessed epoch window for chat; the anchoring position for a version), the DAG
  requires the property.
- **Monotonicity along an authored path.** The ordering key is **non-decreasing** from any node to any
  descendant — chat: `(epoch, timestamp)`; documents: version order. A tip-append carrying an earlier key is
  **malformed → rejected** (the backdate defense; the same footing as a broken signature).

## The variants — the fork rule is the only difference

- **Single-parent — a lane (chat).** Exactly one `previous` per node. A
  **second child of a node is a fork** — the writer signed two conflicting successors to one point in its own
  history = self-proving **equivocation**. Each node's **content-addressed SAID** commits its content and carries
  the writer's signature, so the two siblings are provably the same writer's conflicting successors —
  **undeniable** (a same-writer fork), no way to pass a fork off as one node. Whether it is **misbehavior** is the
  group's policy, not automatic: a crash-**resend** carries the *same* SAID (a dedup), but a crash before
  persisting the record, re-authored with a fresh nonce, is a genuine honest sibling. **Surfacing** it needs both siblings to reach a common honest reader: a witnessed node (a doc
  version) has the receipt beacon; an **unwitnessed** chat node rides propagation, so an eclipse / split delivery
  only **defers** detection (the standard detection-is-eventual residual), never hides the fork permanently. The
  consequence is the group's policy (for chat, coupled to membership removal + the epoch turn). **A writer's
  nodes forming a _single_ chain is a feature-enforced rule, not a single-parent property (PR#25 r2 W1/cold-P1):**
  single-parenthood alone yields a **forest** — a second parentless **root** is a disjoint lane the fork rule
  never fires on (two roots share no parent), and two roots are **not self-proving** the way a shared-parent fork
  is (nothing intrinsic marks which is the writer's real one). So the composing feature **anchors the lane root**
  — for chat, a writing **device's** lane root is a body-less join marker it mints, registered by a
  `chat-membership` grant-chain act, and a verifier honors only the lane rooted there; an unanchored root is
  **rejected** data-locally ([membership](vdti-area-membership.md)).
- **Multi-parent — a version graph (shared documents).** A node may name **several** `ancestors`; **branch and
  merge are legitimate** (concurrent editing diverges, a later version reconciles by naming both parents). Two
  successors carry **no** equivocation charge — divergence is the point, merge is the resolution. Monotonicity
  and per-branch attribution still hold.

## What this leaves standing

- **Backdating shrinks to a detectable act — for a writer whose tip has advanced (round-3 F4 + whole-design
  cold-P1).** When the writer's tip is **past** the target, monotonicity forces a backdate to **fork its own
  lane** — a self-signed equivocation any reader surfaces (evidence-bearing, not silent). A **frozen-tip** writer
  (removed from the group, still holding a retired key) has two moves the DAG won't surface, both the feature's to
  close: a **monotone forward-append** into the frozen range is cut by the removal **`bound`** (the lane tip at
  removal — a chat `chat-membership` rescission records it, the verifier cuts past), and a **fresh parentless
  root** is rejected by the **anchored root** (admission registers the writer's lane root; an unanchored one is not
  honored — above). The two brackets pin a removed writer's honored history to `[anchored root … bound]` (PR#25 r2
  W1/cold-P1). The DAG gives monotonicity; the feature gives the root anchor + the removal bound. A **current**
  writer merely gone dormant can still forward-append into an epoch it held but was silent for — no bound, valid
  key — the accepted backdate-within-a-held-window residual, own lane ([membership](vdti-area-membership.md)).
- **The lane-fork ambiguity is closed for honest readers, too.** Before F4 two messages sharing one `previous`
  had **no stated semantics**; single-parent says "that is equivocation," so an honest reader assembling the
  group view has a rule.

## The boundary — what the authored DAG is not

- **Not who may write** — [membership](vdti-area-membership.md) gates appending; the DAG assumes an authorized
  writer.
- **Not keying / confidentiality** — [group-key](vdti-area-group-key.md); the DAG carries an opaque, digest-named
  body.
- **Not delivery** — the transport / the recipient's own nodes; the DAG only requires siblings **reach** readers
  so a fork is detectable.
- **Not currency** — the feature's sender-key-currency mechanism supplies the current-key-state bound; the DAG
  requires the property, not the mechanism.

## Divergence / sources

A **vdti-native** consolidation, not lifted from kels. The two realizations pre-existed: the **chat per-sender
lane** (`vdti-area-exchange.md` §7a — the lane *is* the writer, no sender field; from Jason's 2026-07-14/15
group-message reasoning) and the **document version DAG** (`vdti-area-shared-documents.md` — multi-parent
`ancestors[]`, branch + merge). Round-3 F4 exposed that the chat lane lacked the monotonicity + fork rule the
version DAG's design implied but never stated for a *single-parent* structure; this note names the common
primitive and states the fork rule **per variant** (Jason 2026-07-19 — "define a single DAG concept with
variants"). Monotonicity was Jason's earlier suggestion, confirmed here as the F4 fix.

## Drift → land

- **DONE (2026-07-19).** Design-doc twin written (greenfield); this canon note.
- **DONE (2026-07-19, PR#25 r2 W1/cold-P1 fold).** The single-parent lane's **one-lane-per-writer** property is
  enforced by an **anchored root** (the admitting `chat-membership` grant registers the writer's lane root; an
  unanchored root is rejected), not derived from single-parenthood (which yields a forest — two roots are not
  self-proving). A removed writer's honored history is bracketed **`[anchored root … bound]`** (the anchor closes
  the fresh-root backdate; the existing removal `bound` closes the forward-append), with membership periods as
  disjoint anchored lanes (re-add anchors a new root). Landed across design + canon (authored-dag, membership,
  exchange, shapes, `vdti-area-exchange.md` §7a, inv 21, residuals).
- **Owed (this PR — the exchange encode).** State the **single-parent** chat lane in `vdti-area-exchange.md` §7a
  + `exchange.md`: the `(epoch, timestamp)` monotonicity rule + the fork-is-equivocation rule (coupled to
  `chat-membership` removal + the epoch turn), replacing round-3 F4's understated residual. The chat message SAD
  (`shapes.md`) already carries `previous` / `writer` / `epoch` / `timestamp` — no shape change, only the stated
  rules.
- **⚠ Owed (the shared-documents PR — DO NOT DROP; deferred 2026-07-19 with the membership rename).** Wire the
  **multi-parent** version graph onto this primitive (the version SAD's `ancestors[]` is already the multi-parent
  DAG — `shapes.md`); state branch + merge + version-order monotonicity as this primitive's multi-parent variant
  at the shared-documents encode.
