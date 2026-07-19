# Custody

**Custody** is the per-SAD authority model for standalone (non-chain-event) [SADs](sad.md): a
top-level `custody` field on the SAD wrapper whose value is an inline struct with three optional
sub-fields declaring who may write the object (attested by a direct anchor on the owner's IEL) and
who may read it. Custody is decoupled from **[availability](availability.md)** (replication and
lifecycle), which lives in a sibling top-level field on the same wrapper.

Custody is scoped to the standalone-SAD subset because chain events have a fixed kind-specific
schema with no slots for custody or availability fields (see
[`sad.md` §Structural shapes](sad.md#structural-shapes)).

This doc states the three custody sub-fields, the direct anchor that makes a write attribution
backdate-proof, the asymmetry between the write and read sides, the four combinations they produce,
and the adversarial framing the model is designed against. How an IEL event resolves to members and
threshold is the IEL primitive's — [`../event-logs/iel/`](../event-logs/iel/).

## The three sub-fields

`custody` is a top-level inline struct on the SAD wrapper:

```
custody { owner, pin, readers }
```

The write-binding sub-fields (`owner` / `pin`) move together; `readers` is independent:

- **`owner`** — the writer's IEL **prefix**: which identity wrote the object. The identity is named
  by **prefix, never by a SAID**, because that is what lets a verifier fetch and walk the writer's
  IEL to resolve the write's authority — a SAID has no global index to invert ([`said.md`](said.md);
  [`../../../protocol-doctrine.md` §Negative checks are positive lookups](../../../protocol-doctrine.md#negative-checks-are-positive-lookups)).
- **`pin`** — the **anchor locator**: the SAID of the `previous` of the owner IEL `Ixn` that
  anchored this write, so the anchoring `Ixn` is at `pin`'s serial + 1. A **checked locator**, never
  a trusted claim — an `owner`-bearing SAD **must** carry a `pin`, so a verifier can always find and
  check the anchor that authorizes the write (§Attribution). `owner` and `pin` **move together**
  (both present = an attested write; both absent = anonymous). The SAD's own `kind`
  ([`kinds.md`](kinds.md)) names its type — custody needs no separate namespace field.
- **`readers`** — the **prefix** of a **read-authorization SEL** that names who may read the object,
  or `None` for publicly readable content. Read access is a **membership** check at fetch time: the
  requester's signed read request is resolved to an identity, and that identity must be a current
  member of the `readers` set. Membership is an unbounded, per-participant lookup — resolved one
  requester at a time by the SEL's grant / rescission machinery, never materialized as a set; it is
  **not** a policy expression, and there is no live multi-party evaluation. A SEL is named by
  **prefix**, not a SAID, for the same reason `owner` is — that is what lets a verifier locate and
  walk it. Because the set names **identities**, not raw devices, it tracks the named identity's
  current key state automatically: a device the owner has rotated out no longer reads.

The `custody` struct is inline on the SAD wrapper — it has no `said` field, so per the Recognition
rule in
[`said.md` §Canonical form for SAID computation](said.md#canonical-form-for-said-computation) it is
not a nested SAD; canonical form includes the struct inline, committing its sub-fields to the parent
SAD's SAID. Chain events have no schema slot for `custody` — chain-event kinds replicate as
indivisible units and cannot carry per-event differential authority across links (see
[`sad.md` §Structural shapes](sad.md#structural-shapes)). Custody therefore applies to standalone
(non-chain-event) SADs.

## Attribution requires an anchor

_The **anchor** this section rests on is defined later, under
[`event-logs/`](../event-logs/event-shape.md) (the IEL and SEL primitives). Here, read it as an
append-only commitment recorded on the writer's own identity chain._

A standalone SAD is **not a chain event** — it sits on no chain, so it has no append-only position
of its own. A writer-binding that merely _asserted_ its position (a self-chosen, _trusted_ pin)
would be freely **backdateable**: an adversary who eventually breaks an old, rotated-out key could
point the write at a past position where that key was still authorized and forge a "valid
as-of-then" attestation. Over a long enough horizon any key breaks, so this is a real forgery, not a
hypothetical.

So a write attribution is **corroborated by an append-only anchor**, not self-asserted. **An
`owner`-bearing SAD is anchored directly on the owner's IEL:** the owner authors an `Ixn` on its own
IEL whose `manifest.anchors[]` commits the SAD's `said`. That `Ixn` — a tier-1 (`t_use`) content act
only the owner's `t_use` quorum can author, witnessed, at an append-only position — **is** the write
authorization: it records, non-repudiably, that the owner wrote this SAD. A **credential** is the
named instance (its writer is a body `issuer` field + `issuerPin`; `owner` + `pin` is the same
mechanism under the generic custody names).

- **The `pin` locates the anchor.** `pin` is the SAID of that anchoring `Ixn`'s `previous`, so the
  `Ixn` sits at `pin`'s serial + 1 on the owner's canonical IEL. A verifier goes straight there and
  opens **one** manifest to confirm `previous == pin` and `said ∈ manifest.anchors[]`, never
  scanning a manifest per event. The `pin` is a **checked locator**, never trusted — it only _finds_
  the anchor; the anchor authorizes the write. Non-circular: `pin` (= `previous`) exists before the
  SAD's `said` commits it, and the owner then authors the `Ixn` at the next position.
- **`owner` present ⟹ `pin` present.** An `owner`-bearing SAD with no `pin` has no locator to its
  authorizing anchor, so a verifier reading the raw data cannot tell the owner actually wrote it —
  it is fabricatable and reads ambiguous. So the writer-binding is a **pair**: `owner` iff `pin`
  (both present = an attested write; both absent = anonymous). The SAD's `said` commits both, so
  `(owner, pin)` is tamper-evidently bound to the anchor. (The SAD's `kind` names its type — custody
  needs no separate namespace field.)
- **A SEL is a separate primitive — never custody's mechanism.** SELs are for _evolving_ state or a
  _derived-address lookup_. A SEL may **name** a SAD by `said` — a credential's revocation SEL, for
  instance, derives from its own action-topic + the cred's `said` — but that is the SEL's own
  reference, independent of the SAD's `kind`. **Custody attribution is purely the direct anchor**
  (`owner` + `pin`); it never rides a SEL. (Minting a SAD and a SEL that names it in one instant can
  still put **both** their `said`s in the same `Ixn`'s `anchors[]`.)
- **Enforcement splits by layer.** The SAD structural pass enforces only the **presence** rule
  (`owner` ⟹ `pin`; an `owner`-bearing SAD with no `pin` is rejected). Whether the `Ixn` actually
  exists at `pin + 1`, commits the `said`, and is a valid owner-authored event is verified by
  **`verify_anchored_sad`**, a consumer helper (the store is untrusted — end-verifiability). A
  generic **`verify_sad`** delegates to it whenever the SAD is owned, so a caller never skips the
  anchor check.

## Asymmetric semantics

The write side (`owner` + `pin`) and the read side (`readers`) are intentionally asymmetric:

- **Writes are single-identity-bound.** The writer-binding (`owner` + `pin`) names **one** identity,
  corroborated by a single direct anchor on its IEL (above). A SAD object has at most one writer
  attestation.
- **Reads are membership-gated.** `readers` names the authorized read set as a **membership** — a
  reference to a read-authorization SEL (or `None` for public). A SAD object can be readable to an
  arbitrary set of identities that did not participate in the write, without those identities
  forming a shared IEL; a requester is authorized iff it is a current member of that set, resolved
  by the same participant-blind membership lookup the rest of the system uses — never a live
  multi-party check. `readers` gates only the SAD that declares it — referenced sub-SADs do not
  transitively inherit the parent's read protection. See
  [`compaction.md` §Privacy contract](compaction.md#privacy-contract) for how privacy propagates (or
  doesn't) across the SAD graph.

This matches how custody is actually used in practice. A write is an act by one party at one moment
— the writer's identity and the policy in force at that moment are determinate. Reads can be
membership-shaped: a private message between two parties, a credential gated by issuer-or-issuee, a
drop-box that anyone can write but only the operator can drain.

## Two evaluation modes for the writer-binding

Both modes fetch the writer's IEL by `owner` (never by inverting a SAID) and read its members +
threshold; they differ only in **which position**:

- **Point-in-time (as-issued).** The as-of is the **anchoring position** — the owner IEL `Ixn`
  located by the SAD's `pin` (above), whose `manifest.anchors[]` commits the SAD's `said`. Read the
  IEL's members + threshold **at that anchoring position** and check the write attestation against
  it. The answer reflects how the writer's identity stood at write time — "was this write authorized
  when it happened?" — and it is **backdate-proof**, because the anchoring position is append-only,
  not a self-asserted claim.
- **Identity-current.** Walk the writer's IEL to its **current tip** and read the tip's members +
  threshold. The answer reflects the IEL's current state — "is the writer's identity still
  authorized?"

These two reads — authority at the anchoring position, and authority at the current tip — are the
same as-of / current split the rest of the system uses for chain state. How an IEL event resolves
its members + threshold, and the edge cases at IEL governance changes, are the IEL primitive's —
[`../event-logs/iel/`](../event-logs/iel/).

## The four combinations

The two axes are independently optional, so a SAD object has four valid custody shapes:

| `owner` + `pin` | `readers` | Pattern                                           |
| --------------- | --------- | ------------------------------------------------- |
| `None`          | `None`    | Public, anonymous write                           |
| `Some`          | `None`    | Attested write, public read                       |
| `None`          | `Some`    | Anonymous write, controlled read (drop-box)       |
| `Some`          | `Some`    | Attested write, controlled read (private message) |

(`owner` and `pin` move together — an attested write is **directly anchored** on the owner's IEL,
with `pin` locating that anchor — so the left column is the writer-binding as a whole: `Some` =
attested + anchored, `None` = anonymous.)

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
  every read fetch enforces `readers`.
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
  requires an **`Ixn` on X's IEL** committing the SAD's `said` in `manifest.anchors[]` (located by
  the SAD's `pin`) — a `t_use` content act at X's **current** tip. An adversary who does not control
  X cannot author that anchor — and a broken **old** key cannot either, nor insert one in the past —
  so a write can be neither forged under X's name nor backdated
  ([`../../../protocol-doctrine.md` §Structural authorization](../../../protocol-doctrine.md#structural-authorization)).
- **`readers` evasion requires membership-level compromise.** An adversary that retrieves the bytes
  of a read-gated SAD (e.g., from a misconfigured replica or a leaked cache) still cannot satisfy a
  downstream verifier that re-checks the requester's `readers` membership against the SAD's read
  authorization. Membership is checked on the read side, so a leaked byte stream does not
  automatically grant authorized-read status.
- **Custody fields are committed by the parent SAID.** `owner`, `topic`, and `readers` are
  sub-fields of the top-level `custody` struct on the SAD wrapper, so they participate in the SAD's
  canonical serialization and the SAID derivation. An adversary cannot substitute a different
  `owner` or `topic` (e.g., to re-attribute the write, or to point the anchor derivation elsewhere)
  without changing the SAD's SAID — and the new SAID would not match any reference that names the
  original.
- **Forbidden on chain events is enforced structurally.** Chain-event kind-schemas have no slot for
  `custody`, so the merge layer's structural-validation pass rejects any submission carrying an
  inline `custody` struct on a chain event
  ([`../../../protocol-doctrine.md` §Merge verification](../../../protocol-doctrine.md#merge-verification-and-advisory-locking)).
- **Anonymous writes are not unauthorized writes.** An absent writer-binding (`owner` and `pin` both
  `None`) declares "no writer attestation" — not "no authorization." A storage service deployment
  that accepts anonymous writes still applies the operator-configured write-gate (open + rate-limits
  by default; cred-or-policy-language gated under lockdown) at the storage boundary. The anonymity
  attribute lives in the SAD; the acceptance decision lives in the operator's policy.

The two axes and the four combinations are the protocol-level surface; the consumer-side checks (the
`readers` membership lookup, the `pin`-located anchor resolution for the `owner` + `pin`
writer-binding) and the operator-side write-gate are the enforcement surfaces. Both are required —
the SAD by itself is just data; the structural authority model is what the storage service and
consumers enforce against it.
