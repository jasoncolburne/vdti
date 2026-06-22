# Protocol Doctrine

The structural rules that govern VDTI — security invariants, cross-cutting doctrines, and
verification mechanics. Each part below is load-bearing for protocol correctness; per-primitive
design docs cross-reference these as the upstream source rather than re-deriving them.

Read [`system-thesis.md`](system-thesis.md) first. The thesis is the framing — adversarial-first
posture, end-verifiability over data-from-any-source, fail-secure default — and points back here
for the structural rules that realize those properties.

**[Part 1 — Security Invariants](#part-1-security-invariants):**
- [Terminology](#terminology) — locked portion, per-node chain states, cross-chain anchor satisfaction.
- [Operation categories](#operation-categories) — serving, consuming, resolving.
- [Compromise is permanent](#compromise-is-permanent) — authority belongs to current state only.
  - [Pin everything to current, floored per chain](#pin-everything-to-current-floored-per-chain)
  - [Tiers](#tiers) — the three-tier capability model
  - [Structural authorization](#structural-authorization) — no policy on chain events
  - [Forks are seal-bounded](#forks-are-seal-bounded)
  - [Divergence and repair](#divergence-and-repair)
  - [Kills are sealed; validity cut-offs are contiguous](#kills-are-sealed-validity-cut-offs-are-contiguous)
  - [Inception tiers](#inception-tiers)
  - [Decommission and clean retirement](#decommission-and-clean-retirement)
  - [Limit of the doctrine — current-state compromise](#limit-of-the-doctrine--current-state-compromise)

**[Part 2 — Cross-Cutting Doctrines](#part-2-cross-cutting-doctrines):**
- [Ordering without timestamps](#ordering-without-timestamps)
- [Federation convergence](#federation-convergence)
- [Extension discipline](#extension-discipline)

**[Part 3 — Verification Mechanics](#part-3-verification-mechanics):**
- [Verification tokens as proof of verification](#verification-tokens-as-proof-of-verification)
- [Walk semantics](#walk-semantics)
- [Structural problems error; everything else is reported](#structural-problems-error-everything-else-is-reported)
- [Negative checks are positive lookups](#negative-checks-are-positive-lookups)
- [Merge verification and advisory locking](#merge-verification-and-advisory-locking)
- [Federation witnessing in verification](#federation-witnessing-in-verification)
- [Effective-SAID synthetic comparison](#effective-said-synthetic-comparison)

---

## Part 1: Security Invariants

The invariants below are load-bearing for VDTI security. They are stated structurally rather than
statistically: the protocol's safety claims hold *by construction*, not by observation. Verifier
implementations enforce them on every walk; an event or chain state that violates them is rejected
regardless of source.

### Terminology

Structural concepts referenced throughout. Distinct senses; not interchangeable.

- **Locked**: the portion of a chain before its most recent privileged event. **Within-chain
  rule** — locked events are structurally immutable within their own chain: a repair cannot target
  them, and within-chain historical authorizations are not retroactively unsatisfiable. The
  privileged event ratchets the lock forward.
- **Chain states** (per-node — a chain is in exactly one):
  - **Active** — linear chain; accepts linear extension.
  - **Divergent** — two **distinct** events at the same serial. The chain is **frozen**: it accepts
    no new event of any kind until a repair resolves it (see [§Divergence and
    repair](#divergence-and-repair)). Resolvable to Active when the divergent set is repairable.
  - **Decommissioned** — a terminal `Dec` has landed cleanly. Fully terminal: accepts no submission.
- **Federation-irreconcilable**: cross-node disagreement on which event a chain accepted at a given
  serial — surfaced at the federation layer via **divergent witness receipts** (see
  [`federation/`](federation/)). It is a federation-layer property, not a per-node chain state; the
  per-node states stay Active / Divergent / Decommissioned. A prefix becomes federation-irreconcilable
  at-and-beyond its divergent serial; events strictly below it stay canonical.
- **Cross-chain anchor satisfaction**: whether a document's or upper-layer event's authorization
  still holds is checked against its contributing lower-layer anchors. How a contributing anchor
  becomes non-canonical depends on its **tier**: a tier-1 (`Ixn`) anchor (archivable) drops when a
  later repair archives its host; a tier-2/3 anchor (on a seal-advancing event, durable against
  repair) drops only when its host chain surfaces **federation-irreconcilable** at-or-beyond the
  divergent serial. Either way the lower-layer verifier reports the SAID as not-anchored on the
  canonical branch, and the dependent answer flips to unsatisfied. Distinct from within-chain state
  — locked events stay locked within their own chains; cross-chain satisfaction is handled by
  composition redundancy (anchor count above the exact threshold).

### Operation Categories

The database cannot be trusted — it may have been altered. All operations on chain data fall into
three categories:

1. **Serving** — returning data to a client or peer. **No verification needed**; the receiver
   verifies what they get. (`GET` endpoints, effective-SAID lookups, paginated reads.)
2. **Consuming** — using data for a security decision (anchoring, key extraction, divergence
   routing, merge). **MUST verify the full chain first.** The only way to reach consumed data is
   through that primitive's **verification token** (`KelVerification` / `IelVerification` /
   `SelVerification`), obtainable only via the verifier — so verification and access happen in the
   same pass, eliminating time-of-check-to-time-of-use gaps.
3. **Resolving** — comparing state to decide whether to sync. A wrong answer triggers an
   unnecessary sync (which itself verifies), not a security hole; standalone functions are
   acceptable here. (Effective-SAID comparison, anti-entropy, proactive-rotation prechecks.)

### Compromise is Permanent

The protocol grants authority **only to a chain's current state** (and its most-recent shared
pre-divergence state, where divergence has occurred). Past keys, past members, past delegators —
anything rotated, evicted, or revoked out — has zero structural ability to act. Per primitive:

- **KEL** — a signing or rotation key compromised in the past cannot extend the chain today, even
  if the adversary still holds the key material. A new event requires the **current** key.
- **IEL** — a member evicted via a `Gov` cannot land further acts after their eviction.
- **SEL** — a SEL pins **up** to its owner IEL's current tip; a rotated-out party of that IEL has
  no authority over it.

This closes the **stale-state kill-switch problem**: without it, everyone who ever held authority
over a chain would retain a permanent kill switch. The structural mechanisms that enforce it are
the per-chain forward floor, the seal bound, the tier model, and fresh-participation — below.

#### Pin everything to current, floored per chain

Every event pins its dependencies' **current tips**, and a per-chain **forward-only floor** keeps
those pins from regressing. The floor lives on the chain doing the pinning (intra-chain — there is
no cross-chain clock for ordering). Two distinct backdate mechanisms are closed, and they are kept
separate:

- **Fresh participation closes the deep-member backdate.** A member participates in an IEL event by
  authoring a **fresh KEL event at its own current tip** that commits to that specific IEL event
  (`Ixn → IEL Ixn`, `Rot → IEL Gov`), signed by its **current** key. A rotated-out key cannot
  produce one — a KEL append needs the current key, and an old event already committed to something
  else. There is no detached-signature-resolved-as-of-a-pin path. So a rotated-out member cannot
  retroactively appear to have authorized an IEL event.
- **The forward floor closes the as-of-context backdate.** An event cannot pin a dependency at an
  old position (an old roster, an old federation context, an old authority state), because the
  per-chain floor only moves forward. This is the monotonicity backstop for the as-of pins.

**As-of authority is judged by the anchoring position, never by a self-asserted pin.** A document
(or any pinned reference) carries a `pin`, but authority-affecting resolution — grandfather and
rescission ancestry, roster and delegation state — is judged by the **anchoring position**: the
serial of the committing event, append-only-fixed via the chain `document ← SEL ← IEL Ixn ← KEL
Ixn` (each `previous`-linked). The verifier **enforces `pin == (the anchoring event).previous`**, so
the pin cannot select a more permissive past while the act anchors in the restrictive present. The
pin lives inside the document, where its issuer chose it; the anchoring position lives on the
append-only chain, where it cannot be inserted into the past. This is why the document layer can
trust a pin: it is checked against the chain, not believed
([`primitives/policy/documents.md`](primitives/policy/documents.md)).

#### Tiers

**Tier** names the cryptographic capability required to forge an event. It is set by
**danger-or-permanence** and is **orthogonal to count** (how many members must act). Tier is
dispatched from the event kind, never stored.

| Tier | Capability | Used for |
|---|---|---|
| 1 | signing key only | content (`Ixn`) — even at a high count |
| 2 | + rotation preimage | establishment-mutation, authority-grant, any sealed kill |
| 3 | + rotation + recovery preimage | repair, identity-kill |

The **reserve** (the rotation / recovery preimage, held apart from the signing key) is required
when a forgery would be high-harm or irreversible, **or** when the act must be **permanent on
arrival** (sealed). A **kill** (revoke / close / rescind / decommission) is the permanence case:
low-danger (it only removes trust) but **monotone** (a third party relies on it), so it must be
sealed — it rides a dedicated sealed kill-anchor and is tier 2 (an identity-kill is tier 3). Only
content is tier 1.

The old signing key is **not** a prerequisite for tier 2 or 3 — the rotation preimage reveals the
new signing key. On the KEL, `Rot` is single-signed (tier 2); `Ror` / `Rec` / `Fed` / `Dec` are
dual-signed (tier 3, new signing + recovery). IEL and SEL events have no intrinsic key state to
elevate against, so they reach a tier by **anchoring in a KEL event of at-least that tier**: a
tier-3 KEL event satisfies a tier-2 anchor requirement (anchor-tier elevation — it reveals both
preimages, and the rotation preimage alone already satisfies tier 2). This closes the
signing-key-only path to forging governance acts, grants, and terminals on the chains that root
other chains' authority. The per-primitive anchor matrix is in [`primitives/data/event-logs/`](primitives/data/event-logs/).

#### Structural authorization

**Chain events carry no policy.** Authorization is structural, per primitive:

- **KEL** — the device's own key state (tier 1/2/3 above).
- **IEL** — a roster of member KELs plus a **threshold vector** `{t_use, t_govern, t_delegate,
  t_recover}`, indexed by the event's kind. Every IEL kind **prices itself**: `Ixn` from `t_use`,
  `Gov` from `t_govern`, `Del` from `t_delegate`, `Rpr` from `t_recover`, the terminal `Dec` from
  `t_govern`. The one count-parametrized kind is the sealed kill-anchor `Kil`, whose committed
  `threshold` slot (`govern` / `delegate`) names the count — **backed** by the `Kil`'s own
  signatures at the IEL walk and **demanded** by the anchored kill's kind at the SEL check. So
  verifying an IEL chain's validity needs **no SEL input** — each event prices from its own kind.
- **SEL** — single-owner ownership: the owner IEL anchors the SEL event, and the count is set by the
  SEL event's kind.

**Threshold-vector floors** (re-checked on the post-change roster at every `Gov`, not only at
inception): `t_use >= 1`; the authority slots carry a **security floor** `>= 2` (hard, every
identity — no single member exercises authority) and a **recoverability floor** `<= |roster| − 1`
(evict/recover without one member — advisory at `|roster| = 2`, hard at `|roster| >= 3`, where a
threshold equal to `|roster|` is a gratuitous hostage config and is rejected). A singleton
(`|roster| = 1`) sets all thresholds to 1. The federation IEL's recoverability floor is **hard**
(it is critical infrastructure and must always be able to evict a compromised witness), so a
federation requires `|roster| >= 3`.

Authorization that a third party relies on — who issued a credential, who may present it — is the
job of the **document policy layer** ([`primitives/policy/policy.md`](primitives/policy/policy.md)),
which sits above the primitives and consumes their verification. Keeping the two apart removes the
issuer-chosen-policy backdate surface from the chain entirely.

#### Forks are Seal-Bounded

The structural mechanism that enforces current-state-only authority is the chain's **seal**.

Each primitive tracks `last_seal_advancing_event` — the SAID of the chain's most recent
seal-advancing event that landed cleanly on the linear chain. A new event's parent must sit
at-or-after the seal (`parent_serial >= seal_serial`); a submission whose parent sits in the locked
portion is rejected. This guarantees the authorization context resolved at the event's parent is the
chain's currently-tracked state, not a stale one.

The **seal-advancing** kinds (those that open a new locked window, plus the terminal `Dec` which
opens none) per primitive:

- **KEL**: `Rot` / `Ror` / `Rec` / `Fed` (and `Dec`).
- **IEL**: every non-inception **privileged** event advances the seal — `Ixn` is the lone content
  kind, and an IEL `Ixn` does not advance the seal; the privileged kinds (`Gov` / `Del` / `Kil` /
  `Rpr` / `Dec`) are the window-openers.
- **SEL**: `Pin` / `Rpr` (and `Dec`); a content `Ixn` does not advance the seal.

The terminal `Dec` advances the seal to its own serial and permits no successor. The seal-cap
rejects any submission whose parent sits before the `Dec`; a direct `Dec`-child passes the cap and
is rejected by the terminal-state gate.

KEL additionally tracks which recovery-key preimage is currently committed: once a recovery preimage
is spent (revealed by an `Ror` / `Rec` / `Fed` / `Dec`), it cannot be reused to recover against an
earlier divergence.

**Bounds on the post-seal window.** KEL, IEL, and SEL bound the gap between seal-advancing events at
`MINIMUM_PAGE_SIZE − 2` non-seal-advancing events, so a recovery batch produced on any conformant
deployment fits in any other's single page (`MINIMUM_PAGE_SIZE` is a protocol constant, not a
per-deployment knob; the `− 2` headroom accommodates a 2-event repair batch). On the IEL the cap is
just as load-bearing: content (`Ixn` — the rail **issuance** rides, via `issues[]`) does **not**
advance the seal, so trailing issuances accumulate and the seal lags the tip; without the cap the
post-seal window grows unbounded and page-atomic content-divergence repair breaks. A busy issuer
that fills the window **re-seals with an empty-delta `Gov`** (no roster change — the identity-layer
analogue of a KEL re-sealing via `Rot`; validation **accepts** an empty-delta `Gov`), advancing the
seal with no new kind. The exact constant and the empty-delta re-seal are IEL doctrine —
[`primitives/data/event-logs/iel/`](primitives/data/event-logs/iel/).

#### Divergence and repair

A chain **diverges** the instant it carries two **distinct** events at one serial. Distinct means
different-SAID: SAIDs are content-addressable, so two byte-identical events **are** one event (the
submit path accepts an already-present event idempotently, never as a second branch). So identical
acts dedup — two parties revoking the same credential produce the same `Dec` SAID and there is no
divergence; only distinct events at one position collide.

**A divergent chain is frozen.** It accepts **no new event of any kind** — content, governance,
rotation, kill — until the divergence is repaired. The **sole** valid next move is the repair,
authored as soon as the divergence is observed. This is the founding insight of the primitive.

**Divergence is resolved by tier, not by identity.** Chain data cannot tell the rightful operator
from an adversary — both branches were structurally authorized when they landed. So the divergent
set is evaluated by **tier**, and the highest tier present decides:

- **Only content (`Ixn`) is archivable.** A privileged event (a rotation, a `Gov`, a `Kil`, a
  terminal) is **never** archived or overturned — reversing a rotation resurrects retired keys, and
  un-doing a kill breaks a third party's reliance.
- **≤ 1 privileged branch → recoverable.** The repair (`Rec` on the KEL, `Rpr` on the IEL / SEL —
  itself tier 3, requiring the recovery reserve) **keeps the single privileged branch** (extending
  it — e.g. a `Rec` extending a forked `Rot`) and **archives the all-content branch(es)**, then
  advances forward. An all-content divergence keeps one branch and archives the rest. If the kept
  privileged event had anchored a higher-layer event, that anchor is **realized on recovery** — the
  higher layer's own threshold (`t_govern`, …) still gates it, so no forgery, provided that
  threshold is floored `>= 2`. **Singleton residual:** at `|roster| = 1` (`t_govern = 1`) realizing
  an anchored `Gov` succeeds — the one compromised member meets the gate — so a singleton recovery
  must be followed by an eviction `Gov` (part of why a single-device identity gets no governance
  resilience).
- **≥ 2 privileged branches → terminal.** No privileged branch can be archived to reduce to one
  (`{Rot, Rot}`, `{Gov, Gov}`, `{Kil, Kil}`, …) → the chain is contested and must reincept under a
  new prefix.

A linear tip-appended rotation (no divergence) is recoverable by appending a forward `Ror` past it.
Genuine reincept is a tier-3 compromise, a ≥2-privileged divergence, or federation-irreconcilability.

**Repair conditions** (data-driven, merge-layer-enforced, uniform across primitives):

- **Hard auth at landing.** The repair's signature / threshold check hard-fails on rejection — no
  soft-fail. (KEL `Rec`: dual-signature against the parent's rotation and recovery commitments. IEL
  / SEL `Rpr`: `t_recover` of the owner identity, anchored at tier 3.) Authority concurrence is a
  moment-in-time question; "submit and satisfy later" does not generalize to authority-tier checks.
- **The repair's `previous` is not in the locked portion.** It is at-or-after the most recent
  seal-advancing event on any branch. This restricts repairs to constructions that *could* be an
  honest extension of the submitter's own tip — a party holding stale authority cannot construct a
  repair against an old position to rearrange the chain. When the repair's `previous` is the
  divergence ancestor `v_{d-1}` (structurally shared across all nodes), the repair validates
  uniformly regardless of which divergent contents each node received — this is what makes recovery
  cross-node-validatable.

**Cross-node races do not converge at the protocol layer.** Two nodes can each accept a competing
event extending `v_{d-1}` via independent clean linear landings; gossip then delivers each to the
other node, where the seal-cap rejects the late arrival. The federation surfaces the disagreement
via **divergent witness receipts** (see [§Federation
convergence](#federation-convergence)). This is the deliberate trade-off: relaxing the seal bound to
admit competing privileged events at a sealed serial would re-open the stale-authority kill-switch
surface, so the bound stays unconditional and federation-race non-convergence is resolved at the
federation layer rather than by fork-merging.

**Pre-seal verifiability.** Everything at-or-below `last_seal_advancing_event` is permanently final —
for the chain (no event targets it) and for consumers (they verify against it indefinitely),
regardless of any later divergence. Anchors hosted at-or-below the seal stay anchored; documents
issued under at-or-below-seal state stay verifiable; audit queries on the sealed portion return
truthful answers. Above-seal events carry tier-1-only auth — structurally indistinguishable from
signing-key-only adversary capture — and become durable only when a later seal-advancing event
lands cleanly past them. The seal is the boundary the protocol can defend.

#### Kills are sealed; validity cut-offs are contiguous

A **kill** — revoke, close, rescind, decommission — is **always sealed on arrival**. It is anchored
in a dedicated sealed kill-anchor (the IEL `Kil`, tier 2; an identity-kill rides a tier-3 terminal),
distinct from the roster-changing `Gov`. Because a sealed kill-anchor is privileged and
terminal-on-divergence, the kill can **never** be archived by a repair (no silent un-revoke), and
there is no unsealed window to undo. A kill is **monotone**: restoring a killed thing is **never** a
retraction — the party reincepts under a **new prefix** and is granted or issued afresh. A re-grant
of the *same* killed prefix does not restore it; its kill locus permanently caps that prefix.

A **validity cut-off** (a rescission's cut-off, or a compromise rewind) removes a **contiguous
suffix** of a chain. By chain linearity every event builds on the prior, so only a contiguous tail
can be invalidated — never a non-contiguous subset. **Nothing past the cut-off is honored — grants
*and* kills alike**; there is no per-kind exception across a validity bound (honoring a post-cut-off
event would trust an un-anchored, invalidated event). In a compromise the invalidated suffix is
exactly the attacker's contiguous tail from the divergence point — legitimate and attacker events
never interleave into a subset worth keeping. A cut-off can only move **earlier** (more killing),
never later; a sealed kill is never retracted. Recovery from a mis-set cut-off is operational
(reincept and re-grant / reissue), not a rewind.

#### Inception tiers

Inception tier follows what the inception establishes:

- **KEL `Icp`** — tier 1. The root is self-authorizing; there is no chain above it.
- **IEL `Icp`** — tier 2. It establishes governance (a roster + threshold vector) — a genuine
  state-establishment.
- **SEL `Icp`** — tier 1. It establishes single-owner data, not governance, and an IEL `Ixn`
  anchors it. The pin is not a separate field: for a **credential SEL**, `data` **is** the
  credential's SAID and the pin lives **inside** the credential, so the `Icp` carries no manifest
  and the SEL floors to the IEL through the credential's pin. For a **lookup SEL** (where the
  verifier blind-recomputes the prefix from data it already holds), the pin cannot live in the
  recomputable prefix, so the `Icp` is paired with a **`Pin`** event carrying the pin — the only
  reason a SEL `Icp` needs a second establishment event.

A compromised tier-1 signing key can already issue content in your name, so letting it also create
a SEL adds no blast radius — tier-1 inception is sound. Issuing a credential is tier 1 because a
credential is **content** (one bounded, revocable claim); an authority-grant (a delegation, `Del`)
is tier 2 because it **expands who may act with your authority** going forward (an ongoing forgery,
not one revocable assertion).

#### Decommission and clean retirement

When a terminal `Dec` lands cleanly on a linear chain, it is a clean-retirement signal — no
compromise indicated, pre-`Dec` content keeps its meaning. Once it lands the chain is
Decommissioned and accepts nothing further. A `Dec` is privileged, so a `Dec` that would land in a
divergent set is subject to the divergence rules above (a `{Dec, content}` collision is recoverable
by keeping the `Dec`; a `{Dec, Dec}` or `{Dec, Rot}` collision is terminal). An IEL `Dec` freezes
all the identity's SELs.

A submitter who detects compromise pre-emptively has no dedicated "compromise signal" event:
available paths are to rotate the compromised key out (chain stays alive), to `Dec` (clean
retirement — semantically loose when compromise is the cause), or to attest out-of-band under a
separate KEL. This trade-off is accepted; the chain layer has no identity concept, so a
"terminate-with-prejudice" primitive justified by submitter intent would be structurally incoherent.

#### Limit of the doctrine — current-state compromise

The doctrine closes attacks rooted in **past** state. It does **not** defend against compromise of
**current** state. An adversary holding sufficient currently-controlling authority — current KEL
rotation (+ recovery) preimages, or `t_govern`-many current IEL members across distinct custody — is
the chain's current state by every protocol-observable measure, and can rotate authority away and
lock the prior operator out. There is no protocol mechanism to distinguish "legitimately current"
from "compromise-acquired-current"; there is only a narrow detect-and-respond window before the
adversary's rotation lands.

**Defense is layered** — the layers compose; none is load-bearing alone:

- **KEL dual-signature** on `Ror` / `Rec` / `Fed` / `Dec` blocks signing- and rotation-key
  compromise regardless of where the recovery key is custodied. A single-device deployment is
  first-class.
- **IEL threshold composition** (high thresholds, `M > N` redundancy across **distinct custody
  domains**) handles total device compromise: evict the device via a `Gov`; surviving members keep
  the threshold and the identity stays alive. Two prefixes under one operator's hardware compose to
  effective threshold 1 against an adversary who breaches that hardware — composition must span
  genuine custody separation.
- **Federation witnessing** makes a partition-or-no-partition rotation-tier race **detectable**:
  under always-witness, competing events at one position accumulate receipts from the full pool and
  threshold-two-events surfaces the disagreement (see [§Federation
  convergence](#federation-convergence)). The rotation-tier-compromise-plus-partition case is the
  structurally unavoidable CAP failure mode — VDTI guarantees the divergence is detected
  post-resolution, not prevented.
- **Operational hardening** — monitoring for unexpected governance/rotation events, fast
  detect-to-respond, custody separation, and abandon-and-reincept as the last resort.

**Adversary patience.** A strategic adversary accumulates authority quietly (compromise key 1, wait,
key 2, …) and acts only on a satisfying combination, so the response window is bounded by the
adversary's timeline, not the operator's first detection. Policy design is therefore a budget
against patience: high thresholds + custody separation raise the accumulation cost; `M > N`
redundancy tolerates loss of `M − N` members (evict via `Gov`, no reincept); hierarchical scope
partitioning bounds blast radius. A chain whose roster permits no eviction path — a threshold equal
to `|roster|` — loses to the first compromise that reaches the threshold and forces a reincept under
a new prefix, which propagates to every consumer. Design rosters to **survive compromise instead of
catastrophically reincepting**; treat reincept as the last resort.

**Cascade-reincept honesty.** Reincept is needed only when the primitive itself is blocked at the
federation layer (irreconcilable) — not when a referenced primitive is. Dependent chains whose
bindings reach at-or-below-seal state stay authorized.
- **IEL irreconcilable** → every SEL bound to it that would forward-extend its binding must reincept
  under a new prefix.
- **SEL irreconcilable** → the SEL is dead in place; nothing downstream cascades.
- **KEL irreconcilable** → dependents reincept only when the disputed KEL actually anchored their
  events **and** the resolving threshold lacks redundancy. A `M > N` roster absorbs a single
  member's dispute by evicting it via `Gov`.
The expensive case is a federation-layer dispute on an IEL at the root of a dependency tree — so
partition identity hierarchies to bound any single dispute's blast radius.

---

## Part 2: Cross-Cutting Doctrines

Properties that hold across all primitives and bind them into a coherent protocol. They constrain
how the protocol composes (across nodes, across kinds, across time) rather than asserting an
authorization rule; the Part 1 rules lean on them for their cryptographic-soundness argument.

### Ordering Without Timestamps

Chain events carry **no wall-clock timestamp field**. Ordering is by serial + cryptographic chain
linkage (`previous` SAID). Wall-clock timestamps on chain events would not be cryptographically
meaningful: an author can write any timestamp, the protocol can only verify an event was *observed*
at-or-before now, and clock drift across nodes precludes timestamps as a cross-node ordering signal.
Cryptographically verifiable ordering already exists via serials and linkage; adding timestamps
would be redundant for ordering and unsound for tiebreaking — an untrusted input as a protocol
decision input, which is exactly the backdate surface to avoid.

Where timestamps appear, they serve narrow roles within a **single party's reference frame** —
peer-to-peer signed requests (a Unix timestamp + nonce checked against the receiver's own clock),
feature-level fields on the content a chain event anchors (a credential's issued/expiry times,
advisory and checked by the verifier against its own clock). None influence chain ordering.

**Federation consensus clock (the one exception).** The federation publishes a coarse,
consensus-attested clock **for freshness / staleness detection only** — the `clock` group in each
federation `Gov`'s `manifest` (a timestamp SAD, one per governance change), sealed and monotonic,
**not** a field on any chain event. It bounds each witness key's validity window so a closed-window
key can only stamp old receipts, which makes a backdated dormant-chain forgery read **stale** —
detectable, fail-secure. It **defeats** backdating rather than inviting it, and intra-chain ordering
stays pin-based, so it honors this rule's intent; the bytes live in a SAD, so the primitives stay
timestamp-free. See [§Federation convergence](#federation-convergence) and [`federation/`](federation/).

### Federation Convergence

VDTI depends on **eventual cross-node convergence**: gossip propagation paired with deterministic
effective-SAID computation ensures every chain resolves to the same semantic state on every node in
a healthy federation where convergence is possible at the protocol layer. Where it is not —
concurrent privileged event races between nodes — divergent witness receipts at the federation layer
surface the disagreement uniformly.

The federation is **an ordinary (restricted) IEL** — there is no separate consensus algorithm and no
central state machine. Its roster is **witness KELs directly** (no per-witness policy or identity
wrapper); its kind set is restricted to `Icp` / `Gov` / `Dec` (no content, so it never diverges and
needs no repair; no delegation, since trust is per-federation and non-transitive). Its trust root is
a **config-pinned federation prefix** (a compile-time default with a runtime override) — the prefix
derives from the whole inception content `(roster, threshold, nonce)`, so it is a binding commitment
to the exact founder set. There is **no self-attestation carve-out**: authorization is ordinary
member-anchoring (the founders are the roster), and everything post-genesis is witnessed normally.

The convergence model has three components:

- **Gossip propagates events** — anti-entropy plus submission-time fan-out push new events to all
  nodes within a bounded window (the bound is operational; the doctrine asserts only the eventual
  property).
- **Semantic state is a function of the events** — each node computes a chain's state (Active /
  Divergent / Decommissioned, with which events at which serials) deterministically from the events
  it holds; identical event sets yield identical state.
- **Effective-SAID determinism** — where contents may differ across nodes (a divergent chain, or a
  federation-irreconcilable prefix), the effective SAID is a deterministic function of `(state,
  prefix)` so anti-entropy recognizes matching state across nodes uniformly (see [§Effective-SAID
  synthetic comparison](#effective-said-synthetic-comparison)).

**Witnessing is detection, not prevention** (and witnesses are reporters, not deciders): every
selected witness signs **every** structurally-valid event it observes at a position (always-witness),
receipts are indexed at the chain position `(prefix, serial)` rather than at event SAID, and a
position is **federation-divergent** iff two or more distinct witnessed SAIDs each reach threshold
**and** each resolves to a structurally-valid event (the verifier independently re-checks validity —
the database cannot be trusted, so a rogue's receipt on a fake event never triggers divergence).
This makes federation state **locally determinable** on every node, without watcher infrastructure.

Receipts are evaluated **as-of the event's federation context** — a receipt counts iff its signer is
in the roster of the federation at the position the event pins (`federationPin`), never at the
federation's current tip — so an event stays witnessed forever (no re-witnessing of history), and a
since-removed witness's established receipts keep counting. A witness's receipting key-window is
bounded by the **federation clock** (above): a cut or rotated-out witness earns no new pinned window,
and a witness **wipes superseded private keys on rotation and removal** (forward secrecy; durability
is unaffected because old receipts verify with public keys). Together — wipe plus the clock — these
close the harvested-old-key forgery on a dormant chain (it reads stale → detectable). Witness
rotation is legal **only** as a synchronized federation rotation-pin `Gov`; an off-ceremony rotation
produces receipts the federation does not honor.

**Detection is eventual, not at-decision-time.** Every detection guarantee assumes the consumer can
reach enough honest witnesses / converged gossip to see the competing branch. A consumer eclipsed to
a malicious subset, or reading during an incomplete heal, sees the detection later — so a binding
made in that window can transiently trust the wrong branch. This is the standard cost of a detection
model; the multi-source freshness bar shrinks the window but does not close it, and recovery is
operational (re-verify before binding; reincept on a surfaced divergence). **Single-node deployments
forfeit convergence** and the DB-tampering-surfaces-as-divergence property.

Full mechanics — receipt encoding, witness selection, the clock's tolerance band and upper sanity
bound — are federation doctrine ([`federation/`](federation/)).

### Extension Discipline

The protocol cannot prevent a currently-authorized party from chaining a new event onto any existing
event — `previous` validates against the structural parent, not "who authored the parent." Operator
**design discipline** closes the implicit-endorsement gap: extending an event is semantically
endorsing it (the new signed event carries the parent's content forward), so a submitter extends
**only**:

- **Their own previously-signed events.**
- **Attested-shared state** — the divergence ancestor `v_{d-1}` (the unique shared parent of all
  events at `v_d`, which every node accepts), or a deterministic dedup-equivalent inception (any
  party's inception for the same derivation inputs produces the same SAID, so extending it is
  extending shared state).

A submitter never points `previous` at an adversary event. If an adversary captures key material and
extends the chain linearly past the legitimate party's last attested event, the legitimate party's
structurally available moves all extend their own last attested event (`v_{N-1}`): a privileged
event there would create a divergence (surfaced via witness receipts and resolved by tier), and a
repair there is available only if the adversary's extension did not advance the seal past `v_{N-1}`.
Once the adversary has rotated authority forward past `v_{N-1}`, no protocol recourse remains and the
response is reincept. The discipline is structurally identical across primitives; the shapes of "own
tip" and "attested-shared state" instantiate per primitive, but the principle holds without
exception.

---

## Part 3: Verification Mechanics

The implementation invariants that make Part 1 enforceable. Verification and use happen in the same
pass, under the same lock, against the same trusted context — this is how "the database cannot be
trusted" becomes a safe operation.

### Verification tokens as proof of verification

Functions that consume chain data accept a verification token (`&KelVerification` /
`&IelVerification` / `&SelVerification`). Holding the token proves the chain was verified; token
fields are private with no public constructor, so the only way to obtain one is through the
corresponding verifier. A token exposes per-primitive specifics plus the cross-cutting signals: the
structural-validity result, which registered SAIDs were found anchored on the canonical branch,
per-position divergence (carrying the competing SAIDs when true), and witnessing status (`witnessed`
/ `minority_dissent`).

**Token reuse is transitive.** A cached token's reusability gates on the effective-SAID of **every**
chain it transitively leans on — the KEL(s) beneath an IEL, the IEL beneath a SEL, every delegator
above it, and the federation that witnesses it — not on that one chain alone. A lower-layer repair
that breaks an upper event must be visible to a holder of the upper token, so a loss-of-trust
decision confirms each dependency's effective-SAID **multi-source** (a witness-signed effective-SAID
is multi-source by construction; an unwitnessed chain degrades to single-source, flagged). "Is this
chain divergent / irreconcilable?" is itself a loss-of-trust question — a one-branch holder computes
a normal-looking tip and never sees a fork, so divergence detection is in the multi-source bucket.

### Walk semantics

Every walk is preloaded with the SAIDs the caller cares about. The **baseline is a full walk** that
returns which sought SAIDs were found and the chain's divergence status. Whether the tip must be
reached depends on the question: *"is the chain valid?"* walks to tip; *"is this SAID anchored?"* may
end once all sought digests are found, **provided the chain is non-divergent up to that point**. A
`search_only` walk ends when all digests are found and the token points at the reached position; a
`resume` takes that token forward to a later tip. **`resume` must re-run the to-tip negative checks**
(revocation / rescission / divergence) against the new tip whenever any transitively-pinned chain
moves — an incremental resume that only extended chain state would advance the token past a
revocation without surfacing it.

Chain verification **streams** events page by page rather than loading whole chains; the verifier
walks in generations (all events at a serial), and a generation spanning a page boundary re-fetches
rather than being processed half-observed.

### Structural problems error; everything else is reported

A **structural** problem — an invalid chain, a divergence, broken linkage, tamper, a SAID or prefix
mismatch — produces a descriptive **error**. A **non-structural** condition — a sought SAID not
anchored, a document's policy unsatisfied, an expired credential — is returned as **contextual
information** in the result, never raised. Callers must distinguish "the data is broken" from "the
answer is no"; conflating them is a correctness and fail-secure hazard. (Chain events carry no
policy, so there is no chain-layer "policy satisfaction" — document-policy evaluation is the policy
layer's concern, [`primitives/policy/evaluation.md`](primitives/policy/evaluation.md). The chain
verifier reports structural validity and anchoring; the policy layer composes those token answers.)

The verifier and the merge layer share the same walk but compose its result differently: the
**verifier** reads through pathology to expose it (it must surface the at-or-below-seal portion even
on a chain with above-seal divergence), reserving hard-fail for structural-integrity violations; the
**merge layer** gates writes — it runs the same verifier under a lock and rejects a submission whose
post-batch walk reports a structural failure, with no per-kind carve-out.

### Negative checks are positive lookups

"Is X rescinded / revoked / closed?" is answered by recomputing **one derived lookup-SEL address**
`derive(owner, topic, data)` and reading it (present → yes, O(1)), **never** by scanning a chain or
list for the absence of a kill. A scan-for-absence forces deep-inspecting everything it touches; the
positive lookup is O(1) and tamper-evident. This is why rescission and closure are lookup-SELs rather
than list-walks. Logs are referenced **by prefix**; a SAID is an integrity commitment, not a global
lookup key — there is no SAID→event index — so a SAID harvested off a public chain does not invert to
a private chain's prefix.

### Merge verification and advisory locking

All verify-then-write paths hold a PostgreSQL advisory lock for the duration of both verification and
write: the submit handler verifies the entire existing chain under the lock, obtains a trusted token,
verifies the incoming events against that token's data, and writes — never re-querying the database
between verification and use. The verifier supports **registering SAIDs of interest before the walk**
so the walk records what it observed without a second pass. The pattern is uniform across KEL, IEL,
and SEL.

### Federation witnessing in verification

Federation witnessing surfaces in verification as the per-token witnessing signals and as the set of
witnessed anchors that IEL / SEL anchor resolution consults on a KEL. IEL and SEL events do **not**
carry a federation field; they inherit federation context via their KEL anchors (the KEL is the leaf
of trust composition, carrying the federation context declared in the most-recent `Icp` / `Fed`
at-or-before the anchor's serial). A consumer refuses to bind under a divergent position or
insufficient attestation, and grounds trust in the **config-pinned federation prefix set**
(compile-time-baked + runtime override) — for a chain that transferred federations via `Fed`, each
federation in its history must be independently in the trusted set (no transitive trust). The full
witnessing rules are federation doctrine ([`federation/`](federation/)).

### Effective-SAID synthetic comparison

The effective SAID is the canonical chain-tip representation across KEL, IEL, and SEL — it identifies
a chain's current state and lets nodes recognize that state without exchanging chain data. A
normal-tip chain carries its tip event's real SAID; a decommissioned chain carries its `Dec` event's
real SAID. Two states have **synthetic** representations, depending only on `(state, prefix)` — no
history, no fork point, no serial:

- `hash_effective_said("divergent:{prefix}")` — the chain has competing branches at some serial
  (recoverable via repair). Applies on the KEL, the SEL, and any IEL carrying content — only the
  content kind (`Ixn`) diverges, so a federation IEL (which carries no `Ixn`) never reaches it.
- `hash_effective_said("irreconcilable:{prefix}")` — the prefix is in dispute at the federation
  layer (divergent witness receipts). The federation layer holds the source-of-truth; the per-node
  state stays Active / Divergent / Decommissioned.

There is **no "contested" per-node state and no synthetic for it** — a ≥2-privileged divergence is
terminal and recovers by reincept, and federation-layer dispute is the `irreconcilable:` synthetic.
The prefix-only shape is what lets two differently-divergent nodes compute the same
`divergent:{prefix}` and recognize each other's state; encoding a fork point would break that.
Differently-divergent chains are resolved through **local repair**, never by cross-node sync of the
divergent contents.
