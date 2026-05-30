# Event Shape — KEL / IEL / SEL

Canonical reference for the event-log primitives' event taxonomy, field shape, and per-kind structural-validation rules. KEL, IEL, and SEL primitive docs reference this for the underlying shape; doctrine specific to a primitive (anchor tier elevation, divergence rules, federation mechanics, prefix-derivation specifics) lives in the per-primitive docs and in [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md).

This is a **shape reference** — it states what fields exist, which kinds populate them, and how the verifier enforces per-kind field rules. It does not enumerate cross-primitive doctrine (which lives elsewhere).

## Reading order

- [`kel/`](kel/) — KEL primitive specs (currently the only filed primitive)
- [`iel/`](iel/) — IEL primitive (subsequent sub-issue)
- [`sel/`](sel/) — SEL primitive (subsequent sub-issue)
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md) — cross-primitive doctrine: anchor tier elevation, privileged-divergence rules, federation convergence, event-class taxonomy
- [`../../sad/sad.md`](../../sad/sad.md) — SAD layer: chain events are SADs

## Common fields

Five fields appear on every event across all log types. The per-kind shape (defined in §Per-kind structural validation) adds additional fields per kind.

- **`said`** — Blake3-256 hash of the canonical event content with the `said` field blanked (and `prefix` populated with its real value). Identifies the event uniquely.
- **`prefix`** — Blake3-256 hash of the canonical event content with both `said` and `prefix` blanked. Identifies the chain. Derives from the **whole-event content** — not a special tuple. Two distinct inceptions for the same chain are structurally impossible without a Blake3-256 collision.
- **`serial`** — chain position. Inception events have `serial == 0`; all other events have `serial >= 1` monotonic per branch.
- **`previous`** — SAID of the parent event. Forbidden at inception (no parent); required elsewhere.
- **`kind`** — log-type × event-kind discriminator. Drives per-kind structural validation, tier dispatch, and authorization rule selection.

