# VDTI System Thesis

VDTI lets users control their identity and data without relying on a central authority. Devices are
decoupled from the identity that operates them; identity is a first-class primitive, and policy is a
composable layer over it. In contrast to solutions like KERI (a Decentralized Key Management
Infrastructure), where system-wide state must be inferred via out-of-band watcher infrastructure,
VDTI lets any verifier determine system-wide state — including attack exposure — by inspecting the
data itself.

This is the canonical orientation doc. Read it before doing substantive work on VDTI. Detailed
doctrine — primitive specs, witnessing mechanics, kind-strict anchoring, divergence handling,
custody, policy DSL, verification — lives in sibling docs under `docs/design/`. This doc states the
framing; the others elaborate it.

Terms used throughout, briefly:

- **SAID** — Self-Addressing IDentifier. Blake3-256 hash of the content with the SAID field
  populated with a fixed value.
- **SAD** — Self-Addressed Data. A content-addressable data structure identified by its SAID.

## What VDTI provides

System state lives in **append-only chains of cryptographically-linked events** that entities
throughout the network hold and verify independently — no central authority, no trust by fiat. Each
chain primitive plays a distinct structural role:

- **KEL** (Key Event Log) — anchors authenticity to devices. A device's cryptographic chain of
  custody; signing a SAID under a KEL event proves the device produced or endorsed that data.
- **IEL** (Identity Event Log) — governs identities. Aggregates member devices under a **threshold
  vector** `{t_use, t_govern, t_delegate, t_recover}` — how many member devices must act for
  content, governance, delegation, and recovery respectively. A rule spanning several identities
  lives in the document policy layer. Identity is the unit at which credentials are issued.
- **SEL** (SAD Event Log) — content-addressed application data, identity-rooted. A SEL is a
  **single-owner data log**: owned by exactly one IEL, with no roster of its own. Its events are
  authorized structurally by the owner IEL, which anchors them; it floors **up** to the owner IEL's
  current tip.

Federation is itself an identity, governed by a shared IEL. Membership is governance-authorized;
cross-federation interop is by user-initiated transfer rather than implicit trust.

Credentials are verifiable claims — documents that carry their own authorization policy and are
issued by an identity (structurally, under its own threshold); they permit access to resources based
on authenticated identity, and are revocable by their issuer.

## End-verifiability

Any verifier, given **data from any source** plus the **trusted federation set**
(compile-time-baked, runtime-overridable), can determine system-wide state — including whether a
prefix is divergent, decommissioned, or disputed. Source location matters for cost (cache,
replication, retrieval latency), not for trust. Tamper-evident chain linkage means a verifier
catches inconsistencies at page boundaries regardless of where the bytes came from.

This is the property that justifies the architecture. **End-verifiability over
data-from-any-source** is what differentiates VDTI from systems that require trusted-watcher
infrastructure to infer system state.

## Federation convergence

End-verifiability rests on the **data**, with the federation as a propagation aid:

- **Prevention for witnessed content; detection for the rest.** On a witnessed chain the
  witness-config's **majority floor** (`threshold > signers/2`) plus
  one-content-sibling-per-position witnessing means two competing content events can never both be
  witnessed — a content fork is **prevented** from forming, below a priced fork-cost of
  `2·threshold − signers` compromised witnesses. Privileged races, direct-mode chains, and the
  byzantine residual are **detected**.
- **Detection is data-local.** Gossip propagation plus deterministic effective-SAID resolution
  ensures every chain converges on the same semantic state across all nodes that hold the same
  events. A divergence is resolved by **tier**: a content fork is repairable; a divergence with
  **two or more privileged branches** is _terminal_ — there is no merge for it. Whether a fork is
  terminal is a **branch-level fact any verifier walks from the retained branches** (a node retains
  a competing branch as evidence rather than discarding it at the seal-cap), never a verdict
  delegated to the federation.
- **The federation propagates.** Cross-node privileged-vs-privileged races still converge
  data-locally — the witness beacon's divergent receipts (see
  [`federation/witnessing.md`](federation/witnessing.md) — _forthcoming_) **enumerate the competing
  branches** so a one-branch holder can fetch and walk them, but the verdict is the verifier's own.
  The federation delivers evidence; it does not decide.

A single node can still _detect_ a divergence it holds — local end-verifiability needs no federation
— but it forfeits the beacon's **propagation** (learning of divergences it does not yet hold) and
the **freshness** that a single node cannot self-attest. So federations are not optional for
propagation and freshness.

