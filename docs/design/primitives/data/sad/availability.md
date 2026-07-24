# SAD Availability

**Availability** is the per-SAD declaration of **how long the bytes live and whether retrieval is
destructive**. It is a top-level `availability` field on the standalone-SAD wrapper, sibling to the
[`custody`](custody.md) field, and is one of the per-object axes the wrapper carries.

This doc states the structural role of `availability` and its two sub-axes. Per-axis policy
expression — concrete encoding for one-shot semantics — and storage-side enforcement live in
[`../../../substrate/infrastructure/vdtid.md`](../../../substrate/infrastructure/vdtid.md).

## What availability declares

`availability` is a sibling top-level inline struct on the SAD wrapper:

```
availability { expiry, once }
```

Each sub-field is independently optional and covers one operational axis:

- **`expiry`** — the **absolute instant** past which the bytes need not be retained at the storage
  boundary. It is committed inside the SAID'd bytes — never a duration counted from a local write,
  which each holder would measure from its own clock, letting an expired object re-arrive from a
  peer and start a fresh life at every hop. An absolute horizon reads the same from the object alone
  wherever it lands, so an expired copy is refusable on sight. Expired SADs are garbage-collected;
  fetches against an expired SAID return the same "not present" response a never-existed SAID would.
- **`once`** — one-shot delivery. Whether retrieval is destructive. A `once` SAD is removed from
  storage after the first successful read; subsequent fetches by the same or any other consumer
  fail. So `once` composes poorly with a **blob shared across a fan-out**: if one ciphertext blob is
  meant for a recipient's several devices (or a group's members), the first reader consumes it and
  the rest fail. `once` fits a blob with a **single** consumer — per-device ESSR gives each device
  its own ciphertext, where `once` is exactly right — not a shared one.

The two sub-fields compose freely — a SAD MAY declare any combination (e.g., an expiry with
non-destructive read, or no expiry with one-shot delivery).

**Where** the bytes live is not an availability axis. A SAD carries no placement field: the client's
**cascading store**
([`../../../substrate/infrastructure/architecture.md` §The store traits](../../../substrate/infrastructure/architecture.md#the-store-traits--one-interface-composed-in-sequence))
routes a write — **federation-published** (submitted to a federation node, which replicates it
across **all** the federation's witnesses) or **off-federation** (kept on a local or private
[`sadstore`](../../../example-applications/sadstore.md) tier and not submitted) — by application and
deployment policy, never by anything in the bytes. A federation replicates every SAD it admits
across all its witnesses, so there is no per-object replication scope to declare.

When a SAD names bulk bytes as a **content-addressed blob** rather than inlining them
([`sad.md` §Bulk opaque bytes](sad.md#bulk-opaque-bytes--the-content-addressed-blob)), the blob is
the bytes this `availability` governs: the `expiry` and `once` semantics apply to the referenced
blob, not only the SAD wrapper. Where the blob lives follows the same client placement decision as
any SAD — a `file` kept **off the federation** lives on a
[`sadstore`](../../../example-applications/sadstore.md) tier of the cascading store (a recipient's
inbox, a private drive), placed by the application, not on the federation's witnesses.

## Scope

Availability applies to **standalone SADs only.** Chain events (KEL, IEL, SEL) have a fixed
kind-specific schema with no slot for `availability`; they replicate as indivisible units governed
by their per-primitive event-log doctrine. Per-event availability is structurally impossible because
the chain-event kind-schemas forbid the slot.

## Decoupling from custody

Availability and [custody](custody.md) are orthogonal axes on the SAD wrapper:

- **Custody** is an authority decision — who may write, who may read.
- **Availability** is an operational decision — how long the bytes live and whether retrieval is
  destructive.

Either axis composes independently with the other. The combinations of custody with where the bytes
live are enumerated in
[`custody.md` §Decoupling from availability](custody.md#decoupling-from-availability).

## A root covers its children

A standalone SAD may serve as a **root** for others — an accepted event or parent SAD whose
commitment lets the store admit a child ([`rooting.md`](rooting.md)). A rooted child stays
re-confirmable only while its root is still reachable, so a root's availability must **cover** every
SAD it roots:

- **`expiry`** — `child.expiry ≤ root.expiry`; a root with no expiry covers any child.
- **`once`** — a root may **not** be `once`: deleted after one read it could cover nothing, and no
  consumer can be guaranteed to grab a root and its child atomically. Data whose sub-parts must
  vanish together is a single `once` object with **inline** sub-parts, not separate `once` SADs.

A leaf that roots nothing is unconstrained **as a root**, but every SAD is still bound by this check
**as a child of its own root**, whatever it roots. A chain-event root is federation-wide and
permanent, so only a parent-SAD root carries this check. It is enforced at admission from the two
SADs' own `availability` fields — a child whose availability exceeds its root's is refused,
fail-secure.

## SAID commitment

`availability` is a top-level field on the SAD wrapper and participates in canonical serialization,
so the availability declaration is committed by the SAD's SAID. An adversary cannot substitute a
different `availability` value (extending an expiry, converting one-shot to non-destructive) without
changing the SAD's SAID — and the new SAID would not match any reference that names the original.

## Adversarial framing

The structural guarantees follow from the SAID commitment and from where enforcement lives.

- **Availability declarations are tamper-evident.** The SAID commitment makes substitution at the
  wrapper boundary surface as a SAID mismatch at the next verifier walk. An adversary cannot quietly
  convert a one-shot SAD to non-destructive or extend its expiry.
- **Enforcement is at the storage boundary.** Expiry and one-shot semantics are applied by the
  storage service (`vdtid`). A consumer fetching an expired or already-consumed one-shot SAD
  receives a uniform "not present" response; the absence does not distinguish "expired" from
  "one-shot consumed" from "never existed."
- **One-shot is operational, not cryptographic.** A consumer who has retrieved a one-shot SAD can
  persist the bytes locally; the protocol cannot prevent that. `once` is an instruction to the
  storage service about deletion semantics, not a guarantee about post-retrieval consumer behavior.
  Cryptographic deletion is not a property the protocol offers.
- **Expiry is a retention promise, not a verifiable property.** Like one-shot, retention is the
  storage service's promise, not something a consumer can verify: an adversarial replica can keep
  expired bytes indefinitely, and an honest one may lose them early. The `expiry` bounds when the
  store **may** delete, not when the bytes actually vanish.
- **Forbidden on chain events is enforced structurally.** A chain-event kind declares no
  `availability` field, so the exhaustive-schema rule
  ([`kinds.md`](kinds.md#schema--exhaustive-and-versioned)) rejects it: the structural-validation
  pass at the merge layer drops any chain-event submission carrying inline `availability` (see
  [`../../../protocol-doctrine.md` §Merge verification](../../../protocol-doctrine.md#merge-verification-and-advisory-locking)).