Signatures are **not part of event content** — see [§Authentication & signatures](#authentication--signatures).

## Authentication & signatures

Signatures are not part of the event content — events are pure SAD content. The `said` is the Blake3-256 hash of the content; if a signature were embedded, the SAID would change when the signature is added, but the signature would be over the prior SAID — circular. Signatures live **adjacent** to the event as separate data.

**KEL events** are signed at the wire / storage layer — each KEL event SAD is paired with adjacent signatures: a primary signature (all KEL events) and a recovery signature (tier-3 dual-signed kinds: `Ror` / `Fed` / `Rpr` / `Dec`). The pairing is a wrapper concept; the SAD itself stays signature-free.

**IEL / SEL events** carry no adjacent signatures. They authenticate via their **KEL anchor** — each IEL / SEL event is anchored by a KEL `Ixn` / `Rot` / `Ror` event per the per-primitive anchor rules, and the KEL event's adjacent signature provides authentication. The verifier walks from the IEL / SEL event to the anchoring KEL event and validates the KEL event's signatures.

This composition is what makes the three-tier capability model work uniformly across primitives — IEL / SEL operations inherit their authentication tier from the KEL event they anchor in. See [`../../../../protocol-doctrine.md` §Anchor Tier Elevation](../../../../protocol-doctrine.md#anchor-tier-elevation).

## Cross-cutting fields

Beyond the common fields, a small set of fields appears on multiple kinds with consistent semantics across the primitives that use them. The per-kind structural-validation tables (§Per-kind structural validation) define which kinds populate which; this section names the semantic each field carries when present.

- **`governance`** (`Digest256`) — SAID of a governance policy SAD. Declared at IEL inception (`Fcp` / `Icp`) and SEL `Icp`; evolved via IEL `Evl` and SEL `Evl`.
- **`delegation`** (`Digest256`) — SAID of a delegation policy SAD. Optional at IEL inception; evolved via IEL `Evl`. Gates IEL `Del` / `Rsc`.
- **`delegating`** (`Digest256`) — SAID of an IEL event on the delegator's chain. Set only at IEL `Icp` (for delegated inception); names the delegator. Immutable post-inception.
- **`delegated`** (`Digest256`) — pointer to SAD of IEL prefixes being added (`Del`) or removed (`Rsc`) from the delegated set on the IEL declaring the event. `{ said, prefixes: Vec<Digest256> }`
- **`policyBinding`** (`Digest256`) — cross-chain binding to a policy state. Appears on KEL `Icp` / `Fed` (federation binding to federation IEL `Fcp`).
- **`topic`** (`String`) — application-level discriminator. SEL `Icp` only; participates in prefix derivation alongside `governance` to make the SEL prefix deterministic given those two inputs.
- **`content`** (`Vec<Digest256>`) — generic SAID anchors. Appears on KEL `Ixn` / `Rot` / `Ror` and SEL `Ixn`; the verifier validates each entry as a SAID-shaped token, doesn't constrain what it points at (see [`../../../../protocol-doctrine.md` §Anchor Tier Elevation](../../../../protocol-doctrine.md#anchor-tier-elevation) for downstream-verifier interpretation rules).
- **`nonce`** (`Nonce256`) — opaque random bytes chosen by the inceptor; required on IEL inception (`Fcp` / `Icp`). Makes the IEL prefix unpredictable from outside (camping-defense property). Forbidden on non-inception events.

The KEL-specific key-state fields (`publicKey`, `rotationHash`, `recoveryKey`, `recoveryHash`) and witness params (`witnessThreshold`, `witnessSelectionSize`) are not cross-cutting — they appear only on KEL events with kind-specific semantics; see [`kel/events.md`](kel/events.md).

## `ielEvent`'s two interpretations

`ielEvent` is a `Digest256` that the verifier dereferences. The dereferenced content determines interpretation:

- **Single-IEL binding** — the SAID points to an IEL event directly. The bound state is that IEL at that serial.
- **Multi-IEL binding** — the SAID points to a **binding SAD** that lists multiple IEL event SAIDs. The bound state is each listed IEL at its respective serial.

Same field, two cases. The SAD type discriminator at the dereferenced content tells the verifier which case applies. Multi-IEL binding is the SEL pattern that supports SELs jointly owned by multiple identities; single-IEL binding is the common case.

## Event taxonomy

### KEL — 8 kinds

| Kind | Class | Tier | Purpose |
|---|---|---|---|
| `Fcp` | inception | 1 | Founder pre-federation inception |
| `Icp` | inception | 1 | Standard inception, federation-bound |
| `Ixn` | content | 1 | Interaction; anchors generic content SAIDs |
| `Rot` | privileged | 2 | Rotation; reveals next signing key, commits new |
| `Ror` | privileged | 3 | Rotate-recovery; dual-signed; rotates signing and recovery keys |
| `Fed` | privileged | 3 | Federation-binding mutation; dual-signed |
| `Rpr` | archiving | 3 | Repair; resolves divergent chain by archiving discriminator-losing branch |
| `Dec` | privileged | 3 | Decommission; dual-signed; terminal |

### IEL — 6 kinds

| Kind | Class | Tier | KEL anchor | Purpose |
|---|---|---|---|---|
| `Fcp` | federation inception | 3 | founder `Fed` at v=1 | Federation IEL inception; self-attesting at v=0 via kind-dispatched verifier carve-out |
| `Icp` | inception | 2 | `Rot` per `governance` member | Standard IEL inception; optionally delegated (sets `delegating`) |
| `Evl` | governance mutation | 2 | `Rot` per prior `governance` member | Evolve `governance` and/or `delegation`; must change at least one |
| `Del` | delegation declaration | 2 | `Rot` per `delegation` member | Add prefixes to cumulative delegated set |
| `Rsc` | delegation rescission | 2 | `Rot` per `delegation` member | Remove prefixes from cumulative delegated set. Invalidates any graphs depending on the removed prefixes. To cleanly decomission a delegated IEL, use `Dec` on the delegate IEL |
| `Dec` | terminal | 3 | `Ror` per `governance` member | Terminal; ends IEL on clean linear landing |

Every IEL event is privileged — no content kind; divergent sets cannot form locally on IEL.

### SEL — 6 kinds

| Kind | Class | Tier | KEL anchor | Purpose |
|---|---|---|---|---|
| `Icp` | inception | n/a (permissionless) | — | Permissionless, dedup-equivalent inception; declares `governance` and `topic` |
| `Est` | privileged | 2 | `Rot` per `governance` member | Establishes IEL binding at v=1; carries `ielEvent` |
| `Ixn` | content | 1 | `Ixn` per `governance` member | Content extension; anchors `content` |
| `Evl` | privileged | 2 | `Rot` per prior `governance` member | Evolve `governance` (may be a no-op if ratcheting seal) |
| `Rpr` | archiving | 3 | `Ror` per `governance` member | Repair; resolves a divergent SEL by archiving discriminator-losing branch |
| `Dec` | terminal | 3 | `Ror` per `governance` member | Terminal; ends SEL on clean linear landing |

SEL `Icp` must be submitted in a batch with `Est` to:
1. Allow for deterministic lookup
2. Pin the `ielPrefix` to an event for endorsement.

## Per-kind structural validation

Verifier enforces per-kind field rules. Cells are:

- **req** — field MUST be set on this kind; verifier rejects if absent
- **fbd** — field MUST be unset on this kind; verifier rejects if present
- **opt** — field MAY be set or unset on this kind

Common fields (`said`, `prefix`, `kind`) are always required and not enumerated here. `previous`: forbidden on inception kinds (`Fcp`, `Icp`), required elsewhere. `serial`: 0 on inception, `>=1` elsewhere. Signatures live adjacent to events (not in content) — see [§Authentication & signatures](#authentication--signatures).

### KEL

| Kind | publicKey | rotationHash | recoveryKey | recoveryHash | ielEvent | content | witnessThreshold | witnessSelectionSize |
|---|---|---|---|---|---|---|---|---|
| `Fcp` | req | req | fbd | req | fbd | fbd | fbd | fbd |
| `Icp` | req | req | fbd | req | req | fbd | req | req |
| `Ixn` | fbd | fbd | fbd | fbd | fbd | req | fbd | fbd |
| `Rot` | req | req | fbd | fbd | fbd | opt | fbd | fbd |
| `Ror` | req | req | req | req | fbd | opt | fbd | fbd |
| `Fed` | req | req | req | req | req | fbd | req | req |
| `Rpr` | req | req | req | req | fbd | fbd | fbd | fbd |
| `Dec` | req | fbd | req | fbd | fbd | fbd | fbd | fbd |

(Tier-3 kinds — `Ror` / `Fed` / `Rpr` / `Dec` — additionally have a recovery signature paired adjacent to the event per §Authentication & signatures; not an event field.)

- `ielEvent` on KEL Icp/Fed is the federation IEL event SAID (single-IEL binding — the federation).
- `content` on KEL Ixn is required (≥ 1 entry); on Rot/Ror is optional (≥ 0 entries).
- `Fcp` is at v=0; `Icp` is at v=0; `Fed` is at v ≥ 1 (the founder pattern is `Fed` at v=1 on an `Fcp`-rooted chain).

### IEL

| Kind | nonce | governance | delegation | delegating | delegated |
|---|---|---|---|---|---|
| `Fcp` | req | req | opt | fbd | fbd |
| `Icp` | req | req | opt | opt | fbd |
| `Evl` | fbd | opt[note 1] | opt[note 1] | fbd | fbd |
| `Del` | fbd | fbd | fbd | fbd | req |
| `Rsc` | fbd | fbd | fbd | fbd | req |
| `Dec` | fbd | fbd | fbd | fbd | fbd |

Notes:
1. **`Evl` `governance` / `delegation`** — at least one MUST be set. A no-op `Evl` (neither changes) is rejected. Parallels KEL `Fed`'s "must change one of (federation binding, witness params)" rule.

The `nonce` is required at inception (drives prefix unpredictability per [§Prefix derivation](#prefix-derivation-is-whole-content)). `delegating` is the structural marker for delegated inception — if set, the delegator's outbound `Del` MUST list this prefix (transitively gated by delegator's `delegation` policy).

Authentication is via the KEL anchor per §Authentication & signatures — tier-3 IEL events (`Fcp`, `Dec`) are anchored by a tier-3 KEL event (whose adjacent signatures provide authentication), not by an event-level recovery signature.

### SEL

| Kind | governance | topic | ielEvent | content |
|---|---|---|---|---|
| `Icp` | req | req | fbd | fbd |
| `Est` | fbd | fbd | req | fbd |
| `Ixn` | fbd | fbd | fbd | req |
| `Evl` | opt | fbd | req | fbd |
| `Rpr` | fbd | fbd | fbd | fbd |
| `Dec` | fbd | fbd | fbd | fbd |

- `governance` on `Icp` declares the SEL's gating policy (SAID of a policy SAD). For single-IEL bindings, the common case is `governance = kel(iel_prefix)` — degenerate but explicit. For multi-IEL bindings, an arbitrary policy DSL.
- `ielEvent` on `Est` declares the SEL's first IEL state binding (single IEL event SAID or binding-SAD SAID) at v=1.
- `Evl` carries optional new `governance` and required `ielEvent`; **must change at least one** of (`governance`, `ielEvent`) relative to the prior tracked state — a no-op `Evl` (neither changes) is rejected. This collapses what would otherwise be two events (governance evolution + seal-advance re-ratchet) into one kind. Parallel to KEL `Fed`'s "must change at least one of (federation binding, witness params)" rule.
- `Ixn` / `Rpr` / `Dec` don't carry their own `ielEvent` — they inherit the SEL's tracked binding from the most-recent prior `Est` / `Evl`.
- `topic` on `Icp` is an application-level discriminator; the chain's prefix derives from the whole-Icp content including `governance` and `topic`, so two Icps with the same `(governance, topic)` produce the same prefix (Icp dedup-equivalence).

Authentication is via the KEL anchor per §Authentication & signatures — tier-3 SEL events (`Rpr`, `Dec`) are anchored by a tier-3 KEL event (whose adjacent signatures provide authentication), not by an event-level recovery signature.

## Batching requirements

Some event kinds can only land at merge time as part of a multi-event atomic batch. Per-event structural validation (§Per-kind structural validation) doesn't capture these — they are merge-layer constraints enforced when events arrive together.

**Structurally-required batches:**

- **SEL `[Icp, Est, ...]`** — SEL `Icp` is permissionless and dedup-equivalent (any party's Icp for the same `(governance, topic)` produces the same SAID). The merge layer **rejects bare `[Icp]`** — an Est at v=1 must accompany the Icp (or be in a longer batch containing both). The Est is what raises the per-attempt cost to tier-2 anchor; without it, the camping-defense argument doesn't hold.
- **Federation bootstrap (multi-chain atomic batch)** — interleaves: founder KEL `[Fcp, Fed]` pairs (one per founder KEL), the federation IEL `Fcp` (on the federation IEL chain), and cross-attestation receipts. The federation IEL `Fcp` self-attests via the kind-dispatched verifier carve-out at v=0; founder Fed events at v=1 anchor it from the KEL side. All events land together as a single transaction. See [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) (subsequent sub-issue) for the full ceremony.

**Common operational batches (not structurally required, but conventional):**

- **KEL founder `[Fcp, Fed]`** — a founder KEL's `Fcp` at v=0 is pre-federation; the `Fed` at v=1 declares federation binding. The pair lands together when the founder joins the federation. Bare `Fcp` is structurally valid (the chain stays in pre-federation state) but operationally rare outside the bootstrap pattern.

The per-primitive `merge.md` docs and `federation/bootstrap.md` enumerate the full enforcement rules. This section is the reference index of which kinds participate in batching; detail lives in per-primitive doctrine.

## Cross-log analogy

What each log calls events with the same structural role (after parity renames):

| Structural role | KEL | IEL | SEL |
|---|---|---|---|
| Federation inception | `Fcp` | `Fcp` | — |
| Standard inception | `Icp` | `Icp` | `Icp` (permissionless) |
| Content extension | `Ixn` | — (every event is privileged) | `Ixn` |
| Key rotation | `Rot` / `Ror` | — | — |
| Governance evolution | — | `Evl` | `Evl` |
| Federation re-binding | `Fed` | — | — |
| Cross-chain binding establishment | `Icp` / `Fed` | `Icp` (federation context inherited via parent KEL) | `Est` |
| Cross-chain binding re-ratchet | (re-`Fed`) | — | `Evl` (re-ratchets `ielEvent`; may also change `governance`) |
| Delegation declaration / rescission | — | `Del` / `Rsc` | — |
| Archival (divergence resolution) | `Rpr` | — | `Rpr` |
| Terminal | `Dec` | `Dec` | `Dec` |

## Prefix derivation is whole-content

Prefix derives from the entire event body (with both `said` and `prefix` blanked). It's not a special tuple. Whatever fields are populated on the inception event participate in the prefix. The verifier reconstructs the prefix from canonical-form serialization and rejects any event whose computed prefix doesn't match its declared prefix.

For chains where prefix unpredictability is required as a structural property (IEL), the inception event includes a `nonce` field whose content is opaque random bytes — this makes the prefix unpredictable to outside observers. For chains where prefix is intentionally derivable by external parties (SEL — to support identity-rooted discovery), the inception event omits `nonce` and the prefix derives deterministically from declared content (`governance` + `topic` for SEL).

## Tier dispatch

Tier is determined by event kind, not by policy. Tier names the cryptographic capability required to forge the event — see [`kel/events.md` §Three-tier capability model](kel/events.md#three-tier-capability-model). Tier and policy are orthogonal axes:

- **Policy** = who (the member set authorized for this action — defined in IEL `governance` / `delegation`, SEL `governance`, or KEL-intrinsic dual-signing rules)
- **Tier** = at what auth level (the required KEL anchor capability or dual-signature shape)

The verifier composes both — at every authorization site, it checks the event member is named by the relevant policy AND that they authored at the required tier. The same policy member set may authorize different actions at different tiers (e.g., SEL `governance` members authorize tier-1 `Ixn` AND tier-2 `Est`/`Evl` AND tier-3 `Rpr`/`Dec` under the same member set; SEL event kind dispatches the tier requirement).

See [`../../../../protocol-doctrine.md` §Anchor Tier Elevation](../../../../protocol-doctrine.md#anchor-tier-elevation) for the cross-primitive anchor-tier rules.

## Authorization gating per kind

Brief mapping of which policy gates each event kind. For all non-inception events, gating evaluates against the chain's tracked policy at the parent event — for evolution events that's the policy before this event changes it; for non-evolution events the policy is simply unchanged from the parent's state. (KEL fields like `rotationHash` / `recoveryHash` work the same way — the commitment is on the prior establishment event.)

| Event kind | Gating policy | Notes |
|---|---|---|
| KEL `Fcp` / `Icp` | self (signing key declared in event) | Self-authenticating via prefix derivation |
| KEL `Ixn` | signing key | Tier-1 |
| KEL `Rot` | rotation-key preimage of `rotationHash` | Tier-2 |
| KEL `Ror` / `Fed` / `Rpr` / `Dec` | rotation + recovery preimages of `rotationHash` and `recoveryHash` | Tier-3 dual-signed |
| IEL `Fcp` | self-attesting at v=0 via kind-dispatched carve-out (pool source = `Fcp`'s declared `governance.identity_leaves`) | Anchored from KEL side by founder `Fed` at v=1 |
| IEL `Icp` | self-authorized against declared `governance` | Optionally delegated (delegator's outbound `Del` must list this prefix) |
| IEL `Evl` / `Dec` | `governance` | `Dec` is tier-3 |
| IEL `Del` / `Rsc` | `delegation` | Forbidden if `delegation` is unset on IEL state |
| SEL `Icp` | permissionless (no policy gate) | Dedup-equivalent via prefix derivation |
| SEL `Est` / `Ixn` / `Evl` | `governance` (resolved at `ielEvent` binding) | Tier dispatched by kind (Ixn tier-1; Est/Evl tier-2) |
| SEL `Rpr` / `Dec` | `governance` | Tier-3 dual-signed |

## Naming conventions

- **Three-letter codes.** All event kinds use three-letter abbreviations (Fcp / Icp / Ixn / Rot / Ror / Fed / Rpr / Dec / Evl / Del / Rsc / Est). Consistent across log types.
- **Inception kinds** all named `Icp` (or `Fcp` for federation-context inceptions). Log type disambiguates structural differences.
- **Class names** — `inception`, `content`, `privileged`, `archiving`, `terminal`. The class column on per-log taxonomy tables names the event's chain-state effect.
- **Common names across log types** — events with the same structural role share names: `Ixn` for content extension (KEL + SEL); `Evl` for governance evolution (IEL + SEL); `Rpr` for archival (KEL + SEL); `Dec` for terminal (all three).
- **`Dip` deprecation** — delegated inception was previously a distinct kind on KEL and IEL. It is now folded into `Icp` with an optional `delegating` field. The verifier dispatches the delegated-vs-non-delegated case from whether `delegating` is set, not from a distinct kind.

## Open items

1. **Multi-IEL ratchet semantics.** When SEL `Est` declares a multi-IEL binding via a binding-SAD-listing-multiple-IEL-events, the ratchet rules for subsequent `Evl` events need to be pinned. Does the new binding-SAD on `Evl` need to strictly-advance each listed IEL's event SAID, or can a subset advance? TBD.

2. **Binding-SAD shape.** The binding-SAD that `ielEvent` may point to (multi-IEL case) is a SAD whose content is a list of IEL event SAIDs. Its exact shape — pure list, or a richer structure (e.g., per-entry threshold weights) — is TBD until SEL primitive doctrine lands.

3. **IEL `Dec` policy gating.** IEL `Dec` is gated by `governance` at tier 3. Whether `delegation` plays any role at terminal time (e.g., the cumulative delegated set survives or is invalidated post-Dec) is a SEL/credential-doctrine concern, not an event-shape concern.

4. **SEL Icp permissionless authorization model under explicit `governance`.** SEL Icp now declares `governance` explicitly (vs. derived in earlier drafts). Camping defense relies on Icp dedup-equivalence — parties producing the same `(governance, topic)` produce the same Icp. Open: do we want an explicit operator-policy requiring `governance` to be derived deterministically from `topic` and a single referenced IEL prefix (preserving the lookup-by-identity discoverability)? Or is `governance` truly free-form (apps that want lookup-by-identity adopt the convention themselves)?
