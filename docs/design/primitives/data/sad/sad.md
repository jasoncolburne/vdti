# SAD — Self-Addressed Data

A **Self-Addressed Data** record (SAD) is a serializable object whose own identifier — its
[SAID](said.md) — is derived from its content. Every content-bearing primitive in VDTI is a SAD:
chain events (KEL / IEL / SEL), credentials, policy declarations, exchange envelopes, replica sets,
and the content payloads SEL events anchor.

This doc states the SAD shape and the structural patterns that follow from it. The derivation
algorithm itself lives in [`said.md`](said.md); compaction and disclosure in
[`compaction.md`](compaction.md); per-object authority in [`custody.md`](custody.md).

**Reading order for the SAD primitive group**: this doc → [`said.md`](said.md) →
[`custody.md`](custody.md) → [`availability.md`](availability.md) →
[`compaction.md`](compaction.md).

## Structural shapes

Every SAD carries a `said` field. From there, one specialization matters at this layer:

- **Chain events** are SADs with chain-linkage fields — `prefix` (chain identifier) + `previous`
  (parent SAID) + `serial` (monotonic position) + kind-specific fields, including SAD references
  that point to what an event commits to (a KEL or IEL event's role-grouped `manifest`, a lookup SEL
  inception's `data`). Chain events live on a KEL, IEL, or SEL chain and replicate as indivisible
  units. Their kind-specific schemas have no slots for custody or availability fields, so those
  fields cannot appear on a chain event.
- **Standalone (non-chain-event) SADs** are the rest — credentials, policy SADs, exchange envelopes,
  replica sets, and the content payloads chain events anchor. Stored in the SAD object store and
  retrieved by SAID. MAY carry per-object authority via a top-level [`custody`](custody.md) field
  and per-object replication scope via an independent [`availability`](availability.md) field on the
  same wrapper.

A chain event is a SAD with additional structural commitments — chain identity, monotonic position,
continuity via `previous`. A standalone SAD is independently addressable and carries its content
directly. The doctrine that follows uses "SAD" as the general term and specializes to "chain event"
or "standalone SAD" where the distinction matters.

**Events are never fetchable by SAID from the SAD object store.** Chain events live in the chain
log, addressed **by prefix** ([`said.md`](said.md): a SAID is an integrity commitment, not a global
lookup key). Only standalone SADs are stored in — and served by SAID from — the SAD object store, so
its write path **classifies a submission by `kind` and rejects event kinds** (`kind` is required on
SAD data). The principle: **nothing whose SAID must stay opaque is fetchable by SAID from the
store.** This closes a correlation vector — event SAIDs float free of their prefix by design
(`said ≠ prefix`, and an IEL's `anchors[]` are opaque commitments), so an attacker who harvests the
`anchors[]` SAIDs off a **public** issuer IEL (each committing to a revocation / rescission
lookup-SEL event) could, if the store answered a fetch-by-SAID for an **event** body, recover the
lookup-SEL and re-derive its prefix, using the store as an inversion oracle for the issuer's
revocations. Rejecting event kinds makes that physically impossible; a **public** credential's body
(a content kind) stays fetchable by SAID (intended), while a **private** credential's body is simply
unpublished. Storage-side enforcement lands in
[`../../../infrastructure/vdtid.md`](../../../infrastructure/vdtid.md) (forward-ref; lands in a
subsequent sub-issue).

## Required fields

Every SAD carries:

- `said` — the SAD's self-addressing identifier. Computed per [`said.md`](said.md): the SAD is
  canonicalized with `said` populated to a fixed-value placeholder, Blake3-256 is computed over the
  canonical bytes, and the digest is base64 encoded and qualified.
- For **chain inception events** (the prefix-deriving SADs): a `prefix` field in addition to `said`.
  The inception event derives the two values via two separate hashes, in order — first `prefix`
  (with both `said` and `prefix` set to the fixed-value placeholder), then `said` (with `prefix`
  populated with its just-derived real value, and only `said` set to the placeholder). On the
  inception event, `prefix` and `said` are different values. Subsequent events on the chain inherit
  `prefix` from the inception event and derive only `said`; the inherited prefix is part of the
  canonical bytes the `said` hash sees. See [`said.md` §Derivation](said.md#derivation) for the
  algorithms.

What content the prefix commits to is per-primitive — the KEL prefix commits to the whole inception
SAD (the device's key state); the IEL prefix likewise commits to its whole inception SAD (the
`roster` of member devices, the threshold vector, and the `nonce` whose randomness makes the IEL
prefix unpredictable); the SEL prefix likewise commits to its whole inception SAD (the populated
`owner` / `topic` / `data` fields). The shared rule is the fixed-value mechanism; the per-primitive
shapes are documented in the corresponding event-log primitive docs.

## Canonical serialization

Canonicalization uses JSON Canonicalization Scheme (JCS, RFC 8785): deterministic key ordering, no
insignificant whitespace, a stable number representation. Two parties starting from the same logical
content produce the same canonical bytes — and therefore the same SAID — independently.

The fixed-value placeholder for `said` (and `prefix`, when prefix-deriving) is the same shape and
byte-length as a real SAID. The canonical serialization's byte layout during SAID computation
matches the byte layout a verifier sees when reading the SAD with its real SAID in place. This is
what lets a SAID be embedded inside its own SAD without circularity: every consumer re-applies the
fixed-value rule, re-hashes the same bytes, and arrives at the same digest. For chain inception
events the same property holds for the prefix derivation as for the SAID derivation — two parties
starting from the same logical content arrive at the same prefix and the same SAID via two
independent hashes (see [`said.md` §Derivation](said.md#derivation)).

## Composition by reference

A SAD that depends on another SAD commits to that child by SAID. The canonical form for SAID
computation always uses SAIDs at sub-SAD positions, never inline content (see
[`said.md` §Canonical form for SAID computation](said.md#canonical-form-for-said-computation)).
Over-the-wire representations MAY embed children inline for atomicity or transport efficiency (see
[`compaction.md`](compaction.md)); the canonical bytes the parent's SAID hashes over are the same
regardless of wire form.

The reference graph composes: a parent SAD's SAID commits to the SAIDs of its referenced children,
which commit to their own children, and so on. An adversary cannot substitute any node in the graph
without changing every SAID at-and-above that node.

## Adversarial framing

A SAD's identity IS its content hash (SAID). Verification reduces to recomputation; trust in the
source is not required.

- A verifier given a SAD and its claimed SAID checks `computed_said == declared_said` from the bytes
  alone. The source can be a hostile peer, a tampered database, or a cached blob of unknown
  provenance; the bytes either hash to the claimed identifier or they do not. This is what
  [`../../../system-thesis.md`](../../../system-thesis.md) names **end-verifiability over
  data-from-any-source**.
- Tamper-evidence is transitive via the reference graph above. Composition by SAID means a parent's
  SAID transitively commits to every reachable child; modification anywhere in the subgraph
  propagates upward as a SAID change at every ancestor.
- Canonical serialization is part of the security argument, not a convenience. A non-deterministic
  serializer would let an adversary produce two different byte sequences from the same logical
  content with two different SAIDs, breaking the "one content, one identifier" property the rest of
  the protocol depends on.

The SAID is the load-bearing handle for every reference in the system — `previous` pointers, `pin`
references, policy SAIDs, anchor SAIDs, `manifest` SAIDs, custody references. The per-primitive
event-log docs and [`../../../protocol-doctrine.md`](../../../protocol-doctrine.md) elaborate the
structural rules that compose on top.