## Adversarial-first posture

Decentralized data systems get attacked at the seams between primitives. VDTI is connected to the
internet; input cannot be assumed valid, well-formed, or non-conflicting. Every structural rule in
the design exists _to handle the adversarial case_ — the valid case is the trivial case.

### The lens

For any gap, deviation, or design choice, ask:

- What is the attacker doing? What is the attacker trying to break?
- What rejection code emerges? Does it correctly name the cause-of-rejection?
- Does the diagnostic feed accurate forensics to operators and verifiers?
- Does the rule preserve or strengthen tamper-evidence at the device boundary (KEL) or identity
  boundary (IEL)?
- Does it preserve fail-secure behavior — when the system can't determine an answer with confidence,
  does it default to refusing rather than guessing?

### Reasoning patterns that are smells

These framings indicate the security model isn't being treated rigorously:

- **"Under valid input"** / **"happy path"** / **"in the normal case"** — if the precondition is
  attacker-controlled, the branch can fire. The valid case being correct says nothing about the
  adversarial case.
- **"No current codepath does X"** — not a safety argument in a cryptographic context. Codepaths
  change. Defenses must be defensible at the algorithm or primitive level, not at the codepath
  level.
- **"Outcomes commute under valid input, so implementations can pick whatever order"** — ordering
  affects what diagnostic fires, what state gets logged, what forensic signal reaches operators.
  Doctrine should flow from adversarial-input correctness, not from outcome-equivalence under benign
  inputs.
- **"This branch can't fire because [precondition]"** — verify whether the precondition can be
  attacker-controlled. If yes, the branch can fire.

### Posture

Think like the attacker to defend against attacks. Assume you are trying to destroy your own design
and try to make it bulletproof. The design is bulletproof when the attacker's attempts produce
**correct-and-informative** rejections — not just rejections, but rejections that name the actual
cause and enable forensic response.

## Load-bearing doctrines

One-line statements of the key doctrines; detailed elaboration in the linked design docs.

### Compromise is permanent

Authority over a chain belongs only to its currently-tracked state. Past keys, past policies, past
endorsers have zero structural ability to act once supplanted — a KEL signing key rotated out cannot
extend the chain even if the adversary still holds it.

