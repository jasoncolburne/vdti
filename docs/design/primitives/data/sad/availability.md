# SAD Availability

**Availability** is the per-SAD declaration of where the bytes live, how long they live, and whether
retrieval is destructive. It is a top-level `availability` field on the standalone-SAD wrapper,
sibling to the [`custody`](custody.md) field, and is one of the per-object policy axes the wrapper
carries.

This doc states the structural role of `availability` and its three sub-axes. Per-axis policy
expression — concrete encoding for replica references, TTL representation, one-shot semantics — and
storage-side enforcement live in
[`../../../infrastructure/vdtid.md`](../../../infrastructure/vdtid.md) (forward-ref; forthcoming).

## What availability declares

`availability` is a sibling top-level inline struct on the SAD wrapper:

```
availability { replicas, ttl, once }
```

Each sub-field is independently optional and covers one operational axis:

- **`replicas`** — replication scope. Names which storage replicas hold the bytes. Absent →
  broadcast to all replicas (default; the SAD is replicated everywhere). Present → carries the SAID
  of a replica-set SAD listing eligible replicas; only those replicas participate in replication for
  this SAD. The replica set is a separately-stored SAD per the canonical-form rule (see
  [`said.md` §Canonical form for SAID computation](said.md#canonical-form-for-said-computation)).
- **`ttl`** — time-to-live. How long the bytes are retained at the storage boundary. Expired SADs
  are garbage-collected; fetches against an expired SAID return the same "not present" response a
  never-existed SAID would.
- **`once`** — one-shot delivery. Whether retrieval is destructive. A `once` SAD is removed from
  storage after the first successful read; subsequent fetches by the same or any other consumer
  fail.

The three sub-fields compose freely — a SAD MAY declare any combination (e.g., replica-scoped
replication + bounded TTL + non-destructive read; or default replication + no TTL + one-shot
delivery).

## Scope

Availability applies to **standalone SADs only.** Chain events (KEL, IEL, SEL) have a fixed
kind-specific schema with no slot for `availability`; they replicate as indivisible units governed
by their per-primitive event-log doctrine. Per-event availability is structurally impossible because
the chain-event kind-schemas forbid the slot.

## Decoupling from custody

Availability and [custody](custody.md) are orthogonal axes on the SAD wrapper:

- **Custody** is an authority decision — who may write, who may read.
- **Availability** is an operational decision — where the bytes live, how long, whether retrieval is
  destructive.

Either axis composes independently with the other. The four-corners composition (custody-gated ×
replicated) is enumerated in
[`custody.md` §Decoupling from availability](custody.md#decoupling-from-availability).

## SAID commitment

`availability` is a top-level field on the SAD wrapper and participates in canonical serialization,
so the availability declaration is committed by the SAD's SAID. An adversary cannot substitute a
different `availability` value (extending a TTL, converting one-shot to non-destructive, broadening
a replica scope) without changing the SAD's SAID — and the new SAID would not match any reference
that names the original.

## Adversarial framing

The structural guarantees follow from the SAID commitment and from where enforcement lives.

- **Availability declarations are tamper-evident.** The SAID commitment makes substitution at the
  wrapper boundary surface as a SAID mismatch at the next verifier walk. An adversary cannot quietly
  upgrade a SAD's replication scope or extend its TTL.
- **Enforcement is at the storage boundary.** TTL, replica scope, and one-shot semantics are applied
  by the storage service (`vdtid`). A consumer fetching an expired or already-consumed one-shot SAD
  receives a uniform "not present" response; the absence does not distinguish "expired" from
  "one-shot consumed" from "never existed."
- **One-shot is operational, not cryptographic.** A consumer who has retrieved a one-shot SAD can
  persist the bytes locally; the protocol cannot prevent that. `once` is an instruction to the
  storage service about deletion semantics, not a guarantee about post-retrieval consumer behavior.
  Cryptographic deletion is not a property the protocol offers.
- **Replica-scope enforcement is fail-secure.** When `replicas` references a replica set that cannot
  be resolved (fetch failure, parse error), replication MUST default to skip rather than to
  broadcast. A resolution failure cannot quietly broaden the replication scope past what the SAD's
  author declared.
- **Forbidden on chain events is enforced structurally.** Chain-event kind-schemas have no slot for
  `availability`, so a chain-event submission carrying inline `availability` is rejected by the
  structural-validation pass at the merge layer (see
  [`../../../protocol-doctrine.md` §Merge verification](../../../protocol-doctrine.md#merge-verification-and-advisory-locking)).
