# Protocol Doctrine

The structural rules that govern VDTI — security invariants, cross-cutting doctrines, and verification mechanics. Each part below is load-bearing for protocol correctness; per-primitive design docs cross-reference these as the upstream source rather than re-deriving them.

Read [`system-thesis.md`](system-thesis.md) first. The thesis is the framing — adversarial-first posture, end-verifiability over data-from-any-source, fail-secure default — and points back here for the structural rules that realize those properties.

**[Part 1 — Security Invariants](#part-1-security-invariants):**
- [Terminology](#terminology) — locked portion, per-node chain states, cross-chain anchor satisfaction.
- [Operation categories](#operation-categories) — serving, consuming, resolving.
- [Compromise is Permanent](#compromise-is-permanent) — authority belongs to current state only, and the structural mechanisms that enforce it:
  - [Forks are Seal-Bounded](#forks-are-seal-bounded)
  - [Routing order](#routing-order)
  - [Per-Chain Forward-Only Floor (SEL-specific)](#per-chain-forward-only-floor-sel-specific)
  - [Privileged Divergence is Terminal](#privileged-divergence-is-terminal)
  - [Event-class taxonomy](#event-class-taxonomy)
  - [One Divergent Generation at a Time](#one-divergent-generation-at-a-time)
  - [Anchor Tier Elevation](#anchor-tier-elevation)
  - [KEL Inception](#kel-inception)
  - [Evl-after-Ixn ratchet (application pattern)](#evl-after-ixn-ratchet-application-pattern)
  - [Decommission and clean retirement](#decommission-and-clean-retirement)
  - [Limit of the doctrine — current-state compromise](#limit-of-the-doctrine)
    - [Defense in Depth](#defense-in-depth)
    - [Adversary Patience and Policy Redundancy](#adversary-patience-and-policy-redundancy)
    - [Cascade-reincept honesty](#cascade-reincept-honesty)

**[Part 2 — Cross-Cutting Doctrines](#part-2-cross-cutting-doctrines):**
- [Ordering Without Timestamps](#ordering-without-timestamps)
- [Federation Convergence](#federation-convergence)
- [Extension Discipline](#extension-discipline)

**[Part 3 — Verification Mechanics](#part-3-verification-mechanics):**
- [Verification tokens as proof of verification](#verification-tokens-as-proof-of-verification)
- [Streaming](#streaming)
- [Merge Verification](#merge-verification)
- [Inline reference checking](#inline-reference-checking)
- [Verifier and merge are distinct treatments](#verifier-and-merge-are-distinct-treatments)
- [policy_satisfied](#policy_satisfied)
- [Federation witnessing in verification](#federation-witnessing-in-verification)
- [Advisory Locking](#advisory-locking)
- [Effective-SAID synthetic comparison](#effective-said-synthetic-comparison)

---

## Part 1: Security Invariants

The invariants below are load-bearing for VDTI security. They are stated structurally rather than statistically: the protocol's safety claims hold *by construction*, not by observation. Verifier implementations enforce them on every walk; an event or chain state that violates them is rejected, regardless of source.

### Terminology

Structural concepts referenced throughout the doctrine. Distinct senses; not interchangeable.

- **Locked**: the portion of a chain before its most recent privileged event. **Within-chain rule.** Locked events are structurally immutable within their own chain — `Rpr` on this chain cannot target them, and within-chain historical authorizations are not retroactively unsatisfiable. The privileged event ratchets the lock forward.
- **Chain states**: a chain is in exactly one of three states per-node. State names are used precisely throughout the doctrine.
  - **Active** — linear chain; accepts linear extension.
  - **Divergent** — multiple branches at the same serial. Divergent sets contain only non-privileged events (Ixn-Ixn on KEL or SEL) — privileged events that would create or join a divergent set are rejected at the merge layer (see [§Privileged Divergence is Terminal](#privileged-divergence-is-terminal)). Recoverable via `Rpr` — returns to Active. IEL has no Divergent state: every IEL event is privileged, so divergent sets cannot form locally on IEL.
  - **Decommissioned** — linear `Dec` has landed. Fully terminal: accepts no submissions of any kind.
- **Federation-irreconcilable**: cross-node disagreement on which privileged event a chain accepted at a given serial — surfaced at the federation layer via **divergent witness receipts**, the federation-attested adjacent-table evidence that the federation cannot agree at that chain position. See [`federation/witnessing.md`](federation/witnessing.md). Federation-irreconcilable is a federation-layer property, not a per-node chain state; the per-node states remain Active / Divergent / Decommissioned. A prefix becomes federation-irreconcilable at-and-beyond its divergent serial; events strictly below the divergent serial remain canonical.
- **Cross-chain anchor satisfaction**: an IEL / SEL event's policy satisfaction at consumer-query time is structurally checked against contributing KEL anchors. How a contributing anchor becomes non-canonical depends on its **tier**: a **tier-1 (`Ixn`)** anchor (above-seal, archivable) drops when a later `Rpr` archives its host; a **tier-2/3** anchor (on a seal-advancing `Rot` / `Ror` / `Fed`, **durable against `Rpr`** — see [§Tier-2 anchor durability](#anchor-tier-elevation)) drops when its host KEL surfaces **federation-irreconcilable** with that host **at-or-beyond the divergent serial** (an anchor strictly below the divergent serial stays canonical — §Terminology). Either way the KEL verifier reports the SAID as not-anchored on the canonical branch; the IEL / SEL's `policy_satisfied` flips false. **Distinct from within-chain state** — locked IEL / SEL events remain structurally locked within their own chains; cross-chain anchor satisfaction is a structural verification concern handled by composition redundancy (anchor count above exact threshold). See [§Anchor Tier Elevation §Threshold Composition](#threshold-composition).

### Operation Categories

The database cannot be trusted — it may have been altered. All operations on chain data (KEL, IEL, SEL) fall into three categories:

#### 1. Serving

Returning data to a client or peer. **No verification needed** — the receiver is responsible for verifying what they get.

Examples: `GET` endpoints serving event pages (per-primitive: `kel/:prefix`, `iel/:prefix`, `sel/:prefix`), effective-SAID lookups, paginated event reads.

#### 2. Consuming

Using data for security decisions (anchoring, key extraction, divergence routing, merge decisions). **MUST verify the full chain first.** The only way to access consumed data is through the corresponding verification token (`KelVerification`, `IelVerification`, `SelVerification`), which can only be obtained via that primitive's verifier (`KelVerifier`, `IelVerifier`, `SelVerifier`). This eliminates TOCTOU vulnerabilities — verification and data access happen in the same pass.

Examples: peer signature verification on a KEL, anchor checking on a KEL, governance-policy resolution on an IEL at a given serial, SEL `policyPin` resolution, submit-handler routing decisions on any primitive.

#### 3. Resolving

Comparing state to decide whether to sync. A wrong answer triggers an unnecessary sync (which itself verifies), not a security hole. Standalone functions are acceptable here without full verification.

Examples: effective-SAID endpoints (per-primitive), anti-entropy comparison, KEL proactive-rotation prechecks.

### Compromise is Permanent

The protocol grants authority **only to the chain's current state** (and the chain's most-recent shared pre-divergence state, where divergence has occurred). Past keys, past policies, past endorsers — anything that was once authorized but has since been rotated, revoked, or evolved out — has zero structural ability to act on the chain. Per primitive:

- **KEL:** a key compromised in the past cannot `Dec` the chain today — or extend it at all — even if the adversary still holds the key material.
- **IEL:** a `governance` participant revoked via `Evl` cannot land further governance acts on the chain after their revocation.
- **SEL:** an SEL bound to a stale IEL event whose governance has since rotated cannot be `Dec`'d by the rotated-out parties — subject to operator-side ratcheting via `Evl` to advance the SEL's tracked `policyPin` to the post-rotation IEL state.

This closes the **stale-state kill-switch problem**. Without this rule, every party who ever held authority over a chain would retain protocol-level kill-switch authority over it forever, and any past compromise would become a permanent vulnerability. With this rule, past compromise is structurally a non-event for authority over **existing** chains. SEL **establishment** is the residual exception — an `Est` self-supplies its pin and may reference old IEL state; see the ex-member note in [§Anchor Tier Elevation](#anchor-tier-elevation).

#### Forks are Seal-Bounded

The structural mechanism that enforces "current-state-only authority" is the chain's evaluation / recovery seal:

Each primitive tracks `lastSealAdvancingEvent` — the SAID of the chain's most recent advancing event (a per-primitive window-opening kind listed below, or the terminal `Dec`) that landed cleanly on the linear chain. The seal never forks: privileged events that would create or join a divergent set are rejected at the merge layer (see [§Privileged Divergence is Terminal](#privileged-divergence-is-terminal)), so seal-advancing landings are linear-chain extensions by construction. Archiving events (`Rpr`) route through the discriminator and resolve divergence rather than create or join it, advancing the seal when they land. The **window-opening** advancing kinds differ (the terminal `Dec` is additionally seal-advancing on every primitive — it opens no window; see below):

- **KEL**: `Rpr` / `Ror` / `Rot` / `Fed`.
- **IEL**: `Evl` / `Del` / `Rsc`.
- **SEL**: `Est` / `Evl` / `Rpr`.

Seal-advance machinery is meaningful only after the first non-inception event lands, since the seal-cap rule it gates (`parent_serial >= seal_serial`) is structurally vacuous against an inception event (which has no parent).

The terminal kind (`Dec` everywhere) advances the seal to its own serial and permits no successor — the chain is sealed at the `Dec` event. The seal-cap rejects any submission whose parent sits before the `Dec` (`parent_serial < seal_serial`); a direct `Dec`-child passes the cap (`parent_serial == seal_serial`) and is rejected by the terminal-state gate (Decommissioned accepts no submissions of any kind).

KEL additionally tracks `lastRecoveryRevealingEvent` (`Rpr` / `Ror` / `Fed` / `Dec`) for the spent-key / immunity rule. This is a distinct concept from the seal — the seal-advancing kinds bound chain-state changes, while the recovery-revealing kinds track which recovery-key preimage is currently committed (and once spent, cannot be reused to recover against an earlier divergence). Recovery-preimage rotation cadence is operator guidance, not a protocol-enforced cap.

A new event's parent MUST sit at-or-after the seal (`parent_serial >= seal_serial`). Since `event_serial = parent_serial + 1`, this is equivalently `event_serial > seal_serial` — the event lands strictly after the seal-defining event. Any submission whose parent sits in the locked portion (`parent_serial < seal_serial`) is rejected (`"Cannot extend serial V — parent in locked portion behind seal at serial S"`). This guarantees the auth context resolved at the event's parent is the chain's currently-tracked policy / key state — not a stale one — and that no event lands at the seal-defining event's own serial.

**Bounds on the post-seal window per primitive:**

- **KEL**: the **seal-advance cap** bounds the chain at `MINIMUM_PAGE_SIZE − 2 = 62` non-seal-advancing events between privileged-or-archiving events (`Rpr` / `Ror` / `Rot` / `Fed`). `MINIMUM_PAGE_SIZE` is a protocol constant (a deployment floor, not a per-deployment knob), so a recovery batch produced on any conformant deployment fits in any other's single page. Recovery-key-preimage rotation cadence is operator guidance — not a protocol-enforced cap — because recovery keys are typically hardware-held and preimage-identified rather than usage-degraded, and a protocol-forced cadence would impose access on cold-stored / separated-custody recovery keys on a fixed schedule.
- **IEL**: no protocol cap — every non-inception IEL event advances the seal, so the seal coincides with the tip on linear chains and within-window forks don't structurally exist. The "how stale can authority become" bound is operator-side discipline.
- **SEL**: protocol-bounded at `MINIMUM_PAGE_SIZE − 2 = 62` non-seal-advancing events via the **seal-advance cap** (`Est` at v=1; `Evl` or `Rpr` thereafter). Combined with SEL's per-event `policyPin` ratchet — the **per-chain forward-only floor** (forward-only relative to the cumulative max over **all** prior surviving pins, not merely the parent; see the section below) — this prevents stale-IEL-policy holders from extending an existing branch with a regressed binding. The `− 2` headroom accommodates an atomic 2-event lifecycle batch — `[Rpr, Evl]` (repair followed by a re-resealing `Evl`) is the SEL worst-case shape — in one `MINIMUM_PAGE_SIZE`-bounded page on every conformant deployment. The same 2-event-headroom rationale applies to KEL with its primitive-specific worst-case batch.

The SEL-specific ratchet that the bound composes with lives at [§Per-Chain Forward-Only Floor (SEL-specific)](#per-chain-forward-only-floor-sel-specific) below.

#### Routing order

The merge layer routes a submitted event through four rule scopes, in this **recommended structural order**:

1. **Structural validation.** Per-kind field rules, SAID integrity, prefix consistency, signature shape, chain-linkage continuity. Any failure here is a structural error and the submission is rejected regardless of chain state.
2. **Seal-cap.** The event's parent must sit at-or-after `lastSealAdvancingEvent` in chain order (`parent_serial >= seal_serial`). Submissions whose parent is in the locked portion are rejected — this is what enforces current-state-only authority (see [§Forks are Seal-Bounded](#forks-are-seal-bounded)). A Decommissioned chain's seal sits at the `Dec` event's serial, so the cap rejects any submission whose parent sits before the `Dec`; a direct `Dec`-child passes the cap (`parent_serial == seal_serial`) and is rejected by the terminal-state gate (Decommissioned accepts no submissions of any kind).
3. **Fork-detect.** The event's `(parent_said, serial)` is checked against the chain's existing events at that serial. If acceptance would produce a divergent set containing a privileged event — by joining an existing divergent set or by colliding with an existing event at the same serial when the candidate is privileged — the submission is rejected (see [§Privileged Divergence is Terminal](#privileged-divergence-is-terminal)). Non-privileged collisions form (or extend) a divergent set; archiving kinds route through their discriminator before this check fires.
4. **Kind-specific.** Per-kind authorization (signing, dual-signing, anchor-tier checks against the gating policy, leaves resolved per primitive), structural-extension rules (Evl change-≥1 + `policyPin` non-regression, inception batch rule, etc.), and chain-state effects (seal advance, decommission, repair).

**Why this order — adversarial-input diagnostics.** The recommended order is chosen so attacker diagnostics name the structural cause-of-rejection correctly. Consider attacker input where `parent.serial < seal.serial` AND a conflicting event already exists at `candidate.serial`: seal-cap first (rule 2 before rule 3) emits `ParentLocked`, accurately naming the structural rule the attacker violated — the parent sits in the locked portion. Fork-detect first finds the conflict in locked history and rejects as an immutable-history violation, naming the symptom (the conflict in locked storage) rather than the cause (the attacker's parent reference into the locked portion). Implementations MAY commute scopes whose outcomes match under valid input, but SHOULD follow the recommended order so adversarial-input diagnostics correctly name the structural cause.

The seal never forks (rule 2 plus rule 3 jointly). Divergent sets contain only non-privileged events. The chain's three per-node states (Active, Divergent, Decommissioned) are the only states the rules can produce.

#### Per-Chain Forward-Only Floor (SEL-specific)

SEL is the only primitive where authorization context is referenced via a separate field (`policyPin`) pointing at other chains. KEL and IEL have no analog — they resolve authorization from commitments / policy intrinsic to their own chain at the event's parent (`previous`), so there's nothing for a per-event monotonic check to compare across. (KEL's `federationBinding` also points at another chain, but it is membership context set under the `Fed` rule, not per-event authorization context — nothing ratchets.) (An **aggregate IEL** that carries its own `policyPin` over `{governance, delegation}` would want the same floor for the same reason; reconciling "IEL has no analog" with that aggregate-IEL pin is a **separate, low-priority** doc item — and the credential floor does **not** depend on it, since it lives on each entity's **registry-SEL**, not the IEL pin.)

The pin ratchets forward along a **per-chain forward-only floor**. (The floor is **cumulative** — the running max over **all** prior surviving pins, retained per prefix across gaps — **not** a parent-relative check against only the immediately-preceding pin.) As the verifier walks the SEL chain it maintains, per directly-referenced IEL prefix `Z`, `chain_floor[Z]` = the maximum marker-serial any prior **surviving** pin referenced on `Z`; a new pin is valid iff **every** slot referencing `Z` sits at marker-serial `≥ chain_floor[Z]`, and the floor then advances to the running max. A later pin that **omits** `Z` does not clear `Z`'s floor. Flooring **every** occurrence (not just the maximum) is load-bearing — flooring only the max would let a backdated *second* occurrence of `Z` ride alongside a fresh one. Keying by **prefix** (not slot position) is what defines slot correspondence across a policy change: a governance-gated `Evl` may co-evolve `governance` / `operation`, breaking positional correspondence, yet the per-prefix floor still pins every reference forward — so a co-evolved policy + pin cannot route a slot to older chain state. A prefix's **first appearance** — a prefix **never previously pinned on the surviving chain** — has no prior marker, so its first marker is free (absent floor ⇒ unconstrained — the inception residual at [§Anchor Tier Elevation](#anchor-tier-elevation) and event-shape `§policyPin`); a dropped-then-**re-referenced** prefix is **not** a first appearance — its floor is retained across the gap, so the re-reference stays floored and a drop-and-reintroduce cannot reset it. The floor counts only **validly-anchored** pins: a SEL `Evl` is privileged and seal-advancing, so no SEL `Rpr` ever archives it (an `Rpr`'s parent is at-or-above the seal), and its anchor is **tier-2** (on a seal-advancing `Rot`), **durable against `Rpr`** ([§Tier-2 anchor durability](#anchor-tier-elevation)). An `Evl`'s pin drops from the floor only when its **contributing KEL surfaces federation-irreconcilable** with the anchor's host **at-or-beyond the divergent serial** — the host branch becomes non-canonical and the `Evl`'s `policy_satisfied` flips false ([§Terminology](#terminology), cross-chain anchor satisfaction) — while the `Evl` event stays on the SEL chain. In the linear case every `Est`/`Evl` anchor is durable, so the floor is the immutable `Est`/`Evl` sequence. A pin-only `Evl` must still advance ≥1 slot (see [§Shape constraints on SEL Evl](#shape-constraints-on-sel-evl)). The pin itself is **shallow** — one slot per `id` / `grp` occurrence in the policy text, every entry an IEL state-marker; device / KEL evidence is per-event and self-dating, never part of the pin and never floored (event-shape `§policyPin`). Only `Est` / `Evl` carry a pin, and both land only as clean linear extensions (see [§Privileged Divergence is Terminal](#privileged-divergence-is-terminal)), so the comparison is always against the submitter's linear parent.

**Divergent SEL chains share the inherited pin.** Divergent sets contain only `Ixn`, and `Ixn` / `Rpr` / `Dec` carry no pin — every branch inherits the same tracked pin from the last `Est` / `Evl` at-or-below the divergence ancestor, so within-chain pin variation cannot occur. Cross-node disagreement about which `Est` / `Evl` landed at a serial is surfaced as federation-irreconcilable at the federation layer (see [§Limit of the doctrine — concurrent privileged event races](#concurrent-privileged-event-races)), not by the per-event ratchet.

#### Privileged Divergence is Terminal

The protocol's terminal-authority mechanism is two composable rules. Read them in order: rule 1 names what counts as privileged divergence and why the merge layer rejects it; rule 2 specifies the structural conditions on repair events (`Rpr`).

**1. Privileged-divergence-is-terminal.** A privileged event that would land in a divergent set — by extending the divergence ancestor `v_{d-1}.said` while the chain has an existing event at `v_d`, or by colliding at the same serial on a linear chain — is rejected at the merge layer. The seal never forks: divergent sets contain only non-privileged events by construction. Privileged kinds differ per primitive:

- **KEL privileged-or-archiving**: `Rot`, `Rpr`, `Ror`, `Fed`, `Dec`. The privileged subset (`Rot`, `Ror`, `Fed`, `Dec`) is rejected when its landing would create or join a divergent set; the archiving event (`Rpr`) routes through the discriminator instead. The recovery-revealing sub-class (`Rpr`, `Ror`, `Fed`, `Dec`) is dual-signed; `Rot` is single-signed and seal-advancing but not recovery-revealing.
- **IEL privileged**: every IEL event is **policy-gated and privileged** (`Fcp` / `Icp` / `Evl` / `Dec` by `governance`; `Del` / `Rsc` by `delegation`), so no divergent set can ever form locally on IEL. The privileged-divergence rule (rule 1) applies to post-inception kinds (`Evl`, `Del`, `Rsc`, `Dec`): a second event at the same serial would have to be privileged, and rule 1 rejects it at merge. Inception kinds (`Fcp`, `Icp`) sit outside rule 1 (no parent), but are non-divergent by prefix derivation — two distinct inceptions for the same prefix are structurally impossible. IEL chain state reduces to `{Active, Decommissioned}` locally.
- **SEL privileged-or-archiving**: `Est`, `Evl`, `Rpr`, `Dec`. The privileged subset (`Est`, `Evl`, `Dec`) is rejected when its landing would create or join a divergent set; the archiving event (`Rpr`) routes through the discriminator. `Est` is privileged at v=1 (tier-2 anchored, operation-authorized seal-advance — see [§Anchor Tier Elevation](#anchor-tier-elevation)).

Archiving events (`Rpr`) route through the discriminator before any divergent-set check fires — they resolve rather than create divergence. Non-privileged events at the same serial form (or extend) a divergent set, which is recoverable via the archiving primitive of the same chain.

Cross-node race outcomes — two nodes accepting different privileged events at the same serial via independent linear-chain extensions — are not a per-node state. Each node's seal-cap rejects the gossip-arriving competing event, and the federation surfaces the disagreement via divergent witness receipts at the federation layer (see [§Limit of the doctrine — concurrent privileged event races](#concurrent-privileged-event-races) and [`federation/witnessing.md`](federation/witnessing.md)).

**2. Repair-event conditions.** Two structural conditions apply to repair events — `Rpr` — at the merge layer. They are data-driven (no receiver-state dependency), uniform across primitives with per-primitive instantiations.

2a. **Hard auth at landing.** Governance / signature check hard-fails on rejection at the merge layer; no soft-fail.
   - **KEL Rpr**: dual-signed. `publicKey` preimage matches the parent's `rotationHash`; `recoveryKey` preimage matches the parent's `recoveryHash`. Both signatures verify; both digest commitments match.
   - **SEL Rpr**: evaluation of the SEL's own `governance` — its leaves resolved against the IEL state at the `policyPin` — hard-passes threshold. Repair-event SAID is anchored by a tier-3 KEL event per contributing governance member.
   - Authority concurrence is a moment-in-time question; "submit and satisfy later" does not generalize from cross-chain content references (which can resolve later because content is fetchable) to authority-tier checks.

2b. **Repair-event `previous` must not be in the locked portion.** `previous.serial ≥` the serial of the most recent seal-advancing event on the chain (any branch — privileged or archiving). The repair event's own serial = `previous.serial + 1`.
   - **KEL**: seal-advancing events are `Rot`, `Rpr`, `Ror`, `Fed`, `Dec`. Subject to the bound: `Rpr`.
   - **SEL**: seal-advancing events are `Est`, `Evl`, `Rpr`, `Dec`. Subject to the bound: `Rpr`.
   - **IEL**: no repair events exist on IEL (no `Rpr`). The bound is vacuous on IEL.
   - If no privileged event has landed (only inception + non-privileged events), the bound holds vacuously — the repair event's `previous` can be any chain event including inception.

**Semantic intent.** The honest construction of a repair event extends its submitter's local tip. A legitimate submitter wouldn't insert events into their own stream from anywhere else, and wouldn't accept adversarial events into their stream and append on top of those (that would imply trust in the adversary's events). Chain data cannot identify a submitter or distinguish "honest extension of submitter's tip" from "adversarial extension of an injected fake-tip" — the protocol has no notion of identity at the chain layer. Condition 2b restricts allowed constructions to those that *could* be honest tip-extensions: anything with `previous` in the chain's locked portion is structurally incompatible with extending a current legitimate tip and is denied.

The bound prevents revival attacks: a party holding stale authority (e.g., a recovery preimage revealed by an earlier `Rpr` / `Ror` / `Fed`, or a revoked governance member whose old policy SAID remains immune-resolvable) cannot construct a repair event against an old authority position to rearrange the chain. Only current authority gates repair events. See [§Terminology](#terminology) for the locked-portion concept.

When a repair event's `previous` is the divergence ancestor (`v_{d-1}`), `Rpr` land at `v_d`. This shape is cross-node-validatable: `v_{d-1}` is structurally shared across all nodes (it lands cleanly before any divergence), so the repair event validates uniformly regardless of which divergent contents each node received. This is what solves the cross-node propagation problem that breaks tip-extension and combined-digest approaches.

##### Two parent shapes for archiving recovery events

KEL and SEL `Rpr` resolve divergence by archiving events via the discriminator. They each take two parent shapes, named by what `previous` points at:

- **Branch-tip-extending shape** — `Rpr.previous` is a branch tip at `v_d`. Rpr extends that branch at `v_{d+1}`; the other branch is archived.
- **Divergence-ancestor-extending shape** — `Rpr.previous` is `v_{d-1}`, the divergence ancestor. Rpr lands at `v_d`; ALL events at `serial >= d` (both branches) are archived. Rpr is the only event at `v_d` after the discriminator runs.

##### Routing semantics of privileged and archiving kinds

How the merge engine routes the two non-content classes (the full three-class taxonomy is in [§Event-class taxonomy](#event-class-taxonomy) below):

- **Archiving kinds** — `Rpr`. Go through the discriminator's archival path. Either parent shape (branch-tip-extending or divergence-ancestor-extending) routes through the discriminator before any divergent-set check fires; the discriminator resolves the divergent set rather than producing one.
- **Privileged kinds** — `Rot`, `Ror`, `Fed`, `Dec` on KEL; `Est`, `Evl`, `Dec` on SEL. Do not archive. The merge layer rejects a privileged submission whose acceptance would create or join a divergent set — either by extending `v_{d-1}.said` when an existing event already occupies `v_d`, or by colliding with an existing event at the same serial on a linear chain. A privileged event landing as a clean linear extension of the chain's tip is admitted normally.

The verifier rule simplifies to:
- Divergent at `v_d`? (a divergent set exists in the chain data)
  - Yes → divergent (recoverable via `Rpr`). Divergent sets contain only non-privileged events; privileged kinds never appear in them.
  - No → linear (Active, or Decommissioned via `Dec`).

IEL has no Divergent state: every IEL event is privileged, so rule 1 rejects any second event at the same serial at merge. IEL is `{Active, Decommissioned}` locally.

##### Cross-node priv-vs-priv races

Two nodes can each accept a competing privileged event extending `v_{d-1}` via independent linear-chain extensions: each event lands cleanly on its submitting node (the seal advances locally), and gossip then delivers each event to the other node where the seal-cap rejects the late arrival (its parent sits in the locked portion behind the now-advanced seal). Each node retains its locally-landed first-receive; the federation does not converge at the protocol layer. Federation-level convergence is provided by **divergent witness receipts** at the federation layer: federation members witness every structurally-valid event they observe (always-witness; see [`federation/witnessing.md`](federation/witnessing.md)), and adjacent receipts at the same chain position carrying different `witnessedSaid` values are the structural evidence that the federation cannot agree at that position. See [§Limit of the doctrine — concurrent privileged event races](#concurrent-privileged-event-races).

##### Repair-event authorization

Authorization for a repair event (`Rpr`) resolves through the commitments at the event's parent (`previous`).

- **KEL.** The dual signature is produced under the private signing and recovery keys whose public-key preimages are committed by the parent event's `rotationHash` and `recoveryHash`. Revealing the public-key preimage via a prior event landing at the parent's child serial does not yield the corresponding private key; signing capability remains submitter-held.
- **SEL.** The SEL's own `governance`, its leaves resolved against the IEL state at the `policyPin` tracked at the parent event (`Rpr.previous`).
- **IEL.** No repair events on IEL. Every IEL event is privileged, so divergent sets cannot form locally — a second event at the same serial is always privileged and rejected at merge. There is no divergent state for a repair event to resolve.

Repair-event authorization is **HARD** at the merge layer per condition 2a. **General invariant: any event with failed auth is rejected.** A repair event (or `Dec`) whose dual-signature, governance-anchor, or SEL-`governance` check fails is rejected by the merge handler; the chain stays at its prior state. The DB-cannot-be-trusted invariant requires this — an unauthorized terminal must not advance the chain locally. See [§Verifier and merge are distinct treatments](#verifier-and-merge-are-distinct-treatments) for how the verifier's soft-fail composition is hardened at the merge layer.

**Recourse against Tier-2 `Rot` takeover (KEL specifically)**: an adversary holding the rotation-key preimage at `v_N` (revealing their `Rot` at `v_N`) does not hold the recovery-key preimage committed by the prior establishment's `recoveryHash`. A `Rpr` (branch-tip-extending on a divergent chain, or divergence-ancestor-extending where the divergence ancestor's commitments are still legitimate) — subject to the locked-portion bound (condition 2b) — resolves dual-sig against the parent's commitments; the legitimate party's recovery-key preimage satisfies, the adversary's does not.

The repair-event bound (condition 2b) together with the merge-layer's rejection of privileged events in or against divergent sets means that, on KEL / SEL, a chain's only exits from Divergent are archiving repair (back to Active) or operator reincept under a new prefix.

##### No dedicated termination-by-contest event

No primitive has a dedicated termination-by-contest event. The event taxonomies are:

- **KEL**: `Fcp`, `Icp`, `Rot`, `Ixn`, `Rpr`, `Ror`, `Fed`, `Dec`.
- **IEL**: `Fcp`, `Icp`, `Evl`, `Del`, `Rsc`, `Dec`.
- **SEL**: `Icp`, `Est`, `Ixn`, `Evl`, `Rpr`, `Dec`.

Structural reasoning: chain data alone cannot distinguish a legitimate submitter from an adversary with equivalent authority. A protocol primitive justified by reference to submitter intent ("the legitimate operator's terminate-with-prejudice signal") is structurally incoherent — the chain layer has no identity concept, so identity framing cannot land in a primitive. Per-node, `Dec` is the only protocol path that terminates a chain.

**Chain lifecycle paths (per-node):**

- **Termination via clean shutdown**: `Dec` lands as a linear extension of the chain's tip → Decommissioned.
- **Recovery from divergence**: `Rpr` archives one branch; chain returns to Active.
- **Rejected (no state transition)**: a privileged event that would create or join a divergent set is rejected at the merge layer per rule 1 above. The submitter's recourse is to extend the local tip cleanly (re-fetch + re-submit) or accept the existing tip.

Cross-node disagreement on which privileged event won a federation race is a federation-level concern, surfaced via divergent witness receipts (see [§Limit of the doctrine — concurrent privileged event races](#concurrent-privileged-event-races) and [`federation/witnessing.md`](federation/witnessing.md)). It is not a per-node chain state.

**Pre-emptive-suspicion gap (acknowledged).** A submitter who detects compromise pre-emptively (e.g., a contributing KEL was breached) and wants to mark a chain as suspect without retiring it has no protocol-level "compromise signal." Available paths: rotate out the compromised key via `Rot` (KEL) or `Evl` (IEL) (chain stays alive, no compromise signal); `Dec` (clean retirement — semantically misleading when compromise is the actual cause); out-of-band attestation under a separate KEL (requires a parallel discovery channel). This trade-off is accepted; the protocol's terminal and recourse paths remain intact.

<a id="concurrent-privileged-event-races"></a>

##### Limit of the doctrine — concurrent privileged event races

Concurrent privileged event races between federation peers do not structurally converge at the protocol layer. This covers all shapes — between archiving repair events (`Rpr`), between privileged events (`Rot` / `Ror` / `Fed` / `Dec` on KEL, `Est` / `Evl` / `Dec` on SEL, `Evl` / `Del` / `Rsc` / `Dec` on IEL), and mixed (`Dec`-vs-`Ror`, `Dec`-vs-`Rot`, etc.). Once a privileged event lands at `v_d` on a node, that node's seal advances and any competing submission whose parent sits at-or-before `v_{d-1}` is rejected by the seal-cap. Different nodes that received different "first" submissions end up on different per-node tips.

**The federation's convergence layer for these races is divergent witness receipts at the federation layer** — see [`federation/witnessing.md`](federation/witnessing.md) for the full mechanics. Federation members witness every structurally-valid event they observe at chain positions they are sort-selected for (always-witness; reporters, not deciders). Adjacent receipts are indexed at the chain position `(prefix, serial)` rather than at event SAID, so when threshold-many receipts witness two or more distinct `witnessedSaid` values at the same position, the position is **federation-divergent** and the prefix is federation-irreconcilable at-and-beyond that serial. Cross-node divergence — priv-vs-priv races, priv-vs-non-priv state mismatches, divergent vs Decommissioned — surfaces uniformly through this mechanism. The protocol layer enforces local invariants strictly; the federation layer surfaces all cross-node disagreement.

This is a deliberate trade-off. The seal-cap and locked-portion bound prevent stale-authority chain rearrangement: a party holding past-position private keys must not be able to land an event targeting the locked portion at any future time. Relaxing the bounds to admit competing privileged events at a sealed serial would re-open that long-tail killswitch surface. The bounds stay unconditional; federation-race non-convergence for concurrent privileged submissions is resolved at the federation layer via witness attestation rather than at the protocol layer via fork merging.

If an adversary holds tier-3 capability on a KEL (rotation + recovery preimages), or compromises threshold-many full-tier KELs on an IEL governance policy, the chain is structurally owned by the adversary and the protocol provides no recovery primitive. Defense lives in policy composition — IEL governance policies should require threshold-many distinct custody domains, so full compromise of any one domain leaves the policy threshold intact. See [§Limit of the Doctrine](#limit-of-the-doctrine) for the broader treatment of current-state compromise.

##### Pre-seal verifiability

A chain preserves the structural verifiability of every event at-or-below `lastSealAdvancingEvent`, regardless of any subsequent per-node divergence or federation-level irreconcilability. The seal-cap and locked-portion bound prevent any event — on any branch, at any future point — from rearranging or invalidating events at-or-below that seal serial. The at-or-below-seal portion is permanently final.

A chain remains useful as a verification surface for everything sealed before any later disruption:

- **Anchors hosted at-or-below the seal** stay anchored. A KEL `Ixn` that anchored an IEL event at-or-below the seal stays a valid attestation. A tier-1 (`Ixn`) anchor hosted above the seal is NOT durable — it could have been authored under captured signing-key capability and is not structurally distinguishable from adversary work. Such anchors become durable only when a subsequent seal-advancing event lands cleanly past them.
- **Credentials issued under an IEL state at-or-below the seal** remain verifiable. An issuance pinned to an IEL event that sits at-or-below the IEL's `lastSealAdvancingEvent` can still be checked against the IEL state at that event — the chain segment used for verification is structurally immutable.
- **SELs whose `policyPin` binds at-or-below-seal IEL state** stay trust-evaluable for that bound state. The `IelDivergent` rule enforces this by accepting only bindings where `bound_event.serial <= bound_iel.lastSealAdvancingEvent.serial`.
- **Audit and forensic queries** on a chain with above-seal divergence produce truthful, structurally-grounded answers about state at-or-below the seal. Above-seal events appear in the forensic record but are not structurally trustworthy.

**Why the boundary is the seal.** `lastSealAdvancingEvent` advances only on seal-advancing events that land cleanly on the linear chain. The seal never forks: privileged events that would create or join a divergent set are rejected at the merge layer, so every seal advance is a clean linear-chain landing. Events at-or-below the seal were authored under at-least-tier-2 auth that landed cleanly (each seal advance is a clean privileged or archiving landing — both classes require tier-2 or tier-3 capability), which the protocol accepts as structurally valid sealing-level auth regardless of submitter. Events above the seal — in the seal-to-divergence-or-tip gap — carry tier-1-only auth, structurally indistinguishable from signing-key-only adversary capture. The seal is the boundary the protocol can defend.

**On above-seal events: submitter-indistinguishability.** Above-seal events that landed under valid policy at the time they were processed do not carry "who actually submitted them" information. The same authorization that admitted a legitimate operator's event would admit an adversary's event under captured authority. The protocol has no trusted way to bring out-of-band claims about above-seal authorship into the chain — verification tokens cannot be augmented with claims that originated outside the chain. Consumers relying on protocol-trusted information have nothing to distinguish "this above-seal event was authored legitimately" from "this event may have been adversarial." Consumers may apply out-of-band judgment about specific above-seal events if they have it (their own observation history; an external attestation through a different channel) but the protocol cannot make those judgments for them.

This is the consumer-side complement of [§Compromise is Permanent](#compromise-is-permanent). The "past authority cannot act" rule and the locked-portion bound together mean: once a chain segment sits at-or-below the seal, it is final — for the chain itself (no further events target it) AND for consumers (they can verify against it indefinitely).

The verifier signals this via `policy_satisfied`: queries against SAIDs anchored at-or-below `lastSealAdvancingEvent` return `policy_satisfied = true`; queries against SAIDs above the seal return `policy_satisfied = false`. The boundary is the seal.

#### Event-class taxonomy

The protocol's events fall into orthogonal axes: **class** (chain-state effect when landing in a divergent set) and **tier** (key material required to forge the anchor). This divergence-axis class is the three-name set content / privileged / archiving — distinct from the five-name lifecycle class on the per-log taxonomy tables in [`event-shape.md`](primitives/data/event-logs/event-shape.md): lifecycle `terminal` kinds (`Dec`) route as `privileged` here, and lifecycle `inception` kinds sit outside this classification. The table below names every event kind across all three primitives; the structural pattern that emerges is cited from elsewhere in the doctrine.

**Inception events** (KEL `Fcp` / `Icp`; IEL `Fcp` / `Icp`; SEL `Icp`) are structurally outside this classification — they have no parent, and prefix derivation forces unique chains. Enumerated in [§KEL Inception](#kel-inception).

| Chain | Event | Class | Tier | Anchor relationship |
|-------|-------|-------|------|---------------------|
| KEL | `Ixn` | content | 1 | hosts tier-1 anchors |
| KEL | `Rot` | privileged | 2 | hosts tier-2 anchors |
| KEL | `Ror` | privileged | 3 | hosts tier-3 anchors (and satisfies tier-2 anchor requirements per [§Anchor Tier Elevation](#anchor-tier-elevation)) |
| KEL | `Fed` | privileged | 3 | federation-binding mutation (founder binding, re-binding, or witness-params update); hosts tier-3 anchors |
| KEL | `Rpr` | archiving | 3 | — |
| KEL | `Dec` | privileged | 3 | — |
| IEL | `Evl` | privileged | 2 | requires tier-2-capable KEL anchor per member |
| IEL | `Del` | privileged | 2 | requires tier-2-capable KEL anchor per delegation member |
| IEL | `Rsc` | privileged | 2 | requires tier-2-capable KEL anchor per delegation member |
| IEL | `Dec` | privileged | 3 | requires tier-3-capable KEL anchor per member |
| SEL | `Est` | privileged | 2 | requires tier-2-capable KEL anchor per member |
| SEL | `Ixn` | content | 1 | requires `Ixn` per member |
| SEL | `Evl` | privileged | 2 | requires tier-2-capable KEL anchor per member |
| SEL | `Rpr` | archiving | 3 | requires tier-3-capable KEL anchor per member |
| SEL | `Dec` | privileged | 3 | requires tier-3-capable KEL anchor per member |

**Legend.**

- **Class.** Chain-state effect on the event's own chain.
  - **Content** — does not advance the seal; landing in a divergent set leaves the chain Divergent, recoverable via the chain's archiving primitive (`Rpr`).
  - **Privileged** — advances the seal on a clean linear landing; rejected at the merge layer if its landing would create or join a divergent set (see [§Privileged Divergence is Terminal](#privileged-divergence-is-terminal)). Privileged events never appear in divergent sets.
  - **Archiving** — advances the seal AND archives the discriminator-losing branch when landing in a divergent set. The archiving-precedence rule fires the discriminator BEFORE the divergent-set check, so archiving events resolve rather than create divergence.
- **Tier.** Key material required to forge.
  - For KEL events: which preimages the event reveals (1: signing key only; 2: + rotation preimage; 3: + recovery preimage; tier-3 KEL events are dual-signed).
  - For IEL / SEL events: tier of KEL anchor required per contributing policy member.
- **Anchor relationship.** For KEL events: which IEL / SEL anchor tier this kind hosts. For IEL / SEL events: which KEL anchor capability is required per contributing policy member to satisfy authorization.

**Structural pattern.**

- **Content** events populate tier 1.
- **Privileged** events populate tier 2 or tier 3.
- **Archiving** events populate tier 3 (exclusively).

Tier 2 is privileged exclusively; tier 3 is mixed (privileged + archiving). The pattern reflects two facts: lower tiers don't carry chain-state-effecting authority, and archival operations cryptographically require the recovery preimage (tier 3).

**Tier and class are independent axes** — the table's cell population happens to align (tier-1 always content, tier-2 always privileged, tier-3 mixed) but the axes describe distinct properties. Tier describes "what key material was required"; class describes "what happens to the chain when the event lands in a divergent set." See [§Anchor Tier Elevation](#anchor-tier-elevation) for tier semantics and the durability property derived from this taxonomy.

#### One Divergent Generation at a Time

The protocol bounds divergence to **one unresolved generation at a time** on any given chain. Within a generation, the divergent set at `v_d` carries 2 non-privileged events (recoverable via `Rpr`); privileged events that would create or join a divergent set are rejected at the merge layer. Beyond `v_d`, the divergence invariant caps each branch at 1 event per serial (the post-divergence linear-extension cap, applied per branch).

Two unresolved generations cannot coexist on the same chain. A second divergent generation at some `v_{d'} > d` would necessarily place 2 events at `v_{d'}` (one per branch on the second divergence), violating the first generation's post-divergence cap. The structural rules forbid stacking.

**Implication for the verifier walker.** An archiving event (`Rpr`) resolves a divergent generation; its archival must be applied to the walker's running state before any subsequent walk step that could introduce a new divergence. Without inline normalization, the chain would carry a stale divergent set into post-resolution state, structurally forbidding any further divergence even after semantic resolution.

#### Anchor Tier Elevation

Three operation classes, three key-tier requirements. Privileged IEL and SEL events anchor in higher-tier KEL events, not in routine `Ixn`. The elevation closes the signing-key-only adversarial pathway to forging governance acts, binding establishments, and terminal events on the chains that root other chains' authority.

KEL closes this surface intrinsically: KEL `Rpr` / `Ror` / `Fed` / `Dec` are dual-signed (signing + recovery), already requiring tier-3 key material to forge. IEL and SEL have no analogous intrinsic mechanism — they piggyback on KEL's tier hierarchy by requiring privileged IEL / SEL events to anchor in KEL events of the matching capability tier. The per-tier mapping:

**Three-tier mapping.** Each operation class requires a KEL anchor of at-least the named tier:

| Tier | Operation class | Minimum KEL anchor capability | Key material required per contributing KEL |
|------|----------------|------------------------------|-----------------------------------------------|
| 1 | Routine extension | `Ixn` | Current signing key (already known / active; 0 hidden preimages) |
| 2 | Governance declaration or evolution; binding establishment; seal advance | `Rot` (or any tier-3 KEL event) | Rotation-key preimage (1 hidden preimage; committed by prior establishment) |
| 3 | Recovery; terminal | `Ror` or `Fed` | Rotation-key preimage AND recovery-key preimage (2 hidden preimages; both committed by prior establishment) |

**Tier-3 events satisfy tier-2 anchor requirements.** A tier-3 KEL event (`Ror` or `Fed`) reveals both the rotation preimage and the recovery preimage; either one already satisfies the rotation-preimage requirement that tier-2 anchoring is checking against. The verifier-side leaf-anchor check is *minimum-tier-capability*, not *exact-event-kind*: any KEL event of at-least the required capability tier matches. This matters at the bootstrap ceremony where founder `Fed` events at v=1 are the tier-2 anchors for the in-batch federation IEL `Fcp` (see [`federation/bootstrap.md`](federation/bootstrap.md)).

**Per-primitive anchor rules.**

| IEL Event | Minimum anchor tier | Notes |
|-----------|--------------------|-------|
| `Fcp` | special — see notes | Federation IEL inception. Self-attesting at v=0 via the kind-dispatched verifier carve-out (pool source = the `Fcp`'s `governance` policy's DSL expansion to leaf prefixes). Founder Fed events on founder KELs anchor the federation Fcp from the KEL side; see [`federation/bootstrap.md`](federation/bootstrap.md). |
| `Icp` | 2 | Identity / other non-federation IEL inception. Anchored by tier-2-capable KEL event per contributing member. |
| `Evl` | 2 | Anchored by tier-2-capable KEL event per contributing member. |
| `Del` | 2 | Delegation declaration. Anchored by tier-2-capable KEL event per contributing `delegation`-policy member. |
| `Rsc` | 2 | Delegation rescission. Anchored by tier-2-capable KEL event per contributing `delegation`-policy member. |
| `Dec` | 3 | Anchored by tier-3-capable KEL event per contributing member. |

| SEL Event | Minimum anchor tier | Notes |
|-----------|--------------------|-------|
| `Icp` | n/a | Permissionless, no authorization, no anchor. |
| `Est` | 2 | Binding establishment; camping defense. Tier-2-capable KEL event per contributing member. |
| `Ixn` | 1 | `Ixn` per member. |
| `Evl` | 2 | Tier-2-capable KEL event per contributing member. |
| `Rpr` | 3 | Tier-3-capable KEL event per contributing member. |
| `Dec` | 3 | Tier-3-capable KEL event per contributing member. |

**Policy satisfaction under elevation.** The policy DSL's `dev(prefix)` leaf tests anchor presence on a KEL; composers (`thr` / `wgt` / `and`, nested `pol`) compose leaf results. Under anchor elevation, the leaf-level anchor check requires the hosting KEL event to be of capability at-least the tier specified for the dependent event; a leaf that finds an anchor of insufficient capability evaluates as unsatisfied. DSL composition is unchanged — `wgt` still sums satisfied-child weights against the minimum, and `pol` still recursively resolves and evaluates. The verifier accepts the event when the top-level policy evaluates as satisfied, where satisfaction is computed against the tier-appropriate anchor check at every leaf.

**Tier-2 anchor durability.** Tier-2 and tier-3 anchors are both structurally durable against `Rpr` archival — both are seal-advancing classes, so a `Rpr` cannot truncate at-or-before their serial (the seal-cap rejects). The difference between tier-2 and tier-3 is **forging difficulty only** — tier-2 requires the rotation-key preimage; tier-3 additionally requires the recovery-key preimage. The two-axis property of tier (forging difficulty + archivability) collapses to a single-axis property: forging difficulty. Tier-1 anchors (on `Ixn`) carry no such durability — a subsequent `Rpr` can archive them.

**SEL `Est` and camping defense.** SEL prefix derives from `(governance, operation, topic)` — predictable and well-known. An adversary can race-incept SEL chains for any tuple an operator might use. SEL `Icp` is permissionless and dedup-equivalent: any party's `Icp` for the same tuple produces the same SAID and lands once regardless of who submits it. The actual binding and authorization happen at the next event — `Est` — which carries `policyPin` (pinning the IEL policy state) and is authorized under the SEL's `operation` policy (resolved at the `policyPin`). Elevating `Est` to tier 2 makes it privileged at v=1: a second `Est` for the same `(governance, operation, topic)` whose `said` differs from the locally-resident `Est` is rejected at the merge layer per [§Privileged Divergence is Terminal](#privileged-divergence-is-terminal). Each node's chain proceeds under whichever `Est` arrived first locally; the federation surfaces cross-node disagreement via divergent witness receipts. Camping defense is **mutually frustrating** at the federation level: the camper pays tier-2 anchor cost (per contributing policy member) to land their `Est` on at least one node, but cannot dislodge the legitimate operator's `Est` from any node where the operator's `Est` landed first — and vice versa. The disagreement surfaces in the federation-witnessing adjacent tables; consumers see "this prefix is federation-irreconcilable" rather than a working chain. Recourse against a successful camp is reincept under a new `(governance, operation, topic)` tuple. The structural defense composes four rules: `Icp` permissionless + dedup-idempotent; `Est` tier-2 raises per-attempt cost; the inception batch rule rejects bare `[Icp]`; uniform priv-rejection at merge means neither party can capture a working chain federation-wide. Mass camping becomes economically unprofitable. Against outsiders the defense is stronger still: a party who never satisfied the bound identity at any epoch cannot land an `Est` at all — no pin makes `operation = id(P)` satisfiable for them. The residual single-target exposure is the **ex-member**: anyone who satisfied `P`'s `authentication` at a past epoch — or who can extend a rotated-out member's KEL at tier 2 — can pin that old epoch (a pin slot naming `e_old`), satisfy `operation = id(P)` as tracked at `e_old`, and land a **working** `Est` on `P`'s identity-rooted discoverable namespace. The `Est` references `P` for the first time, so its pin sits in the **absent-floor** case — first appearance is unconstrained, no freshness floor (see [`primitives/data/event-logs/event-shape.md` §`policyPin`](primitives/data/event-logs/event-shape.md#policypin)); the per-chain forward floor only blocks a *later* `Evl` from regressing `P`'s marker below this `Est`, it does not bound the `Est` itself.

IEL has no `Est` counterpart because IEL `Icp` is itself the binding event — policies are declared inline at inception, authorized by the founding governance threshold. IEL prefix derives from the whole inception content — the `authentication` / `governance` / `delegation` policy SAIDs, the `roster` (aggregate IELs), the delegator's prefix in `delegating` (delegated IELs), and a `nonce` of opaque random bytes chosen by the inceptor; the resulting prefix is structurally unpredictable from outside, so the well-known-tuple camping surface doesn't exist. IEL `Icp` requires tier-2-capable KEL anchoring: the founding governance act is the same kind of act as `Evl`, and tier-2 (rotation-key preimage per contributing member) prevents signing-only compromise from creating fake-but-validly-governed IELs under stolen policy membership.

**Cross-chain anchor symmetry.** KEL achieves tier-3 intrinsically via dual-signature against `rotationHash` and `recoveryHash` preimages. IEL / SEL achieve it via anchor on KEL `Ror` or `Fed`. Both require the same cryptographic key material; the mechanism differs because IEL / SEL have no intrinsic key state to elevate against. KEL `Dec` is unchanged by anchor elevation — it does not anchor in another chain.

**What anchor elevation defends.**

- **Signing-key-only adversarial governance takeover.** Without elevation, an adversary with signing-only compromise of policy members could forge tier-1-anchored events. Under elevation, IEL `Icp` / `Evl` and SEL `Est` / `Evl` require tier-2-capable KEL anchoring per contributing member; tier-2 capability requires the pre-committed rotation-key preimage, which signing-only compromise does not yield. Governance acts (declaration, evolution, seal advance), SEL binding camping, and fake-IEL creation via signing-only compromise are all closed.
- **Adversarial terminal events without recovery-key compromise.** `Dec` requires tier-3-capable KEL anchoring per contributing member; tier-3 capability requires the rotation-key preimage AND the recovery-key preimage (both committed by prior establishment events, neither yet revealed). An adversary lacking the recovery-key preimage for any contributing member cannot forge tier-3-anchored `Dec`. Rotation-key compromise alone is insufficient.
- **Rotated-out kill-switch.** A rotated-out party who could in principle land `Dec` under the parent-event policy now needs tier-3 capability per contributing member — possession of both rotation-key and recovery-key preimages across the contributing policy members, not signing-key access. The structural authority of the parent's policy persists; the bar to exploit it is raised from tier 1 to tier 3.

**What anchor elevation does not defend.**

- **Recovery-key compromise.** A party holding both rotation- and recovery-key preimages (the tier-3 preimage pair) for enough policy members to satisfy the threshold can forge any IEL / SEL event class up to and including terminal events. They are structurally indistinguishable from the legitimate operator. Operational defenses (custody separation, threshold redundancy, monitoring) remain the only mitigation.
- **Fractured governance.** A rotated-out party convincing other policy members to voluntarily participate in a contesting event satisfies anchor checks legitimately. The protocol cannot distinguish "legitimate threshold coalition" from "rotated-out party plus current-state members." This is social, not adversarial.
- **Custody-degraded members.** Elevation's marginal value scales with per-member key-tier custody separation. A reference implementation that holds all three tiers on a single device gets no marginal protection — full-device compromise yields all three. The protocol is custody-agnostic; trait implementations can provide stronger custody options (HSM separation, geographic split, ceremony-gated reveal). Custody hygiene is a trait / integration concern, not a protocol one.

Anchor tier elevation is a **verifier-side rule**. The verifier walks each IEL / SEL event and checks anchor presence of the required capability in candidate policy members' KELs as part of computing threshold satisfaction. Submit handlers invoke the verifier; consumers reading gossip-received, replicated, or bootstrapped data enforce the same check. No submit-handler-only carve-out exists.

##### Threshold Composition

The anchor tier mapping is structurally only as strong as the composition of contributing KELs. Locking events on IEL / SEL require anchors per contributing governance-policy member; an adversary landing a malicious locking event must compromise the relevant tier on **threshold-many distinct custody boundaries**.

- **Tier-2-anchored locking events on IEL (`Evl`) require rotation-tier compromise on threshold-many KELs.** An adversary at rotation-tier on threshold-many KELs can land a policy-evolving `Evl`, effectively taking over the IEL.
- **Tier-3-anchored locking events (`Rpr`, `Dec` on SEL; `Dec` on IEL) require recovery-tier compromise on threshold-many KELs.** Strictly harder; recovery preimages are by construction held separately from active signing keys.
- **Threshold > 1 is the load-bearing structural mitigation.** A single-KEL governance policy collapses to "rotation-tier compromise = full IEL takeover" — structurally valid but operationally fragile. The federation IEL itself uses N-of-M.
- **Distinct custody boundaries matter.** Two KEL prefixes under the same operator's hardware compose to effective threshold 1 against an adversary who breaches that hardware. Policy composition must span genuine custody separation.
- **Cross-chain anchor satisfaction redundancy.** Composing with anchor count above exact threshold (`M > N` for N-of-M) protects against single-KEL recovery invalidating IEL / SEL anchors. Without redundancy, any single contributing KEL's anchor becoming non-canonical — a **tier-1 (`Ixn`)** anchor `Rpr`-archived, or a **tier-2/3** anchor's host surfacing **federation-irreconcilable** (see [§Tier-2 anchor durability](#anchor-tier-elevation)) — drops the IEL / SEL anchor below threshold and flips `policy_satisfied = false` for consumers (see [§policy_satisfied](#policy_satisfied)).
- **Federation IEL pattern is the canonical safe shape.** N-of-M across distinct federation members with redundancy ensures threshold-many rotation-tier compromises are infeasible without breaching multiple independent custody domains.

Composition fragility is a structural property of the policy itself, derivable by any consumer from chain data alone. The policy DSL is verifier-readable; `M` (total members) and `N` (threshold) are inspectable on every event whose authorization traces through the policy. A consumer computes the threshold buffer (`M − N`) and the per-member custody attestations available out-of-band, then degrades trust accordingly.

The verifier itself accepts any threshold ≥ 1: single-KEL policies are protocol-valid, and remain useful for narrow roles where a single custody domain is the deployment shape. They simply have a threshold buffer of zero and produce `policy_satisfied = false` for any IEL / SEL event whose contributing KEL has been recovered or whose prefix has surfaced as federation-irreconcilable. The chain mathematics surface this; consumers act on it.

#### KEL Inception

KEL inception is one of two structurally distinct kinds, dispatched by the kind discriminator at v=0. The kind determines whether the chain is pre-federation or federation-bound and what witnessing applies.

| Kind | When used | Anchor at v=0 | Witness params at v=0 | Eligible as federation member |
|------|----------|---------------|----------------------|------------------------------|
| `Fcp` | Founder pre-federation inception (no federation exists yet) | forbidden | forbidden | yes — founder KELs become federation-bound via `Fed` at v=1 in the bootstrap atomic batch |
| `Icp` | End-user federated inception | required (= federation IEL SAID) | required | yes |

Delegation is an **IEL** concept, not a KEL one: there is no delegated KEL inception kind. A delegated *identity* is an IEL whose `Icp` sets `delegating` to its delegator's prefix (see [`primitives/data/event-logs/event-shape.md` §Delegation handshake](primitives/data/event-logs/event-shape.md#delegation-handshake)).

**No-delegated-member rule.** A delegated IEL — one whose `Icp` set `delegating`, binding it to a delegator `X` — has its delegator holding structural authority over it: `X` can `Rsc` the delegation, neutralizing the delegate. This authority lives **outside** the federation's `governance` surface, so a delegated IEL admitted as a federation member would appear peer-equal in the federation's governance roster while being structurally subordinate to its delegator in a way the federation cannot see or govern. The constraint is **verifier-enforced at federation IEL `Evl` time**: an `Evl` that would add a delegated IEL (one with `delegating` set) to the federation's governance roster is rejected. End-user (non-member) identities may be delegated freely; the constraint applies only to federation membership. See [`federation/bootstrap.md`](federation/bootstrap.md).

**Fed event.** A separate `Fed` event kind (tier-3, dual-signed; seal-advancing and recovery-revealing) is the federation-binding mutation event. Three use cases: founder binding at v=1 after `Fcp` at v=0 (declares `federationBinding = federation_fcp.said`); re-binding at v > 1 (inter-federation transfer, subject to the "members cannot re-bind while members" constraint); params-only update (changes `witness_threshold` / `witness_selection_size` without changing federation). A `Fed` event MUST change at least one of (federation binding, witness params); a no-op `Fed` is rejected. See [`federation/bootstrap.md`](federation/bootstrap.md) for the bootstrap ceremony, re-binding mechanics, and federation membership vs federation binding distinction.

**Trusted federation `Fcp` SAID set.** Consumer-side trust composes from a configured set of trusted federation IEL `Fcp` SAIDs (compile-time-baked + runtime override). For each event the verifier walks back to the federation IEL's `Fcp`; if the `Fcp` SAID is in the trusted set, the federation is trusted for that event. Multi-federation chains (KELs that have transferred federations via `Fed` events) require each federation in the chain's history to be independently in the consumer's trusted set — no transitive trust. See [`federation/bootstrap.md`](federation/bootstrap.md) for the trust-chain walk.

#### Evl-after-Ixn ratchet (application pattern)

This is an **application-protocol convention, not a protocol invariant** — the verifier does not require `Evl`-trailing structure. Applications that want the properties below enforce the convention at their construction layer.

An application protocol can require trailing SEL `Ixn`s be followed by `Evl`, batching `[Ixn..., Evl]` as the atomic application operation. Plain `Ixn`-tailed chains are application-invalid by construction — conforming tooling never produces them, and consumers reject any chain whose tip is an unsealed `Ixn`.

`Evl` is tier-2 anchored — it must anchor in a tier-2-capable KEL event. So the pattern forces a key rotation on every sealed batch. Three layered properties result:

- **Exposure-window bounding (cryptographic).** Each operating signing key is exposed to operations for at most one batch. Pre-rotation hides the next key behind its hash until rotation reveals it: the next public key is structurally unreachable from cryptanalysis on the current key (offline signature analysis, side-channel observation, harvest-now-decrypt-later quantum attacks against the signature stream all operate on the current key's public bytes; the next key's bytes have not been observed). By the time the current key would be vulnerable, the chain has already rotated to a key the adversary has never seen. The property holds independent of custody arrangement — pre-rotation defends through *exposure surface*, not through where the keys are stored.
- **Policy-layer separation (when `operation ≠ governance`).** `Evl` is governance-authorized; `Ixn` is operation-authorized. An operation-key-only holder can produce `Ixn`s but not `Evl`. Multi-device or otherwise composed identities get real cryptographic separation between "operation-set wrote this" and "governance-set sealed this."
- **Consumer-visibility.** Conforming tooling batches `[Ixn..., Evl]` atomically, so an Ixn-tailed chain is structurally invalid under the convention — not a legitimate intermediate state. Consumers that observe an unsealed `Ixn` at the tip detect a convention violation (tooling bypass, buggy producer, or a producer that cannot produce the `Evl`) and reject the chain.

The exposure-window property is the load-bearing one and applies even to degenerate SELs where `operation = governance`.

**Where it applies:** any IEL+SEL composition where the operator wants exposure-window bounding on durable state, or where operation and governance need to be cryptographically separated, or where governance-aware consumers need a chain-completeness signal.

**Operational cost:** every sealed batch forces a rotation. The operator's rotation cadence is set by application traffic, not by an operator-defined schedule. For peer addresses where updates are infrequent, this is cheap; for high-frequency SEL traffic, the rotation overhead is non-trivial and the operator should batch `Ixn`s aggressively before sealing.

#### Decommission and clean retirement

When `Dec` lands cleanly on a linear chain (not in a divergent set), it is a clean-retirement signal — no compromise indicated. Pre-Dec events retain trust under their original authorization. Once `Dec` lands, the chain is Decommissioned: no further events of any kind are accepted, and the seal-cap rejects any competing submission whose parent sits at-or-before `v_{d-1}`. Past content keeps its meaning. `Dec` is itself a privileged event, so a `Dec` whose landing would create or join a divergent set is rejected at the merge layer per [§Privileged Divergence is Terminal](#privileged-divergence-is-terminal) — `Dec` decommissions only via a clean linear-chain landing. Federation-race convergence between a `Dec` and a concurrent competing privileged submission is handled at the federation layer via divergent witness receipts (see [§Limit of the doctrine — concurrent privileged event races](#concurrent-privileged-event-races)).

For a chain in Divergent state (`Ixn`-`Ixn` on KEL or SEL): events at-or-below `lastSealAdvancingEvent` keep their trust grounding per [§Pre-seal verifiability](#pre-seal-verifiability). Above-seal events on the divergent branches are flagged as untrusted in the verifier's output but stay in storage. The state resolves via recovery / repair (KEL and SEL `Rpr`): the chain returns to Active with the discriminator-archived branch removed from live storage, and the `Rpr` itself advances the seal forward.

<a id="limit-of-the-doctrine"></a>

#### Limit of the doctrine — current-state compromise

The doctrine closes attacks rooted in **past** state. It does NOT defend against compromise of **current** state.

If an adversary acquires sufficient (privileged) currently-controlling authority — current KEL rotation or rotation+recovery preimages; current IEL `governance` threshold; current SEL identity binding's authorizing IEL event — they ARE the chain's current state by every protocol-observable measure. They can:

- Submit governance-authorized events (KEL `Rot` / `Ror` / `Fed`, IEL `Evl`, SEL `Evl`) that legitimately rotate authority away from the prior operator.
- Subsequently submit `Dec` (or any other governance act) under the new authority.
- Lock the legitimate prior operator out of all protocol-level recourse.

There is no protocol mechanism to distinguish "legitimately current" from "compromise-acquired-current." There is a narrow detect-and-respond window before the rotation lands: if the legitimate operator detects compromise and acts under the still-current pre-rotation authority before the adversary's rotation event lands, the legitimate event wins. After the rotation, no protocol-level recourse remains.

##### Defense in Depth

Defense for current-state compromise is **layered**, not single-mechanism. The layers compose; no one of them is load-bearing on its own.

- **KEL dual-signature on `Rpr` / `Ror` / `Fed` / `Dec`** blocks signing- and rotation-key compromise — exfiltration, brute force, coerced signing, side channels — regardless of where the recovery key is custodied. A single-device deployment is first-class for threat models where signing-tier compromise wouldn't also expose the recovery key.
- **IEL policy composition** (high thresholds, `M > N` redundancy across distinct custodians) handles total device compromise: burn the device, rotate it out via `Evl`. The surviving members continue to satisfy the threshold; the prefix stays alive.
- **KEL-internal custody separation** (recovery key on a different device, HSM, ceremony-gated) is an optional deployment hardening for threat shapes where signing and recovery would otherwise fall together (coerced signing especially).
- **Federation witnessing** closes the partition-attack surface and the no-partition rotation-tier compromise surface structurally: under always-witness, competing privileged events at the same chain position route to the same witness set, both branches accumulate receipts from the full pool, and threshold-two-events makes the federation-level disagreement observable in the data layer (see [`federation/witnessing.md`](federation/witnessing.md)). The rotation-tier compromise PLUS federation-partition case is the structurally unavoidable CAP failure mode — VDTI guarantees the divergence is **detectable** post-resolution rather than preventing it.
- **Monitoring** for unexpected governance / rotation events — fire alerts before adversary completes rotation.
- **Fast operator response** — cut the detect-to-respond latency to within the gossip window.
- **Threshold redundancy** (`M > N`) — re-anchor via a different threshold-satisfying subset when one identity is disrupted.
- **Abandon-and-reincept** under a new prefix when current-state compromise is suspected and no ratchet-out path exists.

The trade the protocol makes is intentional: a narrow current-state-compromise vulnerability (high-friction, time-bounded, operationally mitigable) in exchange for closing the much broader past-state kill-switch surface (low-friction, time-unbounded, structurally unmitigable without this doctrine).

##### Rotation-tier adversary federation-non-convergence path

Two compromise paths produce federation-level non-convergence — both are bounded by [§Pre-seal verifiability](#pre-seal-verifiability) and surfaced via divergent witness receipts at the federation layer ([`federation/witnessing.md`](federation/witnessing.md)).

**Tier-2 path.** An adversary holding the rotation-key preimage — and only the rotation-key preimage — can forge `Rot` events (single-signed by the new signing key the preimage reveals; the old signing key is not a prerequisite). Racing `Rot_adv` against an honest concurrent `Rot_op` / `Ror_op` on different federation nodes produces cross-node non-convergence: each `Rot` lands as a clean linear-chain extension on its submitting node and advances the local seal; gossip delivers each to the other node where the seal-cap rejects the late arrival. The forging bar is rotation-tier compromise (one preimage), strictly easier than the full tier-3 compromise required to forge `Ror` / `Rpr` / `Fed` / `Dec`.

**Tier-3 path.** An adversary holding both the rotation-key preimage AND the recovery-key preimage can forge any recovery-revealing event (`Ror` / `Rpr` / `Fed` / `Dec`) — dual-signed by the new signing key the rotation preimage reveals and the recovery key the recovery preimage reveals (the old signing key is not a prerequisite). Racing those events against operator submissions on different federation nodes produces the same cross-node non-convergence shape: each event lands cleanly on its submitting node and advances the local seal; gossip-arriving competing event is rejected by the seal-cap. No in-band protocol recourse exists once an adversary's recovery-revealing event has landed on any node.

**Bounded damage.** Anchors, credentials, and SEL bindings at-or-below each node's `lastSealAdvancingEvent` retain structural verifiability regardless of which side of the race that node accepted, per [§Pre-seal verifiability](#pre-seal-verifiability). A tier-2 adversary extending with tier-1 `Ixn`s between the last seal and the rotation race, or a tier-3 adversary extending under fresh post-rotation key state, pollutes the above-seal range; those events are not structurally trustworthy under the seal-bound rule.

**Federation witnessing closure (no-partition).** Under always-witness, competing privileged events at the same chain position both accumulate receipts from the full witness pool. Threshold-two-events fires from receipts alone on every node; consumers see the prefix as federation-irreconcilable and refuse to bind. Adversary cannot force a fork to ratify under no-partition conditions. Operator recourse is reincept.

**Federation witnessing under partition.** The stronger combined attack — rotation-tier compromise PLUS adversary-controlled federation partition — is the structurally unavoidable CAP failure mode. VDTI chooses detect-after-the-fact: receipts are indexed at chain position rather than at event SAID, so when gossip resolves the partition the competing receipts land in the same row group on each node, threshold-two-events fires, and the divergence becomes structurally observable in the data layer.

##### Adversary Patience and Policy Redundancy

The detect-and-respond window above assumes the adversary acts as soon as they hold sufficient authority. A strategic adversary doesn't. They accumulate — compromise key 1, wait, compromise key 2, wait, compromise key 3, then act once they hold a satisfying combination of the current policy. The window the operator has to respond is bounded by the adversary's timeline (when they choose to act), not by the operator's observation (when they detect the first compromise). Compromise detection at the per-key level may produce no protocol-observable signal until the adversary's accumulation completes; by then the rotation event is already authorized to land.

This makes policy design a budget against strategic patience, not a checkbox:

- **High thresholds + custody separation** raise the cost of accumulating sufficient authority. Each additional independently-held key in the policy is an additional independent compromise the adversary must accomplish. Geographic, organizational, and supply-chain separation between key custodians multiplies the cost of accumulation.
- **Threshold redundancy** (an N-of-M threshold with `M > N`) tolerates loss of `M − N` identities. The operator who detects partial compromise of a subset ratchets-out the compromised members via `Evl` (declaring a new policy that excludes them); the chain remains under operator authority.
- **Hierarchical scope partitioning** (a root identity governs a fleet of subordinate identities; each subordinate anchors a narrower scope) bounds the blast radius. A compromise at a leaf doesn't compromise the root or its siblings; the operator's response is scoped to the affected leaf.

The operational stakes for getting policy design wrong are concrete. A chain whose policy permits no ratchet-out path — e.g., an N-of-N threshold (a unanimous policy with no redundancy beyond the threshold) — loses to the first compromise that hits the threshold. The recourse is reincept under a new prefix, which propagates to every consumer of the identity: every service config, every anchor allowlist, every KEL-backed binding, every peer registry needs to be updated to the new prefix. At federation scale this is a coordinated, expensive rollout. Every consumer is touched; coordination across operators (especially across organizational boundaries) introduces wall-clock delays measured in days or weeks.

Policies designed for ratchet-out — high thresholds, redundancy beyond the threshold, hierarchical scope partitioning — keep the prefix stable across compromise events. **Survivable compromise instead of catastrophic reincept.** Design policies to survive compromise without reincept; treat reincept as the option of last resort, not the routine response.

The principle applies uniformly across KEL, IEL, and SEL. **KEL** uses the dual-signature requirement on `Rpr` / `Ror` / `Fed` / `Dec` to block signing / rotation-key compromise regardless of where the recovery key is custodied — a single-device deployment is first-class for threat models where signing-tier compromise wouldn't also expose the recovery key. Custody separation is an optional deployment hardening for threat shapes where signing and recovery would otherwise fall together (coerced signing especially). **IEL** uses `M > N` thresholds across distinct custodians plus hierarchical scope partitioning (root IEL → subordinate IELs scoped narrowly) to handle total device compromise — surviving members rotate the compromised device out via `Evl` without losing the identity. **SEL** inherits both via its IEL binding — a well-designed IEL governance policy is the SEL's main defense against adversary patience. The choice between KEL-internal custody separation and IEL multi-device composition depends on the application's threat shape and operational model; the protocol supports either, and both can be combined.

##### Cascade-reincept honesty

Reincept is needed when forward extension on a chain is structurally blocked — typically when the federation has surfaced the chain as federation-irreconcilable via divergent witness receipts (see [§Limit of the doctrine — concurrent privileged event races](#concurrent-privileged-event-races)) and the operator cannot proceed without a fresh prefix. Dependent chains whose bindings reach at-or-below-seal state on the disrupted chain stay authorized; only forward extensions that would bind against above-seal state face the freeze.

- **IEL disrupted at the federation layer.** SELs whose binding sits on at-or-below-seal IEL state (`bound_event.serial <= bound_iel.lastSealAdvancingEvent.serial` per the `IelDivergent` rule) stay trust-evaluable. SELs that would forward-extend their binding against the IEL by issuing a new `Est` or `Evl` whose `policyPin` references an above-seal IEL event cannot, and require reincept under a new IEL prefix.
- **SEL disrupted at the federation layer.** At-or-below-seal content stays verifiable; the disruption doesn't cascade beyond the SEL itself.
- **KEL disrupted at the federation layer.** At-or-below-seal anchors retain validity, and dependent IEL / SEL events whose authorization traced through those anchors continue to return `policy_satisfied = true`. For forward evaluations that would have relied on a fresh anchor from the disrupted KEL, whether the dependent IEL / SEL event still evaluates as satisfied depends on whether the resolving policy has threshold redundancy that lets it satisfy without the disrupted KEL's contribution. Policies with `M > N` threshold redundancy across distinct custodians absorb a single member's disruption — past at-or-below-seal anchored events stay satisfied via the surviving members' contributions, and the forward response is governance evolution (`Evl`) to rotate the disrupted KEL out of the policy. No IEL reincept needed.

The expensive case is federation-level disruption of an **IEL at the root of a dependency tree**: the freeze on forward extension cascades transitively to every SEL (and credential issuance, anchor allowlist, peer registry, etc.) bound to it that would have extended forward. **Don't put your entire dependent tree under a single root IEL.** Identity hierarchies should be designed with cascade in mind — partition the dependency graph so any single IEL's disruption has a bounded blast radius.

##### Shape constraints on SEL Evl

- Parent cannot be `Icp` — `Evl` is meaningful only after a binding-establishing event has landed; SEL `Evl` after `Icp` would re-anchor an IEL binding that hasn't yet been declared.
- Parent cannot be `Dec` — terminal events do not extend.
- **SEL Evl-Evl change rule.** A **consecutive** `Evl` — directly following another `Est` / `Evl`, no `Ixn` between — must change ≥1 of {`governance`, `operation`, `policyPin`}; a no-op consecutive `Evl` is rejected. The pin **ratchets forward along the per-chain floor** — every slot sits at-or-above its referenced chain's running floor (see [§Per-Chain Forward-Only Floor (SEL-specific)](#per-chain-forward-only-floor-sel-specific)); when the pin is the field changing, ≥1 slot advances. A governance/operation-only `Evl` re-stating `policyPin` equal is legal. An `Evl` that instead follows **≥1 `Ixn`** is a **seal checkpoint**: it advances the seal to hold the chain under the `MINIMUM_PAGE_SIZE − 2` cap (bounding the repair operator) and **may re-state the prior tracked state unchanged** — the change-≥1 requirement is scoped to consecutive `Evl`s, where there is no `Ixn` accumulation and thus no seal-cap pressure that would force a no-change event.

---

## Part 2: Cross-Cutting Doctrines

Properties that hold across all primitives and bind them into a coherent protocol. These are not security invariants in the narrow sense — they constrain how the protocol composes (across nodes, across event kinds, across time) rather than asserting an authorization rule. Doctrine rules in Part 1 lean on these for their cryptographic-soundness argument.

### Ordering Without Timestamps

VDTI chain events (KEL, IEL, SEL) carry no wall-clock timestamp field. Ordering is by serial number + cryptographic chain linkage (`previous` SAID).

#### Why no event-level timestamps

Wall-clock timestamps on chain events would not be cryptographically meaningful for ordering or tiebreaking:

- An event author can write any timestamp they choose. The protocol can only verify that an event was *observed* at-or-before "now"; it cannot verify the event was crafted when its timestamp claims.
- Clock drift across federation nodes precludes timestamps as a reliable cross-node ordering signal. Different nodes' clocks may disagree; relying on them for "who was first" would let drift, not data, decide chain outcomes.
- Cryptographically verifiable ordering already exists via serial numbers and `previous` SAID linkage. Adding wall-clock timestamps to chain events would be redundant for ordering and unsound for tiebreaking — it would introduce an untrusted input as a protocol decision input.

Where timestamps DO appear in VDTI, they serve narrow roles within a **single party's reference frame**, not chain ordering or cross-node consensus:

- **Peer-to-peer signed requests** carry a Unix timestamp + nonce; the receiving party verifies the timestamp against its own clock within a 60-second window and deduplicates via the nonce cache.
- **Exchange envelopes** carry `createdAt` and a per-envelope `nonce`; recipients evaluate freshness against their own clock at decryption time.
- **Mail nonce expiry** evicts cache entries older than a configured window.

In each case the timestamp is consumed by a single party using its own clock — drift across the federation doesn't affect correctness. None of these timestamps appear in chain events, and none influence chain ordering.

#### Application-layer time-of-creation evidence

Applications building on VDTI may need time-of-creation evidence (audit trails, regulatory reporting, claim validity windows). The recommended pattern is to carry timestamps as application-layer fields on the *content* a chain event anchors, not on the chain event itself.

- **Credentials** carry `issuedAt` (required) and `expiresAt` (optional). The verifier checks `expiresAt` against its own clock at verification time.
- **Exchange envelopes** carry `createdAt`.

For applications that need third-party-attested timestamps (e.g., legal contexts where a notary's stamp is required), the right pattern is an external attestation: a notary signs `(content_said, timestamp)` as a separate object, which the application carries alongside the content. The VDTI chain still anchors the content SAID; the notary's stamp lives in application metadata.

### Federation Convergence

VDTI depends on **eventual cross-node convergence**: gossip propagation, paired with deterministic effective-SAID computation, ensures every chain resolves to the same semantic state on every node in a healthy federation when convergence is possible at the protocol layer. Where the protocol layer cannot converge — concurrent privileged event races between nodes — divergent witness receipts at the federation layer surface the disagreement uniformly (see [§Limit of the doctrine — concurrent privileged event races](#concurrent-privileged-event-races) and [`federation/witnessing.md`](federation/witnessing.md)).

The convergence model has three components:

- **Gossip propagates events.** Anti-entropy and submission-time fan-out push new events to all nodes within a bounded propagation window. (The bound itself is operational; the doctrine asserts only the eventual property.)
- **Semantic state is a function of the events.** Each node's view of a chain (Active / Divergent / Decommissioned, with which events at which serials) is computed deterministically from the events that node holds; identical event sets yield identical state.
- **Effective-SAID determinism on divergent and federation-irreconcilable chains.** Where chain contents may differ across nodes (different surviving fork events on a divergent chain, or federation-layer disagreement surfacing the prefix as federation-irreconcilable), `hash_effective_said` computes a deterministic SAID that depends only on `(state, prefix)`, not on byte-identical content. Anti-entropy compares effective SAIDs to recognize matching state across nodes uniformly; protocol-layer reconciliation handles divergent chains via `Rpr`, while divergent witness receipts at the federation layer hold the source-of-truth for prefixes the protocol layer cannot reconcile (see [§Effective-SAID synthetic comparison](#effective-said-synthetic-comparison) and [`federation/witnessing.md`](federation/witnessing.md)).

For cross-node disagreement that the protocol layer cannot resolve — priv-vs-priv races, priv-vs-non-priv state mismatches, divergent vs Decommissioned — divergent witness receipts record signed attestations of per-node observation, surface the disagreement to operators for out-of-band reconciliation, and provide the canonical "is this chain in dispute?" answer for consumers.

Doctrine rules that lean on convergence as their cryptographic-soundness argument:

- **End-verifiability over data-from-any-source** — the verifier produces the same answer because the data is semantically the same (or effective-SAID-identical) across nodes for chains that converge at the protocol layer.
- **Single-node-compromise mitigation** — depends on cross-node replication surfacing tampering as divergence (at the protocol layer) or as federation-layer disagreement via divergent witness receipts.

Convergence — at the protocol layer where possible, at the federation layer otherwise — is the load-bearing assumption that makes the protocol's cryptographic invariants behave equivalently from any node a consumer queries. **Single-node deployments forfeit this property** — they trade convergence-via-replication for operational simplicity, and accept the structural weakening of DB-tampering surfacing.

Convergence is among gossip-participating nodes. **Permanent node loss before propagation completes** (a node going offline while it still holds events not yet seen by other peers) is a deployment-shape concern — replication factor, node uptime, backup procedures, and clean retirement workflows. It is not a doctrine concern: the protocol asserts what convergence *means* and how it's computed; operators bear responsibility for keeping enough nodes online long enough for it to occur in practice.

#### Worked example: the federation IEL

The federation itself is an instance of the primitive that depends on convergence. A VDTI federation is a single IEL — the *federation IEL* — whose `governance` declares the set of member identities authorized to participate in the witness mesh. On every node, the federation IEL and the supporting member KELs are replicated to the local `vdtid` instance (which hosts both SAD storage and the chain-log acceptance rows); `witnessd` queries `vdtid` as its source of truth for federation state. Propagation uses the normal mechanics — announcement-driven primary path, dependency tracking for out-of-order arrivals, anti-entropy as fallback. The federation has no separate consensus algorithm and no central state machine.

Convergence is what makes this work:

- **Identical `governance` view across nodes.** Every node deterministically resolves the federation IEL's tip from the events it holds. If two nodes hold the same event set, they compute the same effective SAID and read the same current `governance`. Anti-entropy converges any two nodes whose effective SAIDs differ.
- **Handshake authorization is path-agnostic.** A connecting peer's identity is checked against the federation IEL's current `governance`. Two nodes that both hold the federation IEL's authentic tip produce identical authorization decisions.
- **Membership evolution converges.** A governance-authorized `Evl` event evolving `governance` propagates via the standard IEL channel. Two nodes that have both received the `Evl` see identical post-evolution policy.
- **Federation-level disagreement surfaces uniformly.** If two governance-authorized `Evl`s land concurrently on different nodes, each event lands as a clean linear extension on its submitting node and the seal-cap rejects the gossip-arriving competing event. Per-node, each chain is linear; cross-node, divergent witness receipts surface the disagreement (see [`federation/witnessing.md`](federation/witnessing.md)). The federation cannot extend the IEL further under either branch without operator-level reconciliation; the response is a fresh federation IEL inception under a new prefix. The disagreement signal converges at the federation layer; convergence is not contingent on the chain's success.

The per-peer address SEL pattern is the resolution-side companion. Each member identity owns a SEL bound to its own IEL at a deterministic prefix; each peer publishes its current network endpoints there. Discovery on any node reads the federation IEL's `governance`, enumerates the member identities, walks each peer's address SEL, and connects. Convergence applies twice: once to the federation IEL (members agree on who's authorized), once per peer's address SEL (everyone resolves the same current endpoints for each peer).

The federation IEL therefore relies on convergence for the same reason any IEL does — convergent identity state under gossip — but its operational role makes the dependency especially visible: a federation with divergent `governance` views across nodes would have nodes accepting different sets of peers as "current members," and the gossip mesh would partition along those views. The protocol's convergence guarantee, combined with the IEL primitive's structural properties, prevents that partition from ever forming under healthy gossip.

See [`federation/witnessing.md`](federation/witnessing.md) and [`federation/bootstrap.md`](federation/bootstrap.md) for the witnessing and bootstrap mechanics that ground federation operation.

### Extension Discipline

The protocol cannot — and does not — prevent any currently-authorized party from chaining a new event onto any existing chain event. `previous` validates against the structural parent (the event whose SAID is named), not against "who authored the parent." A current-authority holder can technically point `previous` at any prior event the verifier would accept as a parent.

Operator design discipline closes the implicit-endorsement gap. The discipline splits by event semantics:

#### Extend only attested events

Every chain event structurally attests to its parent — signing with `previous = parent.said` declares the predecessor acceptable as the parent state. Extending an adversary's event would be semantically equivalent to endorsing it: the new signed event chains from, and carries forward, the adversary's content.

A submitter extends only:

- **Their own previously-signed events.** Any event the submitter authored is theirs to extend.
- **Attested-shared state.** Two structural shapes:
  - **The divergence ancestor `v_{d-1}`.** On a fork, `v_{d-1}` is the unique shared parent of all events at `v_d`. Every node accepts `v_{d-1}` as authentic; extending it (e.g., a divergence-ancestor-extending `Rpr`) carries no implicit endorsement of either `v_d` branch.
  - **SEL `Icp` via dedup-equivalence.** SEL `Icp` is permissionless and deterministic — the prefix derives from `(governance, operation, topic)` and `Icp.said` derives from the full event with `said`+`prefix` blanked. Any submitter's `Icp` for the same `(governance, operation, topic)` produces the same SAID. The submitter's own `Icp` is therefore structurally indistinguishable from any other submitter's `Icp`; extending it is extending attested state, not the adversary's.

The submitter never points an event's `previous` at an adversary event. This is a construction rule applied at the builder layer — the verifier accepts any structurally-valid parent reference; the discipline closes the gap that the verifier structurally cannot.

**Adversary-extended linear chains.** If an adversary captures KEL signing-key material (or SEL `operation` material) and extends the chain linearly (`v_N`, `v_{N+1}`, …, `v_M`), the legitimate party's local chain after gossip has `v_M` as its highest-serial event. The legitimate party has no protocol move that targets `v_M` without endorsing the adversary's events — any submission extending `v_M.said` would attest to it. The structurally available moves all extend `v_{N-1}` (the legitimate party's last attested event):

- A privileged event extending `v_{N-1}` is rejected at the merge layer per [§Privileged Divergence is Terminal](#privileged-divergence-is-terminal) — it would create a divergent set containing a privileged event. The federation surfaces the conflict via divergent witness receipts.
- An archiving `Rpr` extending `v_{N-1}` is the recourse if the locked-portion bound (condition 2b) holds — i.e., the adversary's extension did not include a privileged event that advanced the seal past `v_{N-1}`. If the adversary's extension included a seal-advancing privileged event, `Rpr` extending `v_{N-1}` would violate the bound.

Practically: when the legitimate party can act under the still-current `v_{N-1}`-anchored authority, they have an archival-recovery path or a federation-level dispute path; once the adversary has rotated authority forward via a seal-advancing privileged event past `v_{N-1}`, no protocol-level recourse remains and the response is reincept.

#### Implications

- **SEL pre-Icp camping response.** When an adversary submits `[Icp, Est_camper]` first, the legitimate party's response is `[Icp, Est_operator]` with `Est_operator.previous = Icp.said` (extending `Icp` via dedup-equivalence), **not** `previous = Est_camper.said`. Pointing `Est_operator` at `Est_camper` would attest to `Est_camper`'s acceptability as a parent. `Est_operator`'s landing creates a 2-event privileged divergent set at v=1 (Est is privileged at tier 2); per [§Privileged Divergence is Terminal](#privileged-divergence-is-terminal), the merge layer rejects the second `Est` on each node — each node retains whichever `Est` arrived first locally. The federation surfaces the cross-node disagreement via divergent witness receipts. Recourse against a successful camp is reincept under a new `(governance, operation, topic)` tuple. Camping yields nothing the camper can use federation-wide: even on nodes where `Est_camper` landed first, the operator's branch is visible in the dispute record, and consumers see the prefix as federation-irreconcilable.

- **KEL / SEL divergence resolution.** `Rpr` extends either the divergence ancestor `v_{d-1}` (attested-shared; divergence-ancestor-extending shape, lands at `v_d`) or the submitter's own branch tip at `v_d` (own attestation; branch-tip-extending shape, lands at `v_{d+1}`). The repair event never points at the other branch's tip. "Whoever holds the recovery / governance key dictates which branch survives" reduces to "the submitter extends their own branch or `v_{d-1}`."

- **Privileged extension under existing divergence.** A privileged event (KEL `Rot` / `Ror` / `Fed` / `Dec`; SEL `Est` / `Evl` / `Dec`; IEL `Evl` / `Del` / `Rsc` / `Dec`) extending `v_{d-1}` on a chain that already has events at `v_d` is rejected at the merge layer. The submitter's recourse is either to extend the local tip cleanly (re-fetch + accept the existing state) or, for KEL / SEL, to issue the archiving primitive (`Rpr`) which resolves the divergence rather than creating new disagreement.

- **No event extends adversary content.** This rule is structurally absolute. Where the legitimate party can act, the structurally valid construction always extends attested state (their own or `v_{d-1}`).

#### Cross-primitive symmetry

The discipline is structurally identical across the three primitives. The shapes of "own previous tip" and "attested-shared state" instantiate differently per primitive (KEL: `v_{d-1}` and own-branch tips; IEL: `v_{d-1}` only — every event is governance-authorized so there are no auth-only operator-extension paths; SEL: `v_{d-1}`, `Icp` via dedup, and own-branch tips), but the underlying principle — submitters attest only to their own content or to genuinely shared state, with termination events following the structural parent rule unconditionally — applies without primitive-specific exception.

---

## Part 3: Verification Mechanics

The implementation invariants that make Part 1's security invariants enforceable. Verification tokens, advisory locks, federation-witness composition, and inline reference checking are the patterns by which "the database cannot be trusted" gets converted into safe operations — verification and use happen in the same pass, under the same lock, against the same trusted context.

### Verification tokens as proof of verification

Functions that consume chain data accept a verification token (`&KelVerification`, `&IelVerification`, `&SelVerification`) as a parameter. Holding the token proves the corresponding chain was verified. Token fields are private with no public constructor — the only way to obtain one is through the corresponding verifier (`KelVerifier`, `IelVerifier`, `SelVerifier`).

Each token exposes (in addition to per-primitive specifics):

- `policy_satisfied: bool` — monotonic-falsy aggregate signal (see [§policy_satisfied](#policy_satisfied)).
- `witnessed: bool` — the per-event query: does this event have threshold receipts under a consistent federation state? See [§Federation witnessing in verification](#federation-witnessing-in-verification).
- `divergent: bool` — federation-layer divergence at the queried chain position (carries the competing event SAIDs when true).
- `minority_dissent` — receipts below threshold for some `witnessedSaid` that don't contribute to pinning; forensic signal for potentially-compromised members.
- `witnessed_anchors` (KEL token) — set of KEL anchor SAIDs that are witnessed on the canonical branch, consulted by IEL / SEL during anchor-tier policy resolution.

### Streaming

Chain verification streams events page by page rather than loading entire chains into memory. The pattern applies uniformly across KEL, IEL, and SEL; each primitive has parallel types — `{Kel,Iel,Sel}Verifier` for the walk, `{Kel,Iel,Sel}Verification` for the proof-of-verification token, and a primitive-specific `PageLoader` trait abstracting the storage backend.

The verifier walks events in **generations** (all events at a given serial), tracking per-branch state; divergence forks per-branch state. `completed_verification(loader, prefix, page_size, max_pages, ...)` is the paginated helper — it drives the loader and calls `truncate_incomplete_generation()` at each page boundary so a generation whose events span two pages re-fetches on the next page rather than being processed half-observed. The helper returns the trusted verification token; `max_pages` caps resource use.

### Merge Verification

When merging new events into an existing chain (submit handler), first verify the entire existing chain in the DB using the corresponding verifier with paginated reads under an advisory lock. Obtain a trusted verification token from the verifier and use that token's data as the context for verifying the new incoming events — never re-query the DB between verification and use. The pattern applies uniformly across KEL, IEL, and SEL submit paths.

### Inline reference checking

Each verifier supports registering SAIDs of interest before the walk so the walk records what it observed without separate DB queries. KEL registers anchor SAIDs (KEL `Ixn`s observed at IEL / SEL Icp time and similar binding points); IEL and SEL register caller-cared-about SAIDs for satisfaction tracking. Registration happens before the walk; results are available on the verification token. The pattern eliminates a second DB pass for SAID-presence questions.

### Verifier and merge are distinct treatments

The verifier and the merge layer share infrastructure — the same verifier walk produces the same `policy_satisfied` signal — but compose it differently.

- **Verifier (reads).** Walks already-landed events and reports trust state on a verification token. Authorization failures above the seal are **soft**: they flip `policy_satisfied = false` and the walk continues. The verifier's purpose is to walk authentic chain data and surface findings; erroring out on a chain that contains divergence or governance-failed events would prevent callers from reading the chain at all, including the at-or-below-seal portion they need for forensic and trust-evaluation purposes. Hard-fail is reserved for structural-integrity violations (SAID mismatch, prefix mismatch, broken chain linkage); chain validity stays separable from policy satisfaction.
- **Merge layer (gates writes).** The submit handler runs the same verifier under an advisory lock and uses the resulting `policy_satisfied` as a gate on the new batch: if false at the post-batch walk, the submission is rejected and the new events never enter storage. Failed governance → no write. The gate applies uniformly across event kinds — `Ixn` extension, `Evl` / `Rpr` / `Ror` / `Fed`, and `Dec` alike — with no per-kind carve-outs.

One signal, two compositions: the verifier reads through pathology to expose it, the merge layer reads `policy_satisfied` to gate against it. The signal's definition and walk-time pathology list are in [§policy_satisfied](#policy_satisfied) immediately below; the merge-layer hard-auth invariant for repair events is in [§Privileged Divergence is Terminal §Repair-event authorization](#privileged-divergence-is-terminal).

### policy_satisfied

The verifier produces a `policy_satisfied: bool` on its verification token. Definition: `policy_satisfied = true` iff no walk-time pathology has been observed during the walk. The flag is **monotonic-falsy**: once flipped false, it stays false for the rest of the walk's reporting.

On a non-divergent chain, all queried SAIDs anchored at-or-below `lastSealAdvancingEvent` are recorded in `satisfied_saids`; SAIDs above the seal stay in storage but are not recorded as satisfied unless and until a subsequent seal-advancing event seals them. On a divergent chain, only SAIDs observed at-or-below `lastSealAdvancingEvent` on the pre-divergence linear portion are recorded; once recorded, those entries are not retroactively invalidated by later pathology.

Walk-time pathologies that flip `policy_satisfied = false`:

- Divergence at or before the SAID's anchor observation (post-divergence anchoring).
- Governance / anchor check failures (inception self-governance soft-fail, `Dec` governance soft-fail, post-divergence `Evl` soft-fail).
- Missing SAD-object dependencies in collect-mode walks.
- Other structural anomalies observed during the walk.

The locked-portion doctrine (see [§Privileged Divergence is Terminal §Repair-event conditions](#privileged-divergence-is-terminal)) means settled events — those whose anchors fell in a clean walk segment, in the locked portion — are immune to subsequent chain pathology. Once `policy_satisfied` is true for a SAID in the locked portion, it stays true regardless of subsequent chain events.

**Merge-layer composition.** A submission whose `policy_satisfied` is false at the post-batch verifier walk is rejected with 403 Forbidden. The new events would not anchor under the agreed-upon (clean walk segment, locked portion) chain interpretation. This is the gate that hard-fails governance-failed `Dec` submissions: the merge layer applies the same `policy_satisfied` check across all event kinds (including `Dec` / `Rpr` / `Fed`), without per-kind carve-outs.

### Federation witnessing in verification

Federation witnessing surfaces in verification two ways: as the witnessed / divergent / minority_dissent signals on the per-primitive verification token, and as the `witnessed_anchors` set that IEL / SEL anchor-tier resolution consults on KEL. The full mechanics — receipt SAD shape, witness selection, placement rule, threshold-two-events divergence detection — live in [`federation/witnessing.md`](federation/witnessing.md); the rules this section names are what the verifier enforces.

**Always-witness; reporter, not decider.** A federation member acting as a witness signs a receipt for **every structurally-valid event** they observe at any chain position they're sort-selected for, regardless of whether they've already signed for a competing event at the same position. Witnesses do not pick a canonical event among competing options; they attest "I verified this event's chain is structurally valid and I observed it." This makes the federation's witness state **locally determinable**: a single node holding the receipts can determine the federation's state from data alone, without consulting watcher infrastructure.

**Threshold-two-events divergence detection.** A chain position `(prefix, serial)` is **federation-divergent** iff two or more distinct `witnessedSaid` values each have ≥ threshold receipts AND each `witnessedSaid` resolves to a structurally-valid event. The receipt count alone is not sufficient — the verifier independently re-checks structural validity of every `witnessedSaid` referenced in the adjacent receipt table (DB-cannot-be-trusted). Single-rogue protection: a rogue who signs receipts on a fake `witnessedSaid` cannot trigger divergence — the fake event fails structural re-check; honest witnesses don't sign for fakes. Threshold-many colluding rogues can only produce threshold-many receipts on a fake; the structural re-check rejects the fake. Both sides must reach threshold AND both events must be structurally valid for divergence to fire.

**Acceptance gating for non-witnesses.** A federation node that is **not** sort-selected as a witness for event `E` MUST NOT accept `E` into the chain's live state until `E` has accumulated threshold receipts. Witness nodes accept `E` upon their own signing (direct evidence of structural validity and self-attestation). Non-witnesses hold `E` in deferred-pending state until receipts arrive via witness gossip.

**Inheritance via anchor walk.** IEL and SEL events do not carry a federation context field; they inherit federation context via their KEL anchors. KEL is the leaf of trust composition. Each IEL / SEL leaf-anchor check resolves to a KEL event, which carries the federation context declared in the most-recent `Icp` / `Fed` at-or-before that anchor's serial. The IEL / SEL verifier consults the KEL token's `witnessed_anchors` set during policy satisfaction — only witnessed anchors count toward threshold.

**Trust composition through trusted federation `Fcp` SAIDs.** For each event the verifier walks the chain's current federation context back to the federation IEL's `Fcp`. If the `Fcp` SAID is in the verifier's trusted set (compile-time-baked + runtime override), the federation is trusted for that event. Multi-federation chains (KELs that have transferred federations via `Fed` events) require each federation in the chain's history to be independently in the verifier's trusted set — no transitive trust. See [`federation/bootstrap.md`](federation/bootstrap.md).

**Federation IEL self-signing carve-out.** The federation IEL itself is witnessed under self-signing semantics at v=0, dispatched by IEL kind. At `Fcp` (v=0), the witness pool is the `Fcp` event's own `governance` policy's DSL expansion to leaf prefixes (the founder identity IEL prefixes). At v > 0 (`Evl` / `Dec`), the standard rule applies (pool = the prior-state `governance` expansion). The kind discriminator makes the self-attesting case structurally explicit. Identity IELs (and other non-federation IELs) use `Icp` at v=0 and are witnessed under their parent KEL's federation — the kind discriminator tells the verifier which rule to apply.

Consumers refuse to bind under `divergent = true` (federation cannot agree at this position) or `witnessed = false` (insufficient attestation), and consult the trusted federation `Fcp` SAID set as the trust ground. Anchors at serials strictly below the divergent serial remain canonical (see [§Pre-seal verifiability](#pre-seal-verifiability)).

### Advisory Locking

All verify-then-write paths hold PostgreSQL advisory locks for the duration of both verification and write. Per-primitive locked-transaction types implement the corresponding `PageLoader` trait by reading under the advisory lock; the same transaction is then used for the write. This eliminates time-of-check-to-time-of-use vulnerabilities. Applies uniformly across KEL, IEL, and SEL submit paths.

### Effective-SAID synthetic comparison

The effective SAID is the canonical chain-tip representation across KEL, IEL, and SEL. It identifies the chain's current state and lets nodes recognize that state across the network without exchanging chain data.

**Concrete vs synthetic representations.** Normal-tip chains carry the tip event's real SAID as the effective SAID; decommissioned chains (where `Dec` is the terminal tip — applies on KEL, SEL, and IEL) carry the `Dec` event's real SAID. Two states have synthetic representations:

- `hash_effective_said("divergent:{prefix}")` — chain has competing branches at some serial (a divergent set; recoverable via `Rpr`). Applies on KEL and SEL; IEL has no Divergent state (every IEL event is privileged, so divergent sets cannot form locally).
- `hash_effective_said("irreconcilable:{prefix}")` — prefix is surfaced as in-dispute at the federation layer via **divergent witness receipts** in the adjacent receipt tables (see [§Limit of the doctrine — concurrent privileged event races](#concurrent-privileged-event-races) and [`federation/witnessing.md`](federation/witnessing.md)). Source-of-truth lives at the federation layer; the per-node chain state remains Active / Divergent / Decommissioned. The service returns this synthetic in chain-query responses when it knows the prefix is federation-irreconcilable. Applies uniformly on KEL, SEL, and IEL.

The synthetics depend only on `(state, prefix)` — no chain history, no fork point, no serial. Any node observing or computing the effective SAID can recognize the state from the SAID alone.

**Cross-node coordination primitive.** Effective SAIDs travel on the wire — gossip announcements, storage-layer responses, `/effective-said` endpoints. Two nodes whose chain `P` is divergent (perhaps at different fork points) compute and exchange the same `hash_effective_said("divergent:P")`; two nodes whose chain `P` is in federation-layer dispute compute and exchange the same `hash_effective_said("irreconcilable:P")`. This is what lets nodes recognize each other's state without exchanging the chains themselves. Encoding fork-point or serial into the synthetic would break this — two nodes couldn't recognize each other's state if their representations differed.

**State-detection algorithm.** Given an observed effective SAID for prefix `P`, a node tests:

1. `observed == hash_effective_said("divergent:{P}")` → chain is divergent (recoverable via `Rpr`).
2. `observed == hash_effective_said("irreconcilable:{P}")` → prefix is federation-irreconcilable (sourced from divergent witness receipts).
3. Otherwise → chain has a real tip event SAID; the tip may be a normal extension event or a `Dec` (use per-event lookup to disambiguate).

A node observing an effective SAID for a prefix it has no local state for can still compute either synthetic: the function is `(state, prefix) → SAID` with no chain-history input. This is what lets a peer recognize "your chain `P` is divergent" or "your prefix `P` is federation-irreconcilable" purely from the observed SAID, even on first contact.

Federation-level irreconcilability — cross-node disagreement on which privileged event a chain accepted — is surfaced both via divergent witness receipts at the federation layer and as the per-primitive synthetic effective SAID `hash_effective_said("irreconcilable:{prefix}")` returned by the service in chain-query responses. The federation layer holds the source-of-truth for "is this prefix in dispute?"; the per-primitive synthetic is the wire-format surface that lets consumers recognize the disputed state from a single SAID.

**Why divergence resolution doesn't need fork-point detail.** Differently-divergent chains across nodes are resolved through local `Rpr` (archiving repair). Cross-node sync of differently-divergent chains is intentionally not attempted — chains that can't be replayed deterministically must be resolved locally. The synthetic abstraction's prefix-only shape aligns with this design choice: a node receiving a divergent-effective-SAID from a peer learns "peer's chain is divergent" but cannot (and should not try to) reconcile against its own divergent state.