→ [`protocol-doctrine.md` §Compromise is Permanent](protocol-doctrine.md#compromise-is-permanent).

### Divergence is resolved by tier; a divergent chain freezes further origination

A **live** fork — two distinct events at one serial, at or above the seal — freezes further work and
resolves by **tier**, never by identity:

- **Freeze is origination, not the reading.** No new work lands on a live fork until it resolves (a
  repair, or — for a content fork — a seal-advancer on the winning branch that buries the loser).
  The chain's reading stays a pure function of the events held; "frozen" is a write posture, not the
  verdict.
- **Resolution is by tier, not identity.** The chain cannot tell the operator from an attacker —
  both branches were authorized when they landed — so it decides by tier: only content (`Ixn`) is
  archivable, and a privileged branch is kept only by whoever holds its recovery preimage — a
  cryptographic fact, not a who-is-legit judgment.
- **Terminal forks reincept; races converge data-locally.** Two or more privileged branches are
  terminal — recovered only by reincept. Concurrent privileged races converge with every node
  holding both branches and walking the verdict itself; the federation propagates, it does not
  decide.

→ [`protocol-doctrine.md` §Divergence and repair](protocol-doctrine.md#divergence-and-repair).

### Forks are seal-bounded

A new event's parent must sit at-or-after the chain's most-recent seal-advancing (privileged) event
(`last_seal_advancing_event`); everything below that seal is locked. Without the bound, anyone who
ever held authority over a chain would keep a permanent kill switch — a rotated-out key or an
evicted member could append below the seal, against a context they no longer control. The bound is
protocol-enforced via proactive seal-caps, which also keep a recovery batch within a single page so
repair is cross-node-validatable.

→ [`protocol-doctrine.md` §Forks are Seal-Bounded](protocol-doctrine.md#forks-are-seal-bounded).

### Defense against current-state compromise is layered

KEL dual-signature on `Ror` / `Rec` / `Wit` / `Dec` (rotate-recovery, recover, federation-bind,
decommission) blocks signing- and rotation-key compromise — exfiltration, brute force, coerced
signing, side channels — regardless of where the recovery key is custodied. A single-device
deployment is first-class. IEL threshold composition (high thresholds, `M > N` redundancy across
distinct custodians) handles total device compromise: burn the device, evict it via a `Evl`
(governance change). KEL-internal custody separation — recovery key on a different device, HSM,
ceremony-gated — is an optional deployment hardening for threat shapes where signing and recovery
would otherwise fall together. A biometric or device PIN gating the keystore is a further on-device
layer — it raises the cost of using a stolen, locked device, but gates _access_ rather than custody:
it can be coerced, and an unlocked device remains usable.

→
[`protocol-doctrine.md` §Limit of the doctrine](protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise).

### Federation convergence

Detection is **data-local**: a node retains a competing branch as evidence and walks the retained
branches to decide whether a fork is terminal — even priv-vs-priv races converge this way. Retention
is **bounded** (≥ 2 competing events per position — privileged on the spine, content as fork
evidence; the uncommitted below-seal flood is droppable, since a privileged event re-validates from
the spine, not from below-seal content), so keep-all-data is not keep-everything. The federation's
divergent witness receipts **propagate** the competing branches to a node that lacks them (and
witnessing supplies freshness); they do not decide the verdict. End-verifiability over
data-from-any-source rests on the data, with the federation as the propagation aid.

→ [`federation/witnessing.md`](federation/witnessing.md) _(forthcoming)_.

### Operational hardening composes on top

Monitoring for unexpected governance or rotation events; fast detect-to-recover response via `Rec` /
`Ror`; abandon-and-reincept as last resort. Multi-party **governance** must serialize submissions
above the protocol layer (designated submitter, leader election, or consensus over the identity's
membership); for high-stakes IEL identities this is load-bearing, not optional — a governance race
is privileged, and a `{Evl, Evl}` collision is terminal. **Content** serialization is the same
discipline at lower stakes: on a **witnessed** chain the majority floor prevents a competing content
sibling going live, so an un-serialized content race costs stalls and re-issuance — a liveness cost,
not a safety one; it stays load-bearing for **direct-mode / solo** chains, where no majority gates
content.

→ [`../operations/multi-party-governance.md`](../operations/multi-party-governance.md)
_(forthcoming)_.

### Cascade-reincept honesty

Reincept is needed when the primitive itself is **disputed** (a data-local verdict) — not when a
referenced primitive is. The cascade rules:

- **A disputed IEL** → every SEL bound to it that would forward-extend its binding must reincept
  under a new prefix.
- **A disputed SEL** → the SEL is dead in place; nothing downstream cascades.
- **A disputed KEL** → dependents only reincept when the disputed KEL actually anchored events on
  them AND the resolving threshold lacks redundancy. Rosters with `M > N` across distinct custodians
  absorb single-member disputes by evicting the disputed KEL via a `Evl`.

The expensive case is a dispute on an IEL at the root of a dependency tree — partition identity
hierarchies so any single dispute has bounded blast radius.

→
[`protocol-doctrine.md` §Limit of the doctrine](protocol-doctrine.md#limit-of-the-doctrine--current-state-compromise).

## Implications

### Correctness is the only metric

VDTI's design is structurally interlocking: pre-seal verifiability, privileged-divergence rules,
locked-portion bound, seal-cap, federation-as-identity, federation witnessing — all hold together as
a single system of properties. If any piece is wrong, the whole system likely fails to provide its
guarantees.

When deciding between options, the criterion is "which is more likely to be correct," not "which is
cheaper, faster, or easier." Wrong doctrine produces wrong code; wrong code collapses the
end-verifiability story that justifies the architecture.

### Fail secure, not safe

When the system cannot determine an answer with confidence, it refuses rather than guesses. Guessing
leaks structural uncertainty into downstream consumers — the verifier loses end-verifiability the
moment a primitive operates on inferred state.

### The verifier is the trust boundary

Every chain-validity invariant lives in the verifier walk or completion. Trust only the data; not
services, not databases, not peers. Submit-handler-only rules are a code smell — if an invariant
matters, the verifier enforces it.

### Greenfield — no migration path

VDTI ships once. There is no rollback for a wrong design decision; protocol semantics propagate to
every verifier, every chain, every credential. Doctrine that turns out to be wrong cannot be patched
after deployment — every chain produced under the wrong rule remains under the wrong rule.

This is the cost basis for the "correctness over ease" framing above.
