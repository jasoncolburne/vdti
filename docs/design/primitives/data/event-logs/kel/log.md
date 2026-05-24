# KEL — Key Event Log

The **Key Event Log** (KEL) is a per-prefix chain of cryptographically-linked signed key events describing a controller's evolving signing and recovery key state. Each event is a [SAD](../../sad/sad.md) carrying chain-linkage fields (`prefix`, `previous`, `serial`) plus kind-specific commitments; authority is asserted by direct signature against keys committed by prior establishment events.

KEL is the foundation primitive in VDTI's chain-of-trust composition. IEL events and SEL events anchor in KEL events — the [anchor-tier-elevation rule](../../../../protocol-doctrine.md#anchor-tier-elevation) ties the cryptographic difficulty of forging a privileged IEL / SEL act to the cryptographic difficulty of forging the corresponding KEL anchor.

This doc states the chain primitive: prefix derivation, the three-state per-node machine, the two seal-tracking concepts, the locked-portion bound, and the page / chunking model. Per-kind reference lives in [`events.md`](events.md); merge-layer routing in [`merge.md`](merge.md); recovery doctrine in [`recovery.md`](recovery.md); verifier walk in [`verification.md`](verification.md); the cross-node correctness proof in [`reconciliation.md`](reconciliation.md).

## Prefix derivation

