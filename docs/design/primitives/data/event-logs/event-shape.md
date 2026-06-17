# Event Shape — KEL / IEL / SEL

Canonical reference for the event-log primitives' event taxonomy, field shape, and per-kind structural-validation rules. KEL, IEL, and SEL primitive docs reference this for the underlying shape; doctrine specific to a primitive (anchor tier elevation, divergence rules, federation mechanics, prefix-derivation specifics) lives in the per-primitive docs and in [`../../../protocol-doctrine.md`](../../../protocol-doctrine.md).

This is a **shape reference** — it states what fields exist, which kinds populate them, and how the verifier enforces per-kind field rules. It does not enumerate cross-primitive doctrine (which lives elsewhere).

## Reading order

- [`kel/`](kel/) — KEL primitive specs (subsequent sub-issue)
- [`iel/`](iel/) — IEL primitive (subsequent sub-issue)
- [`sel/`](sel/) — SEL primitive (subsequent sub-issue)
- [`../../../protocol-doctrine.md`](../../../protocol-doctrine.md) — cross-primitive doctrine: anchor tier elevation, privileged-divergence rules, federation convergence, event-class taxonomy
- [`../policy/policy.md`](../policy/policy.md) — the policy DSL the `governance` / `authentication` / `delegation` / `operation` fields point at
- [`../sad/sad.md`](../sad/sad.md) — SAD layer: chain events are SADs

## Common fields

Five fields appear on every event across all log types. The per-kind shape (defined in §Per-kind structural validation) adds additional fields per kind.

| Field | Type | Description |
|---|---|---|
| `said` | Digest256 | Hash of the canonical event content with the `said` field blanked (and `prefix` populated with its real value). Identifies the event uniquely. |
| `prefix` | Digest256 | Hash of the canonical event content with both `said` and `prefix` blanked. Identifies the chain. Derives from the **whole-event content** — not a special tuple. Two distinct inceptions for the same chain are structurally impossible without a Blake3-256 collision. |
| `serial` | u64 | Chain position. Inception events have `serial == 0`; all other events have `serial >= 1` monotonic per branch. |
| `previous` | Digest256 | SAID of the parent event. Forbidden at inception (no parent); required elsewhere. |
| `kind` | String | Log-type × event-kind discriminator. Drives per-kind structural validation, tier dispatch, and authorization rule selection. |

