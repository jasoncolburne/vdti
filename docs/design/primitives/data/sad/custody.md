# Custody

**Custody** is the per-SAD authority model for standalone (non-chain-event) [SADs](sad.md): a
top-level `custody` field on the SAD wrapper whose value is an inline struct with three optional
sub-fields declaring who may write the object (attested via a SEL anchor) and who may read it.
Custody is decoupled from **[availability](availability.md)** (replication and lifecycle), which
lives in a sibling top-level field on the same wrapper.

Custody is scoped to the standalone-SAD subset because chain events have a fixed kind-specific
schema with no slots for custody or availability fields (see
[`sad.md` §Structural shapes](sad.md#structural-shapes)).

This doc states the three custody sub-fields, the SEL anchor that makes a write attribution
backdate-proof, the asymmetry between the write and read sides, the four combinations they produce,
and the adversarial framing the model is designed against. How an IEL event resolves to members and
threshold is the IEL primitive's — [`../event-logs/iel/`](../event-logs/iel/).

## The three sub-fields

`custody` is a top-level inline struct on the SAD wrapper:

```
custody { owner, topic, readPolicy }
```

Each sub-field is independently optional:

- **`owner`** — the writer's IEL **prefix**: which identity wrote the object. The identity is named
  by **prefix, never by a SAID**, because that is what lets a verifier fetch and walk the writer's
  IEL to resolve the write's authority — a SAID has no global index to invert ([`said.md`](said.md);
  [`../../../protocol-doctrine.md` §Negative checks are positive lookups](../../../protocol-doctrine.md#negative-checks-are-positive-lookups)).
- **`topic`** — the doc's **namespace / schema**: a discriminator naming what kind of document this
  is. With `owner` it locates the write's SEL anchor (next section). A `topic` is either a
  **vdti-reserved** namespace (`CRED_REVOCATION_TOPIC`, `DLG_RSC_TOPIC`, `DOC_RSC_TOPIC`, …) **or**
  an author-defined topic paired with its own schema. `owner` and `topic` are **both present** (an
  attested write) or **both absent** (an anonymous write) — the writer-binding is both-or-neither.
- **`readPolicy`** — the SAID of a [policy](../../policy/policy.md) that gates read access at fetch
  time. The referenced policy is fetched and evaluated in **current mode**
  ([`../../policy/evaluation.md`](../../policy/evaluation.md)) against the verified prefixes of a
  signed read request. Composable via the policy language — `id(X)`, `thr(N, [...])`, and nested
  `pol` are all permitted, so a single `readPolicy` can authorize an arbitrary multi-identity read
  set without those identities sharing an IEL. Because the language names **identities** (`id(X)`),
  not raw devices, a read grant tracks the named identity's current key state automatically: a
  device the owner has rotated out no longer satisfies `id(X)`, so it can no longer read. `None` for
  publicly readable content.

The `custody` struct is inline on the SAD wrapper — it has no `said` field, so per the Recognition
rule in
[`said.md` §Canonical form for SAID computation](said.md#canonical-form-for-said-computation) it is
not a nested SAD; canonical form includes the struct inline, committing its sub-fields to the parent
SAD's SAID. Chain events have no schema slot for `custody` — chain-event kinds replicate as
indivisible units and cannot carry per-event differential authority across links (see
[`sad.md` §Structural shapes](sad.md#structural-shapes)). Custody therefore applies to standalone
(non-chain-event) SADs.

## Attribution requires a SEL anchor

_The **SEL anchor** this section rests on is defined later, under
[`event-logs/`](../event-logs/event-shape.md) (the SEL and IEL primitives). Here, read it as an
append-only commitment recorded on the writer's own identity chain._

A standalone SAD is **not a chain event** — it sits on no chain, so it has no append-only position
of its own. A writer-binding that merely _asserted_ its position (a self-chosen pin) would be freely
**backdateable**: an adversary who eventually breaks an old, rotated-out key could point the write
at a past position where that key was still authorized and forge a "valid as-of-then" attestation.
Over a long enough horizon any key breaks, so this is a real forgery, not a hypothetical.

So a write attribution is **corroborated by an append-only anchor**, not self-asserted. **The
custody rule: direct-anchor an immutable SAD that is _presented_; SEL-wrap anything _mutable_ or
_looked-up-by-address_.** A **credential** is the direct-anchor case — the issuer anchors its
issuance commitment on its own IEL and presents the cred, which needs no derived-address lookup, so
a cred carries **no `custody { owner, topic }`** (its writer is a body `issuer` field, attributed by
that anchor). The `custody` writer-binding covers the **other** case: a standalone SAD a holder must
**self-locate by a derived address** (the revocation / rescission lookup SELs; any looked-up
attested document). Such an `owner`-bearing SAD **must be anchored by a SEL** (the
[SEL primitive](../event-logs/sel/)):

- The anchoring SEL's prefix is **`derive(owner, topic, data)`**, where the `data` argument **is the
  SAD's SAID** (`SEL.owner == owner`, `SEL.data == said`). The SEL's **serial-1 event (its v1 — a
  `Pin`)** is anchored by an owner IEL `Ixn` whose **append-only position is the write's as-of**
  (the `Icp` itself is never anchored — it rides `v1.previous`, per the SEL inception rule) — it
  cannot be inserted in the past, so the attribution cannot be backdated. Forging it would require a
  fresh IEL `Ixn` at the owner's **current** tip, which a rotated-out or broken old key cannot
  author.
- The anchor is **self-locating**: a holder re-derives the SEL prefix from the doc it holds
  (`derive(owner, topic, said)`) and walks that SEL **by prefix** — no SAID is inverted (see
  [`said.md`](said.md)). This mirrors how a credential holder reaches a cred's revocation lookup SEL
  by re-deriving its address.
- Enforcement is **structural at two levels**: the storage service refuses to land an
  `owner`-bearing SAD without its corroborating SEL (`SEL.owner == owner ∧ SEL.data == said`),
  **and** a consumer verifies the anchor independently — the store is untrusted (end-verifiability).

The rule: **`owner` is present iff `topic` is present iff the anchoring SEL exists.** An anonymous
write carries none of the three; an attested write carries all of them. Because the doc's SAID
commits `owner` and `topic`, the triple `(owner, topic, said)` is tamper-evidently bound to the
anchor location — altering any of them changes the SAID and breaks the derivation.

## Asymmetric semantics

The write side (`owner` + `topic`) and the read side (`readPolicy`) are intentionally asymmetric:

- **Writes are single-identity-bound.** The writer-binding (`owner` + `topic`) names **one**
  identity and its document namespace, corroborated by a single SEL anchor (above). A SAD object has
  at most one writer attestation.
- **Reads are composable.** `readPolicy` is a policy SAID; the policy language composes identities
  and thresholds arbitrarily. A SAD object can be readable to "any 2 of 3 named identities" without
  those identities forming a shared IEL, and the read set can include identities that did not
  participate in the write. `readPolicy` gates only the SAD that declares it — referenced sub-SADs
  do not transitively inherit the parent's read protection. See
  [`compaction.md` §Privacy contract](compaction.md#privacy-contract) for how privacy propagates (or
  doesn't) across the SAD graph.

This matches how custody is actually used in practice. A write is an act by one party at one moment
— the writer's identity and the policy in force at that moment are determinate. Reads can be
policy-shaped: a private message between two parties, a credential gated by issuer-or-issuee, a
drop-box that anyone can write but only the operator can drain.

## Two evaluation modes for the writer-binding

Both modes fetch the writer's IEL by `owner` (never by inverting a SAID) and read its members +
threshold; they differ only in **which position**:

- **Point-in-time (as-issued).** The as-of is the **SEL anchor's** position — the owner IEL `Ixn`
  that anchored the SAD's SEL (located by `derive(owner, topic, said)`, above). Read the IEL's
  members + threshold **at that anchoring position** and check the write attestation against it. The
  answer reflects how the writer's identity stood at write time — "was this write authorized when it
  happened?" — and it is **backdate-proof**, because the anchoring position is append-only, not a
  self-asserted claim.
- **Identity-current.** Walk the writer's IEL to its **current tip** and read the tip's members +
  threshold. The answer reflects the IEL's current state — "is the writer's identity still
  authorized?"

Both modes mirror the policy layer's two evaluation modes
([`../../policy/evaluation.md`](../../policy/evaluation.md)). How an IEL event resolves its
members + threshold, and the edge cases at IEL governance changes, are the IEL primitive's —
[`../event-logs/iel/`](../event-logs/iel/).

## The four combinations

The two axes are independently optional, so a SAD object has four valid custody shapes:

| `owner` + `topic` | `readPolicy` | Pattern                                           |
| ----------------- | ------------ | ------------------------------------------------- |
| `None`            | `None`       | Public, anonymous write                           |
| `Some`            | `None`       | Attested write, public read                       |
| `None`            | `Some`       | Anonymous write, controlled read (drop-box)       |
| `Some`            | `Some`       | Attested write, controlled read (private message) |

(`owner` and `topic` move together — both-or-neither, and an attested write is anchored by its SEL —
so the left column is the writer-binding as a whole: `Some` = attested + anchored, `None` =
anonymous.)

The combinations are doctrine, not just enumeration. They name distinct application patterns the
protocol supports without per-pattern carve-outs:

- **Public anonymous content.** SAD objects whose content is fully self-attesting via SAID (e.g., a
  public key publication that anyone may retrieve). No writer attestation, no read gating.
- **Attested public content.** A signed credential or policy declaration where the writer's identity
  matters for downstream evaluation but the content is publicly readable.
- **Drop-box content.** Anonymous writers deliver content that only an authorized reader (the
  drop-box operator) may retrieve. The writer's identity is not attested at the SAD layer; the
  operator's authority over the SAD is.
- **Private messages.** Both attested write and controlled read — the standard "from X, readable
  only by Y" shape.

## Decoupling from availability

Custody and [`availability`](availability.md) (a sibling top-level field declaring replication
scope, TTL, and one-shot delivery) are independent axes:

- A SAD object can be **widely replicated and custody-gated**: the bytes live on many nodes but
  every read fetch enforces `readPolicy`.
- A SAD object can be **unreplicated and permissive**: it lives on one node, but anyone who has its
  SAID can fetch and read.
- A SAD object can be **widely replicated and permissive**: a public credential available
  everywhere.
- A SAD object can be **unreplicated and custody-gated**: an ephemeral private object scoped to one
  node.

The decoupling matters because availability is an operational decision (where the bytes live, how
long they live, whether retrieval is destructive) while custody is an authority decision (who may
write, who may read). The protocol treats them as orthogonal so application designers can compose
either axis independently.

## Adversarial framing

The two axes each carry their own adversarial argument; both are enforced at the storage boundary
and re-checked by consumers.

- **Writer-binding forgery requires IEL-level compromise.** Attributing a write to identity X
  requires a **SEL anchor on X's IEL** (`SEL.owner == X ∧ SEL.data == said`), whose v1 (the `Pin`)
  is anchored by a fresh IEL `Ixn` at X's **current** tip satisfying X's `t_use` threshold. An
  adversary who does not control X cannot author that anchor — and a broken **old** key cannot
  either, nor insert one in the past — so a write can be neither forged under X's name nor backdated
  ([`../../../protocol-doctrine.md` §Structural authorization](../../../protocol-doctrine.md#structural-authorization)).
- **`readPolicy` evasion requires policy-level compromise.** An adversary that retrieves the bytes
  of a read-gated SAD (e.g., from a misconfigured replica or a leaked cache) still cannot satisfy a
  downstream verifier that re-checks `readPolicy` against the consumer's own verified prefix set.
  The policy is evaluated on the read side, so a leaked byte stream does not automatically grant
  authorized-read status.
- **Custody fields are committed by the parent SAID.** `owner`, `topic`, and `readPolicy` are
  sub-fields of the top-level `custody` struct on the SAD wrapper, so they participate in the SAD's
  canonical serialization and the SAID derivation. An adversary cannot substitute a different
  `owner` or `topic` (e.g., to re-attribute the write, or to point the anchor derivation elsewhere)
  without changing the SAD's SAID — and the new SAID would not match any reference that names the
  original.
- **Forbidden on chain events is enforced structurally.** Chain-event kind-schemas have no slot for
  `custody`, so the merge layer's structural-validation pass rejects any submission carrying an
  inline `custody` struct on a chain event
  ([`../../../protocol-doctrine.md` §Merge verification](../../../protocol-doctrine.md#merge-verification-and-advisory-locking)).
- **Anonymous writes are not unauthorized writes.** An absent writer-binding (`owner` and `topic`
  both `None`) declares "no writer attestation" — not "no authorization." A storage service
  deployment that accepts anonymous writes still applies the operator-configured write-gate (open +
  rate-limits by default; cred-or-policy-language gated under lockdown) at the storage boundary. The
  anonymity attribute lives in the SAD; the acceptance decision lives in the operator's policy.

The two axes and the four combinations are the protocol-level surface; the consumer-side checks
(current-mode policy evaluation for `readPolicy`, SEL-anchor resolution for the `owner` + `topic`
writer-binding) and the operator-side write-gate are the enforcement surfaces. Both are required —
the SAD by itself is just data; the structural authority model is what the storage service and
consumers enforce against it.
