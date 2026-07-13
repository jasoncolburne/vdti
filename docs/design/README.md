# VDTI Design Documentation

This directory is the **design surface** for VDTI — the canonical specification of the protocol. It
is built from foundations up: each layer builds on the ones below it. Read it in order for a first
full pass, or jump to a layer with the table of contents.

Two ideas anchor everything here. Every content-bearing object is a **SAD** — Self-Addressed Data, a
record identified by the hash of its own content. And the system's central claim is
**end-verifiability**: any consumer can validate any chain, credential, or event from the data
alone, trusting no service, database, or peer. The reading order follows from that — the data
substrate first, then the doctrine that governs it, then the primitives that implement it, then the
authorization layer that sits on top.

## Table of contents

- [0 — Orientation](#0--orientation)
- [1 — The data substrate](#1--the-data-substrate)
- [2 — Cross-cutting doctrine](#2--cross-cutting-doctrine)
- [3 — The event-log primitives](#3--the-event-log-primitives)
- [4 — The document-authorization layer](#4--the-document-authorization-layer)
- [Forthcoming](#forthcoming)

## 0 — Orientation

Start here.

1. [`system-thesis.md`](system-thesis.md) — the founding thesis: end-verifiability over data from
   any source, the adversarial-first posture, and the load-bearing doctrines (compromise is
   permanent, divergence resolves by tier, forks are seal-bounded, the verifier is the trust
   boundary). The "why" behind every rule that follows.

Keep [`glossary.md`](glossary.md) open alongside — it gives a one-line definition of every
load-bearing term (seal, tier, sealed branch, effective-SAID, …) with a pointer to the doc that owns
it.

## 1 — The data substrate

Everything content-bearing is a SAD; this layer defines what that means. (This group also carries
its own reading-order note in `sad.md`.)

2. [`primitives/data/sad/sad.md`](primitives/data/sad/sad.md) — the SAD record: chain events versus
   standalone SADs, composition by reference.
3. [`primitives/data/sad/said.md`](primitives/data/sad/said.md) — the SAID derivation and
   canonicalization — the mechanism that makes end-verifiability work.
4. [`primitives/data/sad/custody.md`](primitives/data/sad/custody.md) — per-object authority: who
   may write, who may read.
5. [`primitives/data/sad/availability.md`](primitives/data/sad/availability.md) — where the bytes
   live: replicas, time-to-live, one-shot delivery.
6. [`primitives/data/sad/compaction.md`](primitives/data/sad/compaction.md) — compaction and
   selective disclosure.

## 2 — Cross-cutting doctrine

7. [`protocol-doctrine.md`](protocol-doctrine.md) — the rules that span every primitive: the two
   capability tiers, the seal and locked-portion bound, divergence and recovery, federation
   convergence, the verification walk, and the shared terminology. Dense; read it here for the
   concept map, and revisit its divergence and federation sections after the event-log group — they
   land deeper once the event shapes are concrete.

Alongside the doctrine, [`residuals.md`](residuals.md) is the honest-limits catalog — every risk the
design does not fully eliminate, grouped and ranked by cost of exposure, each with the concrete
attack, the mitigation, and what is lost. It is where a deployment learns what each trade costs and
what the whole system leans on. [`monitoring.md`](monitoring.md) covers the owner-side detection
layer for the silent compromises — comparing a prefix's effective SAID against what its key state
expects.

## 3 — The event-log primitives

The KEL / IEL / SEL chains — the heart of the protocol.

8. [`primitives/data/event-logs/event-shape.md`](primitives/data/event-logs/event-shape.md) — the
   event taxonomy, field shape, and per-kind structural rules shared across all three log types. The
   bridge from SADs to chains.

Then the KEL (Key Event Log) primitive, in order:

9. [`primitives/data/event-logs/kel/log.md`](primitives/data/event-logs/kel/log.md) — the chain
   primitive: the four-state per-node machine, the seal / spine / locked-portion, paging.
10. [`primitives/data/event-logs/kel/events.md`](primitives/data/event-logs/kel/events.md) — the
    kind taxonomy, the two-tier capability model, the kind-strict anchor matrix, and forward-key
    commitments.
11. [`primitives/data/event-logs/kel/verification.md`](primitives/data/event-logs/kel/verification.md)
    — the verifier walk and the verification token: how a chain is read and validated.
12. [`primitives/data/event-logs/kel/merge.md`](primitives/data/event-logs/kel/merge.md) — the write
    path: divergence resolution, burial by position and descent, and the single-word merge outcomes.
13. [`primitives/data/event-logs/kel/compromise.md`](primitives/data/event-logs/kel/compromise.md) —
    recovery as a plain burying `Rot`: the reserve defends the signing key, not the rotation key.
14. [`primitives/data/event-logs/kel/reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md)
    — the exhaustive correctness proof: every divergence case resolved, and the argument that all
    honest nodes converge. The densest doc; read it last.

Then the IEL (Identity Event Log) primitive, in order:

15. [`primitives/data/event-logs/iel/log.md`](primitives/data/event-logs/iel/log.md) — the chain
    primitive: an identity as a threshold over member KELs; the four-state machine; the seal,
    locked-portion bound, and seal-cap over the content window versus the sealed spine.
16. [`primitives/data/event-logs/iel/events.md`](primitives/data/event-logs/iel/events.md) — the
    eight-kind taxonomy (plus the restricted federation set), the threshold vector and its bounds,
    the kind-strict anchor matrix, the `kills[]` revocation declaration, and the facet-dependent
    `Wit`.
17. [`primitives/data/event-logs/iel/verification.md`](primitives/data/event-logs/iel/verification.md)
    — the verifier walk: threshold anchoring, roster accumulation by delta, root-facet dispatch, and
    the `kills[]` forward-match.
18. [`primitives/data/event-logs/iel/merge.md`](primitives/data/event-logs/iel/merge.md) — the write
    path: events first-seen at their own position (the universal position gate — content _and_
    sealed), sealed record-both, and eviction via a roster `cut`.
19. [`primitives/data/event-logs/iel/reconciliation.md`](primitives/data/event-logs/iel/reconciliation.md)
    — the correctness-proof matrix: the content-versus-sealed divergence enumeration and the verdict
    by witnessed-sealed-branch count (at the last seal).
20. [`primitives/data/event-logs/iel/delegation.md`](primitives/data/event-logs/iel/delegation.md) —
    the delegate / rescind surface: the single-hop grant-and-rescission primitive.

## 4 — The document-authorization layer

Policy sits above the primitives — it governs documents, never the chain events themselves
(chain-event authorization is structural). (This group carries its own reading-order note in
`policy.md`.)

21. [`primitives/policy/policy.md`](primitives/policy/policy.md) — the policy language (`id` / `del`
    / `pol` leaves; `thr` / `wgt` / `and` combinators).
22. [`primitives/policy/documents.md`](primitives/policy/documents.md) — where policy lives:
    documents as policy hosts, and how a document anchors its evaluation context.
23. [`primitives/policy/evaluation.md`](primitives/policy/evaluation.md) — the two ways a policy is
    evaluated (as-issued and current) and the seam to the primitives.

## Forthcoming

These are referenced above as forward-references and are still forthcoming:

- `primitives/data/event-logs/sel/` — the SEL primitive: single-owner content and credential logs,
  anchored by their owner IEL.
- `federation/` — federation bootstrap and witnessing;
  [`federation/bootstrap.md`](federation/bootstrap.md) is a diagram stub carrying its diagrams ahead
  of the prose.
- `features/` — credentials and shared documents;
  [`features/shared-documents/documents.md`](features/shared-documents/documents.md) is a diagram
  stub carrying its diagrams ahead of the prose.
- `operations/` — operator workflows (recovery ceremony, sealing serialization).
- `infrastructure/` — the storage service.