Signatures are **not part of event content** — see [§Authentication & signatures](#authentication--signatures).

## Authentication & signatures

Signatures are not part of the event content — events are pure SAD content. The `said` is the Blake3-256 hash of the content; if a signature were embedded, the SAID would change when the signature is added, but the signature would be over the prior SAID — circular. Signatures live **adjacent** to the event as separate data.

**KEL events** are signed by the controller **when authored**. The signatures are carried adjacent to the event SAD (paired with it at the wrapper / storage layer), never embedded in the content: a primary signature (all KEL events) and a recovery signature (tier-3 dual-signed kinds: `Ror` / `Fed` / `Rpr` / `Dec`). The pairing is a wrapper concept; the SAD itself stays signature-free. The **recovery key** behind that second signature is the **break-glass reserve** for these high-assurance operations (repair / recovery-rotation / federation / decommission) — **not** a device-recovery-from-loss mechanism: a lost or compromised device is rotated out at the identity layer via an IEL membership change (identity is decoupled from device).

**IEL / SEL events** carry no adjacent signatures. They authenticate via their **KEL anchor** — each IEL / SEL event is anchored by a KEL `Ixn` / `Rot` / `Ror` event per the per-primitive anchor rules, and the KEL event's adjacent signature provides authentication. The verifier walks from the IEL / SEL event to the anchoring KEL event and validates the KEL event's signatures.

This composition is what makes the three-tier capability model work uniformly across primitives — IEL / SEL operations inherit their authentication tier from the KEL event they anchor in. See [`../../../protocol-doctrine.md` §Anchor Tier Elevation](../../../protocol-doctrine.md#anchor-tier-elevation).

## Cross-cutting fields

Beyond the common fields, a small set of fields appears on multiple kinds with consistent semantics across the primitives that use them. The per-kind structural-validation tables (§Per-kind structural validation) define which kinds populate which; this section names the semantic each field carries when present. **Logs** names the subset of {KEL, IEL, SEL} the field appears on (kind names recur across logs, so Events alone would be ambiguous); **Events** names the kinds that carry it.

| Field | Type | Logs | Events | Description |
|---|---|---|---|---|
| `governance` | `Digest256` | IEL, SEL | IEL `Fcp` / `Icp` / `Evl`; SEL `Icp` / `Evl` | SAID of a governance Policy SAD: the chain's **self-mutation** authority. On an IEL it gates the IEL's own lifecycle events (`Evl` / `Dec`, i.e. policy and roster changes — including which device keys the policies' `dev()` leaves name — and decommission); on a SEL it gates the SEL's lifecycle events (`Evl` / `Rpr` / `Dec`). Declared at inception; evolved via `Evl`. It is **never** what an external `id(X)` leaf evaluates — that is `authentication`. |
| `authentication` | `Digest256` | IEL | `Fcp` / `Icp` / `Evl` | SAID of an authentication Policy SAD: an IEL's **outward act-as** authority. It is what every external `id(prefix)` leaf and each `grp` member resolves to (see [`../policy/leaf-semantics.md`](../policy/leaf-semantics.md)). Required at inception; evolved via `Evl` (gated by `governance`). Outward-facing — it **never** gates the IEL's own chain events (so there is no circularity: an IEL's log is governance-gated, not authentication-gated). |
| `delegation` | `Digest256` | IEL | `Fcp` / `Icp` / `Evl` | SAID of a delegation Policy SAD. Optional at inception; evolved via `Evl` (gated by `governance`). Gates IEL `Del` / `Rsc`. |
| `operation` | `Digest256` | SEL | `Icp` / `Evl` | SAID of an operation Policy SAD: a SEL's **operational write** authority over its own log. Gates SEL operational events `Est` / `Ixn`. Declared at `Icp`; evolved via `Evl` (gated by `governance`). (Named `operation` — not `authentication` — because it *does* gate the SEL's own events, the opposite of IEL `authentication`'s never-gates-own-log meaning; a SEL has no act-as identity.) |
| `roster` | `Digest256` | IEL | `Fcp` / `Icp` / `Evl` | SAID of a roster SAD mapping **group label → set of member IEL prefixes** (a member may sit in several groups; group labels match `^[a-z_-]{1,16}$`). Backs the policy DSL's `grp(group)` / `grp(prefix, group)` expansion. **Roster-presence is the IEL's immutable kind signal**: an IEL is **aggregate** iff it carries a `roster` (the federation `Fcp` always does), **singleton** iff it has none. Declared at `Icp`, evolved via `Evl` (gated by `governance`); a singleton `Icp` (no roster) can never gain one, and an aggregate's roster may evolve but never be nulled. |
| `delegating` | `Digest256` | IEL | `Icp` / serial-1 `Evl` | The self-recording delegation link on a delegated IEL. It holds two values across the two-event handshake (see [§Delegation handshake](#delegation-handshake)): on the delegate's `Icp` it is the **delegator's prefix** (binding the delegate's identity to the delegator through prefix derivation); on the batched serial-1 `Evl` it is the **SAID of the delegator's `Del` event** (the back-pointer that names the authorizing event on the delegator's chain). The verifier disambiguates the two by position. |
| `delegated` | `Digest256` | IEL | `Del` / `Rsc` | Pointer to SAD of IEL prefixes being added (`Del`) or removed (`Rsc`) from the delegated set on the IEL declaring the event. `{ said, prefixes: Vec<Digest256> }`. |
| `federationBinding` | `Digest256` | KEL | `Icp` / `Fed` | The federation IEL event SAID the chain binds to (federation binding to federation IEL `Fcp`). A **direct event SAID**, not a pin SAD. |
| `policyPin` | `Digest256` | SEL | `Est` (required) / `Evl` (on binding change) | The SAID of the SEL's **pin SAD** (see [§`policyPin`](#policypin)); **required on `Est`**, **optional on `Evl`** — stated only when the binding changes, else inherited. |
| `topic` | `String` | SEL | `Icp` | Application-level discriminator; participates in prefix derivation alongside `governance` and `operation` to make the SEL prefix deterministic given those inputs. |
| `manifest` | `Digest256` | KEL | `Ixn` / `Rot` / `Ror` | SAID of a manifest SAD `{ said, anchors: Vec<Digest256> }` holding the event's generic SAID anchors (the same SAD-reference shape as `delegated`). The event row carries only the SAID; the anchor list lives in the SAD, separately custody-able — the chain log never exposes what the event anchors. The verifier validates each `anchors` entry as a SAID-shaped token, doesn't constrain what it points at (see [`../../../protocol-doctrine.md` §Anchor Tier Elevation](../../../protocol-doctrine.md#anchor-tier-elevation) for downstream-verifier interpretation rules). This `anchors` array is what the policy DSL's `dev`-leaf anchor check reads (see [§Policy DSL reconciliations](#policy-dsl-reconciliations)). |
| `document` | `Digest256` | SEL | `Ixn` | SAID of the published document — a single opaque SAD. The verifier validates it as a SAID-shaped token and does not constrain or inspect its contents. Not anchors; never read as a policy anchor (unlike KEL `manifest`). |
| `nonce` | `Nonce256` | IEL | `Fcp` / `Icp` | Opaque random bytes chosen by the inceptor; required at inception. Makes the IEL prefix unpredictable from outside (camping-defense property). Forbidden on non-inception events. |

The KEL-specific key-state fields (`publicKey`, `rotationHash`, `recoveryKey`, `recoveryHash`) and witness params (`witnessThreshold`, `witnessSelectionSize`) are not cross-cutting — they appear only on KEL events with kind-specific semantics; see [`kel/events.md`](kel/events.md).

## IEL policy fields & membership shape

An IEL carries **three** policy references with distinct roles — none interchangeable:

- **`governance`** — internal self-mutation gate (`Evl` / `Dec`; policy and roster changes, including which device keys the policies' `dev()` leaves name). Required at inception.
- **`authentication`** — outward act-as policy; the only one an external `id(X)` evaluates. Required at inception.
- **`delegation`** — optional `Del` / `Rsc` gate.

The IEL is one of two **kinds**, fixed at inception by whether the `Icp` declares a `roster` (presence is immutable), and the kind constrains what those three policies may contain (the constraint is on an IEL's *own* policies only — general application / issuance / withdrawal policies keep the full DSL surface):

- **Singleton** (no `roster`) — bottoms out at device keys. Its three policies may contain only `dev()` leaves under `thr` / `wgt` / `and` — no `grp` / `id` / `del` / `pol`. Its `authentication` must be non-empty (≥ 1 satisfiable `dev`), or the identity can never act. A singleton is the base case the `id(...)` recursion terminates at.
- **Aggregate** (carries a `roster`) — composed of member identities. Its three policies may contain only one-arg `grp(group)` arrays (its own roster only, never a foreign `grp(prefix, group)`) under `thr` / `wgt` / `and` — no bare `id` / `dev` / `del`, no `pol`. An aggregate must be **born with a non-empty roster** (else ungovernable). The federation `Fcp` is aggregate-shaped (its founding members are its roster).

See [`../policy/iel-policy-structure.md`](../policy/iel-policy-structure.md) for the DSL-level constraint these kinds impose; the `roster` field (whose presence is the immutable singleton/aggregate kind signal) and the roster-less singleton `Icp` shape are the **event-shape facts** this doc settles.

**`Evl` validates the {roster, policies} pair.** An `Evl` may change any of {`governance`, `authentication`, `delegation`, `roster`, `delegating`} (≥ 1) and carries the full roster + policy state. The verifier enforces **referential integrity on the post-application pair**: every `grp(group)` in the three policies must resolve to a group in the post-event roster. So an `Evl` that drops a roster group still referenced by a policy is rejected — to retire a group, drop its policy references in the same `Evl` (or a prior one). Either may change in isolation; the only constraint is that the post-`Evl` pair still verifies. No committed state can hold a dangling reference.

**Cycle guard.** Aggregate-of-aggregate membership must be **acyclic**. The verifier carries a visited-set in its `id(...)`-resolution walk so a membership cycle denies rather than loops; roster-write may additionally forbid self-membership as a first line. (The recursion is also backstopped by the always-passed `max_depth`.)

The exact on-chain roster-SAD schema and the composer-time mechanics by which `grp` resolves to its members are partly an implementation concern — settled in shape here, provisional in detail (as [`../policy/`](../policy/) flags).

## Delegation handshake

Delegated inception is **not** a distinct event kind — it is an `Icp` with `delegating` set, recorded over a **two-event handshake** so the verifier can walk *up* from a delegate `D` to its delegator `X` without enumerating `X`'s (unbounded, delegate-side) delegated set. `D` **self-records** the link on its own chain:

1. **`D.Icp.delegating` = `X`'s prefix.** `X`'s prefix is known a-priori (no SAID cycle) and participates in `D`'s prefix derivation, so `D`'s identity is cryptographically **bound to `X`**.
2. **A serial-1 `Evl`, batched with the `Icp`,** evolves `delegating` to the **SAID of `X`'s `Del` event** — the event on `X`'s chain that lists `D`'s prefix, known only after `X.Del` exists, and still identifying `X` because the SAID resolves to an event on `X`'s chain. This reuses the privileged `Evl` (no new IEL kind, no local-divergence break); the `Del`-event SAID is one of the things an `Evl` may change.

Two merge-layer rules (parallel to the SEL `[Icp, Est]` pairing) keep the handshake unforgeable and atomic — **neither event is valid on its own**:

- `delegating`-as-SAID appears **only** on a serial-1 `Evl` that follows a `delegating`-`Icp`.
- A `delegating`-`Icp` **must** batch with that serial-1 `Evl` — they land together or not at all.

**Consistency check (verifier).** The serial-1 `Evl`'s `Del` SAID must resolve to a **`Del`** event on the chain `D.Icp.delegating` names — the lookup rejects any other kind — and that `Del` must list `D`'s prefix in its `delegated` set. See [`../policy/delegation.md`](../policy/delegation.md) for the full self-traversing check. **Sequencing** needs no cross-chain atomic transaction: `X.Del` (listing `D`'s prefix) lands first, then `D`'s atomic `[Icp, Evl]` batch references it.

**Resting state.** A fully-formed delegated IEL's tracked `delegating` state is the **`Del`-event SAID** (the serial-1 `Evl` value). The `Icp`-prefix value is transient *within* the atomic `[Icp, Evl]` batch and is never the resting state — the two land together, so any formed delegated IEL already has a SAID-valued `delegating`.

The reciprocal authorization lives on `X`'s chain: the delegator's outbound `Del` must list `D`'s prefix (gated by `X`'s `delegation` policy). See [`../policy/delegation.md`](../policy/delegation.md) for the self-traversing verification flow the handshake enables.

## `policyPin`

`policyPin` is a `Digest256` — the SAID of a **pin SAD**: the SEL's anchored **pinning** over its two policies, `governance` and `operation`. A pin is a security **linkage-commitment** — tamper-evidence that the event's authorization context references *that* specific chain state, so an adversary cannot substitute a different one. It is **not a lookup and not a freeze**: the verifier always walks every referenced chain to tip (end-verifiability; revocation scans never stop early), and the pins ride underneath that walk as committed linkages. Tip-vs-as-of is a property of the **evaluation function**, never of a leaf — anchored evaluation consumes pins and resolves as-of; the live read-time identity proof resolves at tip and ignores pins.

The SEL flow *is* the anchored flow. To verify a SEL event, the verifier evaluates the event's gating policy in **anchored mode** against the matching labeled pinning — `governance` for `Evl` / `Rpr` / `Dec`, `operation` for `Est` / `Ixn`. Both policies are pinned because `Ixn` **inherits** the tracked `policyPin`: the SEL's operational writes are anchored-verified on the walk exactly like its governance events. How each leaf consumes its slot is the policy layer's contract — see [`../policy/pinning.md`](../policy/pinning.md) and [`../policy/leaf-semantics.md`](../policy/leaf-semantics.md); per-leaf resolution is not restated here.

The pin is **always a SAD** — event-log rows hold a fixed-size SAID (events live in PostgreSQL rows, SADs in the SAD store), so the variable-length pinning is never inlined in the event.

The pin SAD is a **labeled collection of positional pinnings** — one array per SEL policy: `{ said, governance: [marker_said, …], operation: [marker_said, …] }`. The top-level labels are the policy names in the clear (event logs are public — nothing leaks); the slots inside each array are **positional and shallow** — one entry per `id` / `grp` occurrence in the SEL's `governance` / `operation` **policy text** (**not** the fully-expanded graph), in the verifier's **pre-order walk order**, with no per-leaf labels so policy internals don't leak (the verifier pairs each slot to its prefix by walking the policy text in the same order). Concretely: `id(X)` lays **one** slot — X's IEL `Evl`/`Icp` state-marker — whether X is a singleton or an aggregate; `thr(2, [id(A), id(B), id(C)])` lays three; a foreign `grp(X, group)` lays **one** (X's marker, fixing X's roster as-of it); `del` lays none; and `dev` **cannot occur** (a SEL `governance` / `operation` is a general policy, so a bare `dev` is a placement error — DQ2). So **every entry is an `id` / `grp` `Evl`/`Icp` state-marker** — there is no `dev`-slot / prior-event form in a `policyPin`. (The `dev` / KEL anchor positions **are** pinned — separately, in the **deep per-event authorizing evidence** (see *State vs. evidence* below), never in a `policyPin`: the pin fixes which IEL version, the per-event evidence fixes which device positions signed.) The common single-identity SEL (`governance = id(P)`, `operation = id(P)`) is a one-slot-each pinning. Encoding follows [`../sad/said.md`](../sad/said.md) (qb64 / JCS).

A **stated** `policyPin` is **full — no null slots**. The **current** pin — the one most recently stated (at `Est`, or at an `Evl` that changed the binding) — is the SEL's standing context, **inherited** by every later `Ixn` **and by any `Evl` that omits the pin**, so it must let **any** combination of the policy's directly-named parties endorse (a null `id` / `grp` slot would make that party's combinations unverifiable), and the forward floor (below) needs a marker for **every** directly-referenced IEL chain. Its slot count is simply the number of `id` / `grp` occurrences in the policy text — bounded by the policy itself; no roster or authentication expansion happens here. Nulls live only in the **deep per-event authorizing evidence** (below) — e.g. a credential's per-issuer anchor pinning, where the issuer evidences only its own contributing leg — **never** in a `policyPin`.

The pin is set at `Est` (v=1) and ratcheted forward by the governance-gated `Evl` along a **per-chain forward-only floor** (see [`../../../protocol-doctrine.md` §Per-Chain Forward-Only Floor](../../../protocol-doctrine.md#per-chain-forward-only-floor-sel-specific)). As the verifier walks the SEL chain it derives, per directly-referenced **IEL prefix** `Z` (the `id` / `grp` prefixes in the policy text), the running `chain_floor[Z]` = the maximum marker-serial any prior **surviving** pin's slots referenced on `Z`; a new pin is valid iff **every** slot referencing `Z` at marker `m` has `m.serial ≥ chain_floor[Z]`, and the floor then advances to the running max. The floor is **cumulative and retained per prefix across gaps** — it is the running max over **all** prior surviving pins, **not** a parent-relative check against only the immediately-preceding pin: a later pin that **omits** `Z` does not clear `Z`'s floor, and a `Z` dropped then **re-referenced** is floored by that same running max — a re-reference is **never** a fresh first appearance. Flooring **every** slot (not just the maximum) is what blocks a backdated *second* occurrence of `Z` from riding alongside a fresh one. Keying by **prefix** (not slot position) survives policy co-evolution, where a co-`Evl`'d `governance` / `operation` breaks positional slot correspondence. The floor counts only **validly-anchored** pins. A SEL `Evl` is privileged and seal-advancing, so no SEL `Rpr` ever archives it (an `Rpr`'s parent is at-or-above the seal), and its anchor is **tier-2** (on a seal-advancing `Rot`), **durable against `Rpr`** ([`../../../protocol-doctrine.md` §Tier-2 anchor durability](../../../protocol-doctrine.md#anchor-tier-elevation)). An `Evl`'s pin drops from the floor only when its **contributing KEL surfaces federation-irreconcilable** with the anchor's host **at-or-beyond the divergent serial** — the host branch becomes non-canonical and the `Evl`'s `policy_satisfied` flips false (cross-chain anchor satisfaction, [§Terminology](../../../protocol-doctrine.md#terminology)) — while the `Evl` event itself remains on the SEL chain. In the linear case every `Est`/`Evl` anchor is durable, so the floor is just the immutable `Est`/`Evl` sequence. Device / KEL evidence is **never** in the pin (it is `id` / `grp` only, above) and so is never floored — it is per-event and self-dating.

`Est` **self-supplies its resolution context**: the parent `Icp` carries no pin, so the only pin in existence at `Est` is the one the `Est` itself declares. A prefix's **first appearance** in the pin — at `Est`, or the first `Evl` to reference a prefix **never previously pinned on the surviving chain** — has no prior marker, so its first marker is free (**absent floor ⇒ unconstrained**): the only structural bound on that choice is the upper `IelDivergent` rule (a pinned IEL event must sit at-or-below that IEL's seal). "First appearance" means *never previously referenced*: a prefix that was pinned, dropped from a later pin, then **re-referenced** is **not** a first appearance — its floor is retained per prefix across the gap (the running max above), so the re-reference is still floored and cannot reset to old state. This first-appearance freedom is what the ex-member residual rides — a slot may reference arbitrarily old chain state on a **genuine** first appearance (see the ex-member note in [`../../../protocol-doctrine.md` §Anchor Tier Elevation](../../../protocol-doctrine.md#anchor-tier-elevation)); the forward floor then blocks any later regression on that chain, including a drop-and-reintroduce.

**State vs. evidence — the pin is shallow by design.** The `policyPin` fixes *which version of each directly-named IEL* an event resolves against — the **membership / state layer**: shallow, full, floored, `id` / `grp` only, no nulls. *Who actually signed* — the expansion into a referenced IEL (its members, their devices) and the per-event anchor — is the **deep per-event authorizing evidence**, resolved by token-pass (§`policyPin` consumes verified chain tokens, not a live source — see [`../policy/evaluation.md`](../policy/evaluation.md)) into that IEL plus the authorizing event's own evidence pinning, **as-of authoring** (grandfather). That deep path has two evidence forms: the **policy-text** walk (`id` markers, `dev` prior-event SAIDs, with a `null` for an un-evidenced occurrence) is **positional**; a **`grp` leaf** is a sparse **`GrpBlock`** naming only the members who signed (never one slot per member, and `null` slots live on the **policy-text** walk only). Its per-SEL-event shape is SEL-primitive (layer-4) detail, forward-pointed there, and the general evidence-pinning mechanism is [`../policy/pinning.md`](../policy/pinning.md). The pin names the snapshot; the evidence proves the signatures against it. **Deep flooring is the feature's concern:** each IEL state-marker the deep walk reaches is a marker **on that entity's own chain** (the coupling check), never an issuer's free choice; the **directly-named** entities are floored per-chain by the shallow `policyPin` (every entity floors its own marker shallow on its own registry-SEL, forward-only — the registry-SEL is **not** a plain log). The **cross-registry** cut-off — flooring the deeper markers a recursion reaches, i.e. whether an issuer is still a delegate as-of an issuance — is the **layer-5 credentials feature**, **not** the policy primitive's (it does not compose authority across a tree of registries). The one marker no rule floors is the terminal **`dev`** anchor (per-event, self-dating — a leaked *current* key is the recovery residual, not a backdating surface). Registry-SEL **provisioning** is the layer-4 obligation; **issuance** as a floored `Ixn` on it and the cross-registry cut-off are the **layer-5 credentials feature** — forward-pointed.

## Event taxonomy

### KEL — 8 kinds

| Kind | Class | Tier | Purpose |
|---|---|---|---|
| `Fcp` | inception | 1 | Founder pre-federation inception |
| `Icp` | inception | 1 | Standard inception, federation-bound |
| `Ixn` | content | 1 | Interaction; anchors generic SAIDs via a `manifest` |
| `Rot` | privileged | 2 | Rotation; reveals next signing key, commits new |
| `Ror` | privileged | 3 | Rotate-recovery; dual-signed; rotates signing and recovery keys |
| `Fed` | privileged | 3 | Federation-binding mutation; dual-signed |
| `Rpr` | archiving | 3 | Repair; resolves divergent chain by archiving discriminator-losing branch |
| `Dec` | terminal | 3 | Decommission; dual-signed |

### IEL — 6 kinds

| Kind | Class | Tier | KEL anchor | Purpose |
|---|---|---|---|---|
| `Fcp` | inception | 3 | founder `Fed` at v=1 | Federation IEL inception; self-attesting at v=0 via kind-dispatched verifier carve-out |
| `Icp` | inception | 2 | `Rot` per `governance` member | Standard IEL inception; optionally delegated (sets `delegating` to the delegator's prefix) |
| `Evl` | privileged | 2 | `Rot` per prior `governance` member | Evolve `governance` / `authentication` / `delegation` / `roster` / `delegating`; must change at least one |
| `Del` | privileged | 2 | `Rot` per `delegation` member | Add prefixes to cumulative delegated set |
| `Rsc` | privileged | 2 | `Rot` per `delegation` member | Remove prefixes from cumulative delegated set. Invalidates any graphs depending on the removed prefixes. To cleanly decommission a delegated IEL, use `Dec` on the delegate IEL |
| `Dec` | terminal | 3 | `Ror` per `governance` member | Terminal; ends IEL on clean linear landing |

Every IEL event routes as privileged in the divergence axis — no content kind; divergent sets cannot form locally on IEL.

### SEL — 6 kinds

| Kind | Class | Tier | KEL anchor | Purpose |
|---|---|---|---|---|
| `Icp` | inception | n/a (permissionless) | — | Permissionless, dedup-equivalent inception; declares `governance`, `operation`, and `topic` |
| `Est` | privileged | 2 | `Rot` per `operation` member | Establishes IEL binding at v=1; carries `policyPin` |
| `Ixn` | content | 1 | `Ixn` per `operation` member | Publishes a `document` SAD |
| `Evl` | privileged | 2 | `Rot` per prior `governance` member | Evolve `governance` / `operation` and/or re-ratchet `policyPin`, **each stated only on change**; a consecutive `Evl` must change ≥1, a post-`Ixn` `Evl` may carry nothing (seal checkpoint) |
| `Rpr` | archiving | 3 | `Ror` per `governance` member | Repair; resolves a divergent SEL by archiving discriminator-losing branch |
| `Dec` | terminal | 3 | `Ror` per `governance` member | Terminal; ends SEL on clean linear landing |

SEL `Icp` must be submitted in a batch with `Est` to:
1. Allow for deterministic lookup
2. Establish the SEL's `policyPin` at `Est` so the binding is pinned for endorsement.

## Per-kind structural validation

Verifier enforces per-kind field rules. Cells are:

- **req** — field MUST be set on this kind; verifier rejects if absent
- **fbd** — field MUST be unset on this kind; verifier rejects if present
- **opt** — field MAY be set or unset on this kind

Common fields (`said`, `prefix`, `kind`) are always required and not enumerated here. `previous`: forbidden on inception kinds (`Fcp`, `Icp`), required elsewhere. `serial`: 0 on inception, `>=1` elsewhere. Signatures live adjacent to events (not in content) — see [§Authentication & signatures](#authentication--signatures).

### KEL

| Kind | publicKey | rotationHash | recoveryKey | recoveryHash | federationBinding | manifest | witnessThreshold | witnessSelectionSize |
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

- `federationBinding` on KEL Icp/Fed is the federation IEL event SAID.
- `manifest` on KEL Ixn is required, with ≥ 1 anchor in its `anchors` array; on Rot/Ror it is optional — absent when nothing is anchored.
- `Fcp` is at v=0; `Icp` is at v=0; `Fed` is at v ≥ 1 (the founder pattern is `Fed` at v=1 on an `Fcp`-rooted chain).

### IEL

| Kind | nonce | authentication | governance | delegation | roster | delegating | delegated |
|---|---|---|---|---|---|---|---|
| `Fcp` | req | req | req | opt | req | fbd | fbd |
| `Icp` | req | req | req | opt | opt[note 1] | opt | fbd |
| `Evl` | fbd | opt[note 2] | opt[note 2] | opt[note 2] | opt[note 2] | opt[note 3] | fbd |
| `Del` | fbd | fbd | fbd | fbd | fbd | fbd | req |
| `Rsc` | fbd | fbd | fbd | fbd | fbd | fbd | req |
| `Dec` | fbd | fbd | fbd | fbd | fbd | fbd | fbd |

Notes:
1. **`Icp` `roster`** — optional at `Icp`: present ⇒ **aggregate**, absent ⇒ **singleton**. Roster-presence is the immutable kind signal — a later `Evl` may evolve an aggregate's roster but may neither add one to a singleton nor null an aggregate's.
2. **`Evl` `authentication` / `governance` / `delegation` / `roster` / `delegating`** — at least one MUST be set. A no-op `Evl` (none change) is rejected. `roster` may move only if the `Icp` declared one (i.e. on an aggregate IEL; a singleton declared none and can never gain one, so `roster` stays effectively `fbd` on its `Evl`s); the co-update is validated against post-application referential integrity (see [§IEL policy fields & membership shape](#iel-policy-fields--membership-shape)). Parallels KEL `Fed`'s "must change one of (federation binding, witness params)" rule.
3. **`Evl` `delegating`** — set only on a **serial-1 `Evl`** that completes a delegated inception (the back-pointer to the delegator's `Del`-event SAID); `fbd` on any later `Evl`. See [§Delegation handshake](#delegation-handshake).

The `nonce` is required at inception (drives prefix unpredictability per [§Prefix derivation](#prefix-derivation-is-whole-content)). `delegating` on `Icp` is the structural marker for delegated inception — when set, the delegate's `[Icp, Evl]` batch and the delegator's outbound `Del` (which MUST list this prefix, transitively gated by the delegator's `delegation` policy) complete the handshake.

Authentication is via the KEL anchor per §Authentication & signatures — tier-3 IEL events (`Fcp`, `Dec`) are anchored by a tier-3 KEL event (whose adjacent signatures provide authentication), not by an event-level recovery signature.

### SEL

| Kind | governance | operation | topic | policyPin | document |
|---|---|---|---|---|---|
| `Icp` | req | req | req | fbd | fbd |
| `Est` | fbd | fbd | fbd | req | fbd |
| `Ixn` | fbd | fbd | fbd | fbd | req |
| `Evl` | opt[note 1] | opt[note 1] | fbd | opt[note 1] | fbd |
| `Rpr` | fbd | fbd | fbd | fbd | fbd |
| `Dec` | fbd | fbd | fbd | fbd | fbd |

Notes:
1. **`Evl` `governance` / `operation` / `policyPin`** — each is **stated only on change**, and a **consecutive** `Evl` (directly following an `Est` / `Evl`, no `Ixn` between) **must change at least one** of the three; a no-op consecutive `Evl` is rejected. `policyPin` is **optional**: state it **iff** the binding changes — a `governance` / `operation` edit that alters the `id` / `grp` **occurrence set** (the re-stated pin must accompany it, full and aligned to the new policy text), or **≥1 marker ratcheted forward**. A gov/op change that leaves the occurrence set unchanged (e.g. a threshold-only edit) may omit it; an `Evl` that follows **≥1 `Ixn`** is a **seal checkpoint** that may **carry nothing** (no `governance`, `operation`, or `policyPin`) and just advances the seal to hold the chain under the seal-advance cap (bounding the repair operator). When a pin **is** stated it ratchets forward along the **per-chain forward-only floor** (every slot referencing chain `Z` at-or-above the running `chain_floor[Z]`; see [`../../../protocol-doctrine.md` §Per-Chain Forward-Only Floor](../../../protocol-doctrine.md#per-chain-forward-only-floor-sel-specific)); the floor is derived from **stated** pins, so an `Evl` that omits the pin doesn't advance it. **Verifier coupling check:** the **current** pin (stated this `Evl`, else inherited) must **pair** to the **current** `governance` / `operation` (stated this `Evl`, else inherited) — one slot per `id` / `grp` occurrence, pre-order, no nulls, **each slot's marker an event on the chain its paired occurrence names** — so a gov/op change that altered the occurrence set without a re-stated pin **fails to pair and is rejected**. (This also catches a *count-preserving* swap — `id(B)`→`id(C)` at the same position: the inherited slot's marker is a `B`-chain event, which is not a `C`-chain event, so it fails to resolve at that occurrence.) The collapse into one kind still holds: an `Evl` may do `governance` / `operation` evolution **and/or** a pin re-ratchet **and/or** a pure seal advance. Parallel to KEL `Fed`'s "must change at least one of (federation binding, witness params)" rule.

- `governance` on `Icp` declares the SEL's lifecycle-gating policy (SAID of a Policy SAD); `operation` declares its operational-write policy. The policies determine the pinning's slots: the common case is the single-identity pair `governance = id(iel_prefix)`, `operation = id(iel_prefix)` — degenerate but explicit — a one-slot pinning per policy; policies with more prefix occurrences yield more slots.
- `policyPin` on `Est` declares the SEL's first policy pin — the SAID of the pin SAD carrying the SEL's positional pinning(s) over `governance` / `operation` — at v=1.
- `Ixn` / `Rpr` / `Dec` don't carry their own `policyPin`, and an `Evl` that doesn't change the binding omits it — all inherit the SEL's tracked `policyPin`, the most-recent prior **stated** pin (the `Est` pin, or the last `Evl` that re-stated it).
- `topic` on `Icp` is an application-level discriminator; the chain's prefix derives from the whole-Icp content — `governance`, `operation`, and `topic` — so two Icps with the same `(governance, operation, topic)` produce the same SAID and prefix (Icp dedup-equivalence). `operation` must participate: were it excluded, two Icps differing only in `operation` would share a prefix but carry different SAIDs, and the merge layer's Icp dedup (which keys on the SAID) would break.

Authentication is via the KEL anchor per §Authentication & signatures — tier-3 SEL events (`Rpr`, `Dec`) are anchored by a tier-3 KEL event (whose adjacent signatures provide authentication), not by an event-level recovery signature.

## Batching requirements

Some event kinds can only land at merge time as part of a multi-event atomic batch. Per-event structural validation (§Per-kind structural validation) doesn't capture these — they are merge-layer constraints enforced when events arrive together.

**Structurally-required batches:**

- **IEL delegated inception `[Icp, Evl]`** — a `delegating`-`Icp` (whose `delegating` holds the delegator's prefix) **must** batch with the serial-1 `Evl` that evolves `delegating` to the delegator's `Del`-event SAID; the two land together or not at all, and `delegating`-as-SAID appears **only** on that serial-1 `Evl`. Neither event is valid alone. See [§Delegation handshake](#delegation-handshake). (Non-delegated `Icp` is bare — no required batch.)
- **SEL `[Icp, Est, ...]`** — SEL `Icp` is permissionless and dedup-equivalent (any party's Icp for the same `(governance, operation, topic)` produces the same SAID). The merge layer **rejects bare `[Icp]`** — an Est at v=1 must accompany the Icp (or be in a longer batch containing both). The Est is what raises the per-attempt cost to tier-2 anchor; without it, the camping-defense argument doesn't hold.
- **Federation bootstrap (multi-chain atomic batch)** — interleaves: founder KEL `[Fcp, Fed]` pairs (one per founder KEL), the federation IEL `Fcp` (on the federation IEL chain), and cross-attestation receipts. The federation IEL `Fcp` self-attests via the kind-dispatched verifier carve-out at v=0; founder Fed events at v=1 anchor it from the KEL side. All events land together as a single transaction. See [`../../../federation/bootstrap.md`](../../../federation/bootstrap.md) (subsequent sub-issue) for the full ceremony.

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
| Self-mutation / config evolution | — | `Evl` | `Evl` |
| Federation re-binding | `Fed` | — | — |
| Cross-chain binding establishment | `Icp` / `Fed` | `Icp` (federation context inherited via parent KEL) | `Est` |
| Cross-chain binding re-ratchet | (re-`Fed`) | — | `Evl` (re-ratchets `policyPin` when a marker advances; may also change `governance` / `operation`) |
| Delegation declaration / rescission | — | `Del` / `Rsc` | — |
| Archival (divergence resolution) | `Rpr` | — | `Rpr` |
| Terminal | `Dec` | `Dec` | `Dec` |

Governance evolution, authentication / delegation / roster evolution (IEL), and operation evolution (SEL) all ride the one self-mutation kind `Evl` on each log — they are not separate kinds.

## Prefix derivation is whole-content

Prefix derives from the entire event body (with both `said` and `prefix` blanked). It's not a special tuple. Whatever fields are populated on the inception event participate in the prefix. The verifier reconstructs the prefix from canonical-form serialization and rejects any event whose computed prefix doesn't match its declared prefix.

For chains where prefix unpredictability is required as a structural property (IEL), the inception event includes a `nonce` field whose content is opaque random bytes — this makes the prefix unpredictable to outside observers. The IEL prefix therefore commits to the whole inception content — the `authentication` / `governance` / `delegation` policy SAIDs, the `roster` (aggregate IELs), the delegator's prefix in `delegating` (delegated IELs), and the `nonce` — not a fixed tuple. For chains where prefix is intentionally derivable by external parties (SEL — to support identity-rooted discovery), the inception event omits `nonce` and the prefix derives deterministically from declared content (`governance` + `operation` + `topic` for SEL).

## Tier dispatch

Tier is determined by event kind, not by policy. Tier names the cryptographic capability required to forge the event — see [`kel/events.md` §Three-tier capability model](kel/events.md#three-tier-capability-model). Tier and policy are orthogonal axes:

- **Policy** = who (the member set authorized for this action — defined in IEL `governance` / `authentication` / `delegation`, SEL `governance` / `operation`, or KEL-intrinsic dual-signing rules)
- **Tier** = at what auth level (the required KEL anchor capability or dual-signature shape)

The verifier composes both — at every authorization site, it checks the event member is named by the relevant policy AND that they authored at the required tier. The same policy member set may authorize different actions at different tiers (e.g., SEL `operation` members authorize tier-1 `Ixn` AND tier-2 `Est` under the same member set; SEL event kind dispatches the tier requirement).

See [`../../../protocol-doctrine.md` §Anchor Tier Elevation](../../../protocol-doctrine.md#anchor-tier-elevation) for the cross-primitive anchor-tier rules.

## Policy DSL reconciliations

The policy DSL ([`../policy/`](../policy/)) reads several of these fields under its own names; the mappings are concrete (no separate stored field):

- **`s.anchors` == `manifest.anchors`.** The DSL's `satisfies_dev` reads the anchoring event's set of anchored SAIDs as `s.anchors`; that is exactly the `anchors: Vec<Digest256>` array of the manifest SAD referenced by the KEL event's `manifest` field (KEL `Ixn` / `Rot` / `Ror` only — a SEL `document` is not an anchor source).
- **`s.tier` == `tier_of(s.kind)`.** Tier is not stored — it is dispatched from the event kind (§Tier dispatch: `Ixn` → 1, `Rot` → 2, `Ror` → 3). The DSL's `s.tier` is read through that dispatch.
- **Per-anchor tier == anchor tier elevation.** A required anchor demanding tier ≥ N means the anchored SAID must appear in the `manifest.anchors` of a KEL event whose kind dispatches to ≥ N (a high-assurance SAD co-anchored in a `Rot` / `Ror` rather than an `Ixn`). This is a constraint on *which KEL kind hosts the anchor* — no new field. See [`../../../protocol-doctrine.md` §Anchor Tier Elevation](../../../protocol-doctrine.md#anchor-tier-elevation).
- **Surviving-branch anchoring child.** The DSL resolves the unique child `S` where `S.previous == prior_said` **on the surviving (non-divergent / post-repair) branch**; an anchor sitting on a discriminator-losing / archived branch correctly fails to resolve. How a `Rpr`-archived branch interacts with anchor validity (the valid-for-binding cutoff) is KEL-primitive doctrine — see [`kel/`](kel/).

## Authorization gating per kind

Brief mapping of which policy gates each event kind. For all non-inception events, gating evaluates against the chain's tracked policy at the parent event — for evolution events that's the policy before this event changes it; for non-evolution events the policy is simply unchanged from the parent's state. (KEL fields like `rotationHash` / `recoveryHash` work the same way — the commitment is on the prior establishment event.) On SEL the same parent-state rule covers the pin as resolution state: `Evl` / `Rpr` / `Dec` evaluate their gating policy in anchored mode against the **parent's tracked `policyPin`**; `Est` is the exception — the parent `Icp` carries no pin, so `Est` resolves against the pin it itself declares (see [§`policyPin`](#policypin)).

| Event kind | Gating policy | Notes |
|---|---|---|
| KEL `Fcp` / `Icp` | self (signing key declared in event) | Self-authenticating via prefix derivation |
| KEL `Ixn` | signing key | Tier-1 |
| KEL `Rot` | rotation-key preimage of `rotationHash` | Tier-2 |
| KEL `Ror` / `Fed` / `Rpr` / `Dec` | rotation + recovery preimages of `rotationHash` and `recoveryHash` | Tier-3 dual-signed |
| IEL `Fcp` | self-attesting at v=0 via kind-dispatched carve-out (pool = the `Fcp`'s `governance` policy's DSL expansion to leaf prefixes) | Anchored from KEL side by founder `Fed` at v=1 |
| IEL `Icp` | self-authorized against declared `governance` | Optionally delegated (`delegating` = delegator's prefix; the delegator's outbound `Del` must list this prefix) |
| IEL `Evl` / `Dec` | `governance` | `Dec` is tier-3. `authentication` never gates the IEL's own events |
| IEL `Del` / `Rsc` | `delegation` | Forbidden if `delegation` is unset on IEL state |
| SEL `Icp` | permissionless (no policy gate) | Dedup-equivalent via prefix derivation |
| SEL `Est` / `Ixn` | `operation` (resolved at the `policyPin` — `Est` at its own declared pin; `Ixn` at the tracked pin) | Tier dispatched by kind (Ixn tier-1; Est tier-2) |
| SEL `Evl` | `governance` (resolved at the parent's tracked `policyPin`) | Tier-2 |
| SEL `Rpr` / `Dec` | `governance` | Tier-3 dual-signed |

## Naming conventions

- **Three-letter codes.** All event kinds use three-letter abbreviations (Fcp / Icp / Ixn / Rot / Ror / Fed / Rpr / Dec / Evl / Del / Rsc / Est). Consistent across log types.
- **Inception kinds** all named `Icp` (or `Fcp` for federation-context inceptions). Log type disambiguates structural differences.
- **Class names** — `inception`, `content`, `privileged`, `archiving`, `terminal`. The class column on per-log taxonomy tables names the event's chain-state effect. This lifecycle axis is distinct from the merge layer's three-name divergence-axis class (content / privileged / archiving, classifying divergent-set behavior — see [`../../../protocol-doctrine.md` §Event-class taxonomy](../../../protocol-doctrine.md#event-class-taxonomy)): lifecycle `terminal` kinds route as `privileged` there, and lifecycle `inception` kinds sit outside the divergence classification.
- **Common names across log types** — events with the same structural role share names: `Ixn` for content extension (KEL + SEL); `Evl` for self-mutation / config evolution (IEL + SEL); `Rpr` for archival (KEL + SEL); `Dec` for terminal (all three).
- **Delegated inception folds into `Icp`.** There is no distinct delegated-inception kind: a delegated IEL is an `Icp` with `delegating` set to the delegator's prefix, completed by a batched serial-1 `Evl` that records the authorizing `Del` SAID (§Delegation handshake). The verifier dispatches the delegated-vs-non-delegated case from whether `delegating` is populated, not from a distinct kind.

## Open items

The pin-SAD serialization and the multi-slot ratchet are **settled** (see [§`policyPin`](#policypin)): serialization is the shallow full positional marker array — one entry per `id` / `grp` occurrence in the policy text, pre-order walk order, no nulls — and the multi-slot ratchet is the per-chain forward-only floor (every slot at-or-above its referenced IEL chain's running floor, surviving-chain-derived; cross-referenced in [`../../../protocol-doctrine.md` §Per-Chain Forward-Only Floor](../../../protocol-doctrine.md#per-chain-forward-only-floor-sel-specific)). The remaining open items:

1. **IEL `Dec` policy gating.** IEL `Dec` is gated by `governance` at tier 3. Whether `delegation` plays any role at terminal time (e.g., the cumulative delegated set survives or is invalidated post-Dec) is a SEL/credential-doctrine concern, not an event-shape concern.

2. **SEL `Icp` discoverability — convention vs. enforced derivation.** Camping defense relies on `Icp` dedup-equivalence — parties producing the same `(governance, operation, topic)` produce the same `Icp`. Identity-rooted discovery is realized by deriving both degenerate policies deterministically from a referenced IEL prefix and `topic`; whether that derivation stays an application convention or becomes an enforced operator policy is a SEL-primitive question — deferred to [`sel/`](sel/) doctrine.