A KEL inception event is a [prefix-deriving SAD](../../sad/said.md#chain-inception-events-prefix-deriving-sads): the prefix and SAID are derived via two separate Blake3-256 hashes over the canonical bytes. The prefix commits to the **whole inception SAD content** with both `said` and `prefix` blanked to the fixed-value placeholder; the SAID then commits to the same SAD with `prefix` populated and only `said` blanked.

Whole-content prefix commitment means an inception event's `publicKey`, `rotationHash`, `recoveryHash`, kind discriminator, and (for `Dip`) `delegatingPrefix` are all bound into the prefix. Two distinct inception events cannot share a prefix without producing a Blake3-256 collision. Subsequent events inherit the inception's `prefix` and derive only `said`.

KEL inception is dispatched by **kind** at v=0 — see [`events.md` §Three-kind inception](events.md#three-kind-inception). The kind determines whether the chain is pre-federation (`Fcp`), federation-bound from inception (`Icp`), or delegated under another KEL (`Dip`). The verifier dispatches structural behavior on the kind; consumer trust composes through the [trusted federation `Fcp` SAID set](../../../../protocol-doctrine.md#federation-witnessing-in-verification).

## Three-state per-node machine

A KEL is in exactly one of three states on any given node. State is computed from the chain's events — never tracked as a separate flag.

| State | Description | Accepts new events? |
|---|---|---|
| **Active** | Linear chain; the current tip extends cleanly via `previous`. | Yes — `Ixn`, `Rot`, `Ror`, `Rec`, `Fed`, `Dec` per their respective authorization and seal-cap requirements. |
| **Divergent** | Two non-privileged events (`Ixn`-`Ixn`) at the same serial sharing a common `previous`. Privileged events that would create or join a divergent set are rejected at the merge layer per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal). | `Rec` only (archives one branch; chain returns to Active). |
| **Decommissioned** | Linear chain terminated by `Dec`. The `Dec` event sits at the chain's tip; the seal sits at the `Dec`'s serial. | None. All submissions rejected by the seal-cap. |

State names are precise and not interchangeable. "Divergent" describes a chain shape (two events at the same serial); "federation-irreconcilable" — surfaced at the federation layer via divergent witness receipts (see [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md)) — is a federation-layer property, not a per-node chain state.

### Federation-irreconcilable is distinct from Divergent

A prefix becomes **federation-irreconcilable** when threshold-many witness receipts at the same chain position witness two or more distinct `witnessedSaid` values, each of which the verifier re-checks as structurally valid. The mechanics live in [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md); the relevant point at the KEL primitive layer is that this state lives at the federation layer rather than in the chain's local event sequence. Per-node, the chain remains Active / Divergent / Decommissioned; the federation-irreconcilable signal rides through divergent witness receipts and surfaces in the [synthetic effective-SAID](../../../../protocol-doctrine.md#effective-said-synthetic-comparison).

## Seal-tracking and the locked-portion bound

The KEL verifier surfaces two distinct seal concepts on its [`KelVerification`](verification.md#kelverification-token) token. Both are forward-only watermarks computed from the chain's events.

| Concept | Advances on | Used for |
|---|---|---|
| `lastSealAdvancingEvent` | `Rec` / `Ror` / `Rot` / `Fed` | Seal-cap rule: every new event's parent must sit at-or-after this serial. The locked portion is everything at-or-below it. |
| `lastRecoveryRevealingEvent` | `Rec` / `Ror` / `Fed` / `Dec` | Spent-key rule: tracks which recovery-key preimage is currently committed. Once any recovery-revealing event lands, the recovery key it reveals is publicly known. |

The membership sets diverge. `Rot` advances the seal without revealing the recovery key; `Dec` reveals the recovery key without advancing the seal (it enforces the seal but is terminal). The orthogonality lets the protocol bound chain-state changes (via the seal-advance cap, below) while leaving recovery-preimage rotation cadence to operator guidance — recovery keys are typically hardware-held and preimage-identified rather than usage-degraded, so protocol-forced cadence would impose cold-storage access on a fixed schedule the operator's threat model is designed to avoid.

### The locked portion

The **locked portion** of a KEL is the segment at-or-below `lastSealAdvancingEvent`. Events in this segment are structurally immutable within the chain:

- `Rec` cannot target the locked portion. The repair-event bound (condition 2b in [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal)) requires `Rec.previous.serial ≥ seal_serial`.
- New events submitted with `previous` pointing into the locked portion are rejected at the merge layer with `ParentLocked`.
- The seal-cap's role is to deny revival attacks: a party holding stale authority (a recovery preimage already revealed by an earlier `Rec` / `Ror` / `Fed`, or a key that has since been rotated out) cannot construct an event targeting the locked portion to rearrange the chain. Only current authority gates further extension.

### Pre-seal verifiability

The at-or-below-seal portion is permanently final — for the chain itself (no future event may target it) and for consumers verifying anchors, credentials, and SEL bindings against it. See [`recovery.md` §Pre-seal verifiability](recovery.md#pre-seal-verifiability) for the structural defense argument and [§Pre-seal verifiability](../../../../protocol-doctrine.md#pre-seal-verifiability) for the cross-primitive framing.

### Once-revealed-final invariant

Once a recovery-revealing event lands, the dual signature it proves is final. Subsequent compromise or revocation of the keys it revealed does not retroactively unsatisfy the past authorization — the chain's history at that serial is locked. Without this, history could be invalidated retroactively by anyone who later comes to control the revealed key material, making terminal states (recovered, decommissioned) unstable. The trade-off: a key controller who later turns adversarial cannot undo their past contributions; only the going-forward spent-key effect applies.

## Seal-advance cap

A seal-advancing event (`Rec` / `Ror` / `Rot` / `Fed`) must land at least every `MINIMUM_PAGE_SIZE − 2 = 62` non-seal-advancing events. The cap bounds the **chain-state-advance window**: divergence on a chain since the last seal-advancing event is capped at 62 events on either branch, so the discriminator's archival window fits in one page.

`MINIMUM_PAGE_SIZE` is a protocol constant — a deployment floor, not a per-deployment knob — so a recovery batch produced on any conformant deployment fits in one page on every other. The `− 2` headroom accommodates an atomic 2-event lifecycle batch: `[Rec, Rot]` (recovery followed by the conditional rotation when the archived branch had rotated past the surviving one) is the KEL worst-case shape and fits in one page on every conformant deployment.

Recovery-preimage rotation cadence (how often `Ror` should land to refresh the commitment) is **operator guidance**, not a protocol-enforced cap — see [`events.md` §Seal-advance cap](events.md#seal-advance-cap).

The seal-advance cap composes with the privileged-divergence-terminal rule to give the [bounded-divergence invariant](reconciliation.md#invariants): an adversary holding less than the rotation-key preimage can only submit `Ixn` events, and the cap limits them to at most 62 events before they must produce a seal-advancing event (which requires at least tier-2 capability — see [`recovery.md` §Three-tier compromise model](recovery.md#three-tier-compromise-model)).

## Page model

Chains are read, verified, written, and replicated in **pages** of bounded size. The page is the unit of memory budget for the verifier walk, the unit of round-trip for storage reads, and the unit of atomicity for the merge handler's discriminator.

- **`MINIMUM_PAGE_SIZE`** — protocol constant; the floor every conformant deployment must support. The seal-advance cap is derived from this constant so a recovery batch produced anywhere validates anywhere.
- **Page boundaries align with generations.** A generation is the set of events at the same serial. The verifier processes events in generation order (`serial ASC, kind sort_priority ASC, said ASC`) and re-fetches an incomplete generation at the next page boundary; a divergent generation that spans two pages re-fetches on the next page rather than being processed half-observed.
- **Deterministic intra-generation ordering.** Per-kind `sort_priority` (see [`events.md` §Per-kind sort priority](events.md#per-kind-sort-priority)) breaks intra-generation order so all nodes process the same batch identically. The `said` tiebreaker is for determinism only and has no semantic meaning.

The page model lets every operation be bounded-resource. The discriminator's archival window fits in one page (per the seal-advance cap derivation above). The verifier's `max_pages` cap (default 64 pages = ~2K events; configurable via env var) caps resource use even on adversarial chains.

## Chain-lifecycle paths (per-node)

The structural rules above produce three lifecycle paths per node.

- **Active extension.** Each new event extends the linear chain via `previous = tip.said`. Seal-advancing kinds (`Rec` / `Ror` / `Rot` / `Fed`) advance `lastSealAdvancingEvent` to their own serial; non-seal-advancing kinds (`Ixn`) leave the seal where it was.
- **Divergence and recovery.** Two `Ixn` events at the same serial form a divergent set; `Rec` archives the discriminator-losing branch and returns the chain to Active. The archival window is bounded by the seal-advance cap and fits in one page. See [`recovery.md` §Rec parent shapes](recovery.md#rec-parent-shapes) for the two ways a `Rec` can attach.
- **Clean retirement.** `Dec` lands as a linear extension of the current tip; the chain becomes Decommissioned. The seal does not advance (`Dec` is terminal), and the seal-cap rejects every subsequent submission. Past content keeps its meaning under the locked-portion bound.

Cross-node priv-vs-priv races — two federation nodes accepting different privileged events at the same serial via independent linear-chain extensions — are not a per-node state. Each node's seal-cap rejects the gossip-arriving competing event; the federation surfaces the disagreement via divergent witness receipts at the federation layer. See [`recovery.md` §Cross-node priv-vs-priv races](recovery.md#cross-node-priv-vs-priv-races), [§Limit of the doctrine — concurrent privileged event races](../../../../protocol-doctrine.md#concurrent-privileged-event-races), and [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md).

## End-verifiability

KEL's contribution to end-verifiability over data-from-any-source is two structural properties: whole-content prefix derivation makes the inception event tamper-evident (substituting content would require a Blake3-256 collision against both `prefix` and `said`), and locked-portion immutability under the seal-cap means events at-or-below `lastSealAdvancingEvent` cannot be rearranged by any future event — so anchors, credentials, and SEL bindings resolving to the locked portion stay structurally trustworthy indefinitely. The cross-primitive framing (verify the data, not the source) is canonical in [`../../../../system-thesis.md` §End-verifiability](../../../../system-thesis.md#end-verifiability); the recovery-side composition with the three-tier compromise model is in [`recovery.md` §Pre-seal verifiability](recovery.md#pre-seal-verifiability).

## Cross-references

- [`events.md`](events.md) — per-kind reference: three-kind inception, privileged and non-privileged kinds, three-tier capability model, anchor requirements, seal-advance cap.
- [`merge.md`](merge.md) — merge handler routing: routing order, outcomes, locked-portion enforcement.
- [`recovery.md`](recovery.md) — recovery doctrine: three-tier compromise model, dual-signature defense, pre-seal verifiability.
- [`verification.md`](verification.md) — verifier walk algorithm, kind dispatch at inception, signature verification, anchor checking.
- [`reconciliation.md`](reconciliation.md) — exhaustive case-matrix proof of cross-node convergence.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md) — anchor tier elevation, privileged-divergence-is-terminal, forks-are-seal-bounded, pre-seal verifiability, operation categories, federation convergence, routing order.
- [`../../sad/sad.md`](../../sad/sad.md), [`../../sad/said.md`](../../sad/said.md) — the SAD shape KEL events compose on; prefix and SAID derivation algorithms.
- [`../iel/`](../iel/) — IEL primitive (subsequent sub-issue). KEL events host the anchors that authorize tier-2 and tier-3 IEL acts per anchor-tier-elevation.
- [`../sel/`](../sel/) — SEL primitive (subsequent sub-issue). KEL events host the anchors that authorize tier-1, tier-2, and tier-3 SEL acts.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation witnessing doctrine (subsequent sub-issue): always-witness, threshold-two-events, divergent witness receipts, acceptance gating, federation-irreconcilable surfacing.
- [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) — federation bootstrap (subsequent sub-issue): the atomic ceremony that brings Fcp / Fed and the federation IEL Fcp into existence together.
