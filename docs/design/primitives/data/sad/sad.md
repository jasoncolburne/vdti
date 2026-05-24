# SAD — Self-Addressed Data

A **Self-Addressed Data** record (SAD) is a serializable object whose own identifier — its [SAID](said.md) — is derived from its content. Every content-bearing primitive in VDTI is a SAD: chain events (KEL / IEL / SEL), credentials, policy declarations, exchange envelopes, NodeSets, and the content payloads SEL events anchor.

This doc states the SAD shape and the structural patterns that follow from it. The derivation algorithm itself lives in [`said.md`](said.md); compaction and disclosure in [`compaction.md`](compaction.md); per-object authority in [`custody.md`](custody.md).

**Reading order for the SAD primitive group**: this doc → [`said.md`](said.md) → [`custody.md`](custody.md) → [`compaction.md`](compaction.md).

## Structural shapes

Every SAD carries a `said` field. From there, one specialization matters at this layer:

- **Chain events** are SADs with chain-linkage fields — `prefix` (chain identifier) + `previous` (parent SAID) + `serial` (monotonic position) + kind-specific fields, including a `content` SAID that points to the SAD where the event's payload lives. Chain events live on a KEL, IEL, or SEL chain and replicate as indivisible units. Their kind-specific schemas have no slots for custody or availability fields, so those fields cannot appear on a chain event.
- **Standalone (non-chain-event) SADs** are the rest — credentials, policy SADs, exchange envelopes, NodeSets, and the content payloads chain events anchor. Stored in the SAD object store and retrieved by SAID. MAY carry per-object authority via the custody fields ([`custody.md`](custody.md)) and per-object replication scope via an independent availability field on the same wrapper.

A chain event is a SAD with additional structural commitments — chain identity, monotonic position, continuity via `previous`. A standalone SAD is independently addressable and carries its content directly. The doctrine that follows uses "SAD" as the general term and specializes to "chain event" or "standalone SAD" where the distinction matters.

## Required fields

Every SAD carries:

- `said` — the SAD's self-addressing identifier. Computed per [`said.md`](said.md): the SAD is canonicalized with `said` populated to a fixed-value placeholder, Blake3-256 is computed over the canonical bytes, and the digest is CESR-encoded.
- For **chain inception events** (the prefix-deriving SADs): a `prefix` field. The prefix is computed by populating BOTH `said` and `prefix` with fixed-value placeholders, canonicalizing, and hashing. The result is shared as both `prefix` and `said` on the inception event. Subsequent events on the chain inherit `prefix` from inception and derive only `said`.

What content the prefix commits to is per-primitive — KEL prefix commits to the whole inception SAD; IEL prefix commits to `(authPolicy, governancePolicy, nonce)`; SEL prefix commits to `(identity, topic)`. The shared rule is the fixed-value mechanism; the per-primitive shapes are documented in the corresponding event-log primitive docs.

## Canonical serialization

Canonicalization uses JSON Canonicalization Scheme (JCS, RFC 8785): deterministic key ordering, no insignificant whitespace, a stable number representation. Two parties starting from the same logical content produce the same canonical bytes — and therefore the same SAID — independently.

The fixed-value placeholder for `said` (and `prefix`, when prefix-deriving) is the same shape and byte-length as a real SAID. The canonical serialization's byte layout during SAID computation matches the byte layout a verifier sees when reading the SAD with its real SAID in place. This is what lets a SAID be embedded inside its own SAD without circularity: every consumer re-applies the fixed-value rule, re-hashes the same bytes, and arrives at the same digest.

## Composition by reference

A SAD that depends on another SAD commits to that child by SAID. The canonical form for SAID computation always uses SAIDs at sub-SAD positions, never inline content (see [`said.md` §Canonical form for SAID computation](said.md#canonical-form-for-said-computation)). Over-the-wire representations MAY embed children inline for atomicity or transport efficiency (see [`compaction.md`](compaction.md)); the canonical bytes the parent's SAID hashes over are the same regardless of wire form.

Two composition patterns at the wire layer:

- **Hard references** — a SAID-typed field on the parent names the SAID of a child SAD. The parent commits to the child's SAID exactly; substituting a different child would require a Blake3-256 collision against the named SAID.
- **Compaction** — a SAD containing nested SADs MAY be transmitted with children embedded inline (expanded form) or with children replaced by their SAIDs (compacted form). The parent's SAID is identical in either form. See [`compaction.md`](compaction.md).

The reference graph composes: a parent SAD's SAID commits to the SAIDs of its referenced children, which commit to their own children, and so on. An adversary cannot substitute any node in the graph without changing every SAID at-and-above that node.

## Adversarial framing

A SAD's identity IS its content hash. Verification reduces to recomputation; trust in the source is not required.

- A verifier given a SAD and its claimed SAID checks `computed_said == declared_said` from the bytes alone. The source can be a hostile peer, a tampered database, or a cached blob of unknown provenance; the bytes either hash to the claimed identifier or they do not. This is what [`../../../system-thesis.md`](../../../system-thesis.md) names **end-verifiability over data-from-any-source**.
- Tamper-evidence is transitive via the reference graph above. Composition by SAID means a parent's SAID transitively commits to every reachable child; modification anywhere in the subgraph propagates upward as a SAID change at every ancestor.
- Canonical serialization is part of the security argument, not a convenience. A non-deterministic serializer would let an adversary produce two different byte sequences from the same logical content with two different SAIDs, breaking the "one content, one identifier" property the rest of the protocol depends on.

The SAID is the load-bearing handle for every reference in the system — `previous` pointers, `ielEvent` bindings, policy SAIDs, anchor SAIDs, content SAIDs, custody references. The per-primitive event-log docs and [`../../../protocol-doctrine.md`](../../../protocol-doctrine.md) elaborate the structural rules that compose on top.
