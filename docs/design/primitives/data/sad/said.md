# SAID — Self-Addressing Identifier

A **Self-Addressing Identifier** (SAID) is the content-derived handle that names a [SAD](sad.md). It is the 44-character CESR-encoded Blake3-256 hash of the SAD's canonical serialization with the SAID field populated with a fixed value.

This doc states the SAID derivation algorithm, the fixed-value placeholder rule that makes self-embedding work, and the consequences for signing and verification. The SAD shape this algorithm hashes over is documented in [`sad.md`](sad.md).

## Derivation

The algorithm is the same across all primitives and all SAD shapes:

1. Take the SAD as a structured value (its logical content, including every field except the SAID being derived).
2. Populate the `said` field with the **fixed-value placeholder** — a 44-byte ASCII string of the same shape as a real SAID.
3. For a **prefix-deriving** SAD (an inception event, or any SAD whose `prefix` derives from its own content rather than being inherited), also populate the `prefix` field with the fixed-value placeholder.
4. Serialize the result with JSON Canonicalization Scheme (JCS, RFC 8785).
5. Compute Blake3-256 over the canonical bytes.
6. CESR-encode the 32-byte digest as a 44-character text token. The CESR encoding carries the algorithm code in its leading characters, so any consumer can re-derive without out-of-band agreement on the hash function.

The result is written back into the SAD's `said` field. For a prefix-deriving SAD, the same value is written into `prefix` (the inception event's prefix equals its SAID).

## The fixed-value placeholder rule

The placeholder mechanism — populating `said` (and `prefix`) with a fixed-value token of the SAID's exact byte shape rather than removing the field or substituting a different-sized value — is the structural property that lets a SAID be embedded inside its own SAD without circularity.

- **Same byte layout at derivation and verification.** The canonical bytes a producer hashes are exactly the canonical bytes a verifier reads, modulo the substitution of placeholder for real SAID at the `said` position. The field's byte length, the surrounding JCS punctuation, and the position of every other field stay identical. The hash function sees the same input shape both times.
- **No re-serialization on verification.** A verifier with the SAD in hand performs the substitution in place — replace the bytes at the `said` position with the placeholder, hash, compare. No reconstruction from a stripped or rewritten form is needed.
- **Deterministic across producers.** Two parties producing the same logical content arrive at the same canonical bytes, the same placeholder substitution, and the same SAID — without coordinating on which producer "owns" the SAID.

Per-primitive prefix derivation rules — what content the prefix commits to (whole-SAD-content for KEL; `(authPolicy, governancePolicy, nonce)` for IEL; `(identity, topic)` for SEL) — are documented in the corresponding event-log primitive docs. They differ in which fields are populated and which are left content-bearing, but they share this same fixed-value mechanism.

## Signing surface

Signatures throughout VDTI are produced over the SAID's CESR-encoded bytes, not over the SAD's serialized content. The SAID is the cryptographic commitment to the content; signing the SAID transitively commits the signer to the canonical bytes that produced it.

- **Stable signing surface under extension.** When a SAD's schema gains new fields under extension discipline (see [`../../../protocol-doctrine.md`](../../../protocol-doctrine.md#extension-discipline)), the SAID computation absorbs the new fields into the digest. The signing surface is still the SAID's 44 bytes, even though the underlying canonical-byte stream changed shape.
- **Unambiguous signature subject.** Signatures over serialized payloads are ambiguous about which canonicalization the verifier should reapply; signatures over a SAID are unambiguous — the SAID names exactly one content. A verifier checks the signature against the SAID, then independently re-derives the SAID from the content and checks equality.

## Adversarial framing

The SAID's adversarial properties follow from Blake3-256's collision resistance and from the determinism of the derivation algorithm.

- **Content authenticity from the SAID alone.** A verifier handed `(content, claimed_said)` recomputes `derived_said` from the content and accepts only when `derived_said == claimed_said`. Source provenance is not a verification input — the source can be a hostile peer, a tampered DB row, or a cached blob — because the bytes either re-derive to the claimed SAID or they do not.
- **Substitution is structurally infeasible.** Replacing a SAD with a different content payload while preserving the SAID would require a Blake3-256 collision. The protocol treats this as out of scope under standard cryptographic assumptions.
- **Producer ambiguity does not break verification.** Two honest parties producing the same content arrive at the same SAID; an adversary producing different content arrives at a different SAID. The protocol cares about which SAID is referenced (by `previous`, by `content`, by an anchor, by a policy SAID, by a custody field), not about who computed it.
- **Canonicalization is part of the security argument.** A non-deterministic serializer would let an adversary produce two byte sequences with the same logical content but different SAIDs. JCS removes that degree of freedom — the canonical bytes are a function of the logical content alone.

The SAID is the load-bearing handle every reference in the system uses to commit to a SAD: `previous` pointers, `ielEvent` bindings, KEL anchor SAIDs, policy SAIDs, content SAIDs on chain events, `ownerIelEvent` references (see [`custody.md`](custody.md)). When the doctrine talks about "a SAID anchored in a KEL `Ixn`" or "the `previous` SAID matches the parent," it is talking about this 44-byte identifier and the recomputable derivation that backs it.
