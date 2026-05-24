# Custody

**Custody** is the per-SAD authority model for standalone (non-chain-event) [SADs](sad.md): two independent top-level fields on the SAD wrapper that declare who may write the object and who may read it. Custody is decoupled from **availability** (replication and lifecycle), which lives in a sibling top-level field on the same wrapper.

Custody is scoped to the standalone-SAD subset because chain events have a fixed kind-specific schema with no slots for custody or availability fields (see [`sad.md` §Structural shapes](sad.md#structural-shapes)).

This doc states the two custody fields, the asymmetry between them, the four combinations they produce, and the adversarial framing the model is designed against. Identity resolution behind the IEL-event reference is treated as a forward-reference to [`../event-logs/identity-rooting.md`](../event-logs/identity-rooting.md).

## The two fields

Custody is the logical grouping of two optional fields on the SAD object wrapper:

- **`ownerIelEvent`** — an [IEL event SAID](said.md) declaring the writer's identity at the moment of the write. A one-time anchored attestation: the writer's identity is fixed by the IEL prefix the event belongs to, and the IEL state authorizing the write is fixed by the event's tracked `authPolicy`. `None` for anonymous writes.
- **`readPolicy`** — a policy SAID that gates read access at fetch time. The referenced policy is fetched and evaluated against the verified prefix set from a signed read request. Composable via the policy DSL — `identity(X)`, `threshold(N, [...])`, and nested `Policy` nodes are all permitted, so a single `readPolicy` can authorize arbitrary multi-identity read sets without those identities having to share an IEL. `None` for publicly readable content.

The fields are inline on the SAD wrapper (no separate SAID per field). Chain events have no schema slot for either field — chain-event kinds replicate as indivisible units and cannot carry per-event differential authority across links (see [`sad.md` §Structural shapes](sad.md#structural-shapes)). Custody therefore applies to standalone (non-chain-event) SADs.

## Asymmetric semantics

The two fields are intentionally asymmetric:

- **Writes are single-identity-bound.** `ownerIelEvent` is one IEL event SAID, naming one identity at one moment. A SAD object has at most one writer attestation.
- **Reads are composable.** `readPolicy` is a policy SAID; the policy DSL composes identities and thresholds arbitrarily. A SAD object can be readable to "any 2 of 3 named identities" without those identities forming a shared IEL, and the read set can include identities that did not participate in the write.

This matches how custody is actually used in practice. A write is an act by one party at one moment — the writer's identity and the policy in force at that moment are determinate. Reads can be policy-shaped: a private message between two parties, a credential gated by issuer-or-subject, a drop-box that anyone can write but only the operator can drain.

## Two evaluation modes for `ownerIelEvent`

The IEL event SAID supports two ways for a verifier to ask "is the writer authorized?":

- **Point-in-time (frozen).** Resolve the bound IEL event directly, read the `authPolicy` it tracks, and check the write attestation against that policy. The answer reflects the issuance-time governance of the writer's IEL — useful when the verifier wants to know "was this write authorized when it happened?"
- **Identity-current.** Dereference the bound event to its IEL prefix, walk the IEL chain to its current tip, and read the tip's `authPolicy`. The answer reflects the IEL's current state — useful when the verifier wants to know "is the writer's identity still authorized?"

Both modes derive from the single `ownerIelEvent` SAID. The forward-reference to [`../event-logs/identity-rooting.md`](../event-logs/identity-rooting.md) covers the structural pattern (frozen vs identity-current, edge cases at IEL evolutions) that makes both modes well-defined.

## The four combinations

The two fields are independently optional, so a SAD object has four valid custody shapes:

| `ownerIelEvent` | `readPolicy` | Pattern |
|---|---|---|
| `None` | `None` | Public, anonymous write |
| `Some` | `None` | Attested write, public read |
| `None` | `Some` | Anonymous write, controlled read (drop-box) |
| `Some` | `Some` | Attested write, controlled read (private message) |

The combinations are doctrine, not just enumeration. They name distinct application patterns the protocol supports without per-pattern carve-outs:

- **Public anonymous content.** SAD objects whose content is fully self-attesting via SAID (e.g., a public key publication that anyone may retrieve). No writer attestation, no read gating.
- **Attested public content.** A signed credential or policy declaration where the writer's identity matters for downstream evaluation but the content is publicly readable.
- **Drop-box content.** Anonymous writers deliver content that only an authorized reader (the drop-box operator) may retrieve. The writer's identity is not attested at the SAD layer; the operator's authority over the SAD is.
- **Private messages.** Both attested write and controlled read — the standard "from X, readable only by Y" shape.

## Decoupling from availability

Custody and `availability` (a sibling top-level field declaring replication scope, TTL, and one-shot delivery) are independent axes:

- A SAD object can be **widely replicated and custody-gated**: the bytes live on many nodes but every read fetch enforces `readPolicy`.
- A SAD object can be **unreplicated and permissive**: it lives on one node, but anyone who has its SAID can fetch and read.
- A SAD object can be **widely replicated and permissive**: a public credential available everywhere.
- A SAD object can be **unreplicated and custody-gated**: an ephemeral private object scoped to one node.

The decoupling matters because availability is an operational decision (where the bytes live, how long they live, whether retrieval is destructive) while custody is an authority decision (who may write, who may read). The protocol treats them as orthogonal so application designers can compose either axis independently.

## Adversarial framing

The two fields each carry their own adversarial argument; both are enforced at the `vdtid` storage boundary and re-checked by consumers.

- **`ownerIelEvent` forgery requires IEL-level compromise.** An adversary cannot populate `ownerIelEvent` with an arbitrary IEL event SAID and have the resulting SAD object accepted as an authorized write — the writer's signed-request signatures over the SAID's CESR bytes must satisfy the bound IEL's `authPolicy` at write time. Forging a write attestation under an identity the adversary does not control would require compromising that identity's IEL ([`../../../protocol-doctrine.md` §Anchor Tier Elevation](../../../protocol-doctrine.md#anchor-tier-elevation)).
- **`readPolicy` evasion requires policy-level compromise.** An adversary that retrieves the bytes of a read-gated SAD (e.g., from a misconfigured replica or a leaked cache) still cannot satisfy a downstream verifier that re-checks `readPolicy` against the consumer's own verified prefix set. The policy is evaluated on the read side, so a leaked byte stream does not automatically grant authorized-read status.
- **Custody fields are committed by the parent SAID.** `ownerIelEvent` and `readPolicy` are top-level fields on the SAD wrapper, so they participate in the SAD's canonical serialization and the SAID derivation. An adversary cannot substitute a different `ownerIelEvent` (e.g., to attribute the write to a different identity) without changing the SAD's SAID — and the new SAID would not match any reference that names the original.
- **Forbidden on chain events is enforced structurally.** Chain-event kind-schemas have no slot for either field, so the merge layer's structural-validation pass rejects any submission carrying inline `ownerIelEvent` or `readPolicy` on a chain event ([`../../../protocol-doctrine.md` §Routing order](../../../protocol-doctrine.md#routing-order)).
- **Anonymous writes are not unauthorized writes.** `ownerIelEvent = None` declares "no writer attestation" — not "no authorization." A `vdtid` deployment that accepts anonymous writes still applies the operator-configured write-gate (open + rate-limits by default; cred-or-policy-DSL gated under lockdown) at the storage boundary. The anonymity attribute lives in the SAD; the acceptance decision lives in the operator's policy.

The two fields and the four combinations are the protocol-level surface; the consumer-side checks (`evaluate_signed_policy` for `readPolicy`, IEL resolution for `ownerIelEvent`) and the operator-side write-gate are the enforcement surfaces. Both are required — the SAD by itself is just data; the structural authority model is what `vdtid` and consumers enforce against it.
