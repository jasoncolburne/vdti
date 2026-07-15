# VDTI residual risks

This is the honest-limits catalog: every risk the design does **not** fully eliminate — knowingly
accepted, bounded, mitigated-but-not-closed, or pushed to an operator or application. It exists so
that a reader never has to reconstruct "what is this exposed to?" from scattered mentions across the
design surface, and so that a deployment can make each trade with eyes open.

A residual is not a bug. Each entry below is a place where the design chose a bound, a trade, or a
deliberate finality over a fuller guarantee that would cost more than it is worth — or a place where
the guarantee is real but rests on a precondition (an operator setting, an application-builder
supplying entropy, a key staying secret) that the framework can provide but cannot enforce.

Almost every residual here reduces to one of a small set of **cross-cutting assumptions**, restated
at the end. When an entry says "the accepted assumption," it means one of those.

## How to read this

Each residual is written as three fields:

- **Attack** — the concrete condition under which the residual is realized: what an adversary must
  do or what must go wrong. Written as a property that fails, not a recipe.
- **Mitigation** — what bounds, detects, or limits it in the current design, and where the
  authoritative (fail-secure) path still holds.
- **Lost** — what is actually given up if it is realized: the accepted cost.

**Cost of exposure** ranks how bad realization is, independent of how hard it is to reach:

- **Catastrophic** (30) — irreversible loss of an identity (a prefix can never be recovered, only
  reincepted under a new one) or a trust break spanning a whole federation.
- **High** (10) — a serious break that is bounded or recoverable, or one gated behind a strong
  precondition (a key theft, a quorum compromise, a skipped mandatory step).
- **Medium** (3) — a bounded, recoverable exposure needing notable adversary capability or an
  operator error; usually a liveness, availability, or bounded-correlation cost, not a trust break.
- **Low** (1) — minor, self-limiting, or a deliberate capability ceiling; no adversary advantage
  beyond the stated bound.

**Exploitability** is how attainable the attack is. The design assumes all keys live in **device
hardware**, key changes are **pre-rotation** (the reserve is committed, never exposed), and
signatures / KEM are **ML-DSA-65/87** / **ML-KEM-768/1024** (no algorithmic break in view) — so
attainability spans **orders of magnitude**: an operator slip is routine, while lifting a 256-bit
post-quantum key out of an HSM or enclave, let alone a quorum of them held apart across
independently-operated witnesses, is astronomically harder. The scale is therefore **logarithmic** —
each band a multiple of the next, not a step.

- **Inherent** (1000) — no one has to act: metadata visible to infrastructure or any public-chain
  reader. No _scored_ residual sits here — the genuinely-passive items are the inherent trade-offs
  below.
- **Human Error** (300) — an operator slips: a misconfig, an opt-out left on, a lost key not cut.
- **Human Intent** (100) — a **person** is compromised on purpose: social-engineering, an insider,
  or coercing a witness operator. The operational-security risk — above the cryptographic bands
  because a human is easier to turn than a hardware key.
- _— the hardware / post-quantum barrier —_
- **Signing** (30) — a `t_use` quorum of hardware-held PQ **signing** keys; reaches only buriable
  content.
- **Reserve** (10) — a `t_authorize` / `t_govern` quorum of **rotation reserves**, held apart from
  the signing key and pre-rotated.
- **Witnesses** (5) — a `threshold` of the federation's **witness keys**; harder than a reserve
  because witnesses are independently operated, so a quorum spreads across separate operators you do
  not control.
- **Signing + Witnesses** (2) — a signing quorum **and** a witness quorum, each in its own hardware.
- **Reserve + Witnesses** (1) — a reserve quorum **and** a witness quorum; the hardest.

**Risk = Cost × Exploitability** is what the ranked tables sort by, so a certain-but-passive leak or
a likely operator slip sorts **above** an astronomically-rare-but-catastrophic key compromise. Both
factors carry the weights above; the product is bucketed **Critical ≥ 1000 / High 200–999 / Medium
50–199 / Low ≤ 49**.

Ranking is a judgment call about blast radius, reversibility, and what is protected. The ordering
below is a first pass meant to be argued with, not a settled verdict.

The **ranked summary** sizes each residual by **Cost** (how bad the outcome is), **Exploitability**
(how attainable it is), and **Risk = Cost × Exploitability** (the sort key), and tags it by **axis**
(the property at risk) and **outcome** (what a user or operator sees). The two ranked tables carry
different remaining columns: **Irreducible** adds **requirements** (what an attacker must already
have), **detectable**, and **resolution**; **Avoidable** adds **mitigation** (the deployment control
that removes it). The **inherent trade-offs** table is unscored — accepted costs, not attacks.

## Classification axes

Each residual threatens one property, sometimes two; the table names the primary, or both where they
are equally the point.

- **Trust** — integrity of authorship and attestation. Can an attacker forge events, take over an
  identity, or be believed as someone they are not? The core end-verifiability property.
- **Privacy** — confidentiality of identities, relationships, and activity. Can an observer
  correlate, de-anonymize, or read what should be hidden?
- **Availability** — liveness. Can the system, an identity, or an operation be denied, frozen,
  stalled, or capped?
- **Recoverability** — the cost of recovering from a realized compromise or error. Is recovery
  in-place, or does it force reinception, lose history, or leave authority you cannot revoke?
- **Freshness** — whether a consumer can know the current truth in time. Is an attack real but
  unseen at decision time — an eclipse, a stale view, a drifted clock, a still-open harvested-key
  window?

## Ranked summary

Three groups. The first is the **irreducible adversarial risk** — what a deployment carries even
under tight config and correct operation, the honest answer to "if I am configured and operating
securely, what am I exposed to?" The second is **avoidable** — extra exposure from opting out of a
default, a weak or degenerate config, a skipped step, or an operational lapse, each with its
one-line fix. The third is **inherent trade-offs** — deliberate design costs and properties (caps,
finality, retention, minimum-disclosure metadata) that are not attacks you defend against but
consequences you accept. An evaluator comparing solutions reads the first group.

Outcomes are what a user or operator would actually observe. (The detailed entries below are grouped
by theme, not by these three groups; a handful of placements are noted in the entry.)

### Irreducible — under tight config and correct operation

| Residual                              | Cost         | Exploitability      | Risk         | Axis                   | Requirements                                                                                                                                                      | Detectable                     | Outcome                                            | Resolution                                                    |
| ------------------------------------- | ------------ | ------------------- | ------------ | ---------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ | -------------------------------------------------- | ------------------------------------------------------------- |
| Rotation-reserve theft                | Catastrophic | Reserve             | High (300)   | Trust + Recoverability | A `t_govern` or `t_authorize` reserve quorum                                                                                                                      | **Yes** — monitoring           | Attacker takes over your prefix                    | Reincept + notify relying parties                             |
| Lookup prefix seen by witnesses       | Medium       | Human Intent        | High (300)   | Privacy                | Compromise a witness operator to weaponize a prefix it legitimately sees, + a known candidate subject                                                             | No — passive at the witness    | Infra confirms a subject you both know             | Inherent to a witnessed lookup; a cut stops only exfiltration |
| Document governance-quorum compromise | High         | Reserve             | Medium (100) | Trust + Recoverability | A `t_authorize` quorum of the creator's reserves                                                                                                                  | **Yes** — monitoring           | The document is captured                           | Reincept + notify relying parties                             |
| Forced-dead receive key               | High         | Reserve             | Medium (100) | Availability           | A `t_authorize` reserve quorum — forge a `Trm` rescind so the key reads dead                                                                                      | **Yes** — monitoring           | Senders can't reach you until you republish        | Republish at a fresh lineage                                  |
| Just-cut key still reads fresh        | Medium       | Signing             | Medium (90)  | Freshness              | Harvest a just-cut key within the staleness window (seconds)                                                                                                      | **Yes** — stale on close       | A just-revoked key still forges, briefly           | Window closes/tighten thresholds                              |
| Signing-key theft + witness collusion | Catastrophic | Signing + Witnesses | Medium (60)  | Trust + Recoverability | `t_use` signing keys **and** a colluding `threshold` witness quorum, shrinking toward `2·threshold − signers` as a partition splits the redundancy onto the rival | **Yes** — provable double-sign | Your identity bricks                               | Reincept                                                      |
| Signing-key content forgery           | Low          | Signing             | Low (30)     | Trust                  | `t_use` signing keys (content stays buriable)                                                                                                                     | **Yes** — fork + monitoring    | Forged content appears until you bury it           | Bury (rotate) — the anchors die on ascent                     |
| Eclipsed at decision time             | High         | Signing + Witnesses | Low (20)     | Freshness              | A signing-key fork + coercing the queried witnesses to withhold                                                                                                   | Post-resolution                | You bind the attacker's branch, not the honest one | Re-verify multi-source before binding                         |

### Avoidable — loose config, opt-outs, and operational lapses

These aren't the point — someone configured and operating correctly carries none of them. They are
enumerated for completeness, each with the one thing that makes it go away.

| Residual                       | Cost   | Exploitability | Risk            | Axis           | Outcome                                       | Mitigation                                                                                                           |
| ------------------------------ | ------ | -------------- | --------------- | -------------- | --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------- |
| Lost keys left in the roster   | High   | Human Error    | Critical (3000) | Trust          | Federation governance is taken over           | Cut lost keys promptly (watch the at-risk flag)                                                                      |
| Skipping the freshness check   | High   | Human Error    | Critical (3000) | Trust          | You accept a forged, stale-issuer credential  | Always run the mandatory to-tip check                                                                                |
| Gated record without a nonce   | High   | Human Error    | Critical (3000) | Privacy        | A named member is de-anonymized               | Give every gated record a high-entropy nonce                                                                         |
| Fail-open revocation opt-out   | Medium | Human Error    | High (900)      | Trust          | You accept a revoked subject                  | Stay fail-secure; don't opt down                                                                                     |
| Fail-open on a walk timeout    | Medium | Human Error    | High (900)      | Trust          | You accept a revoked subject under latency    | Fail secure on timeout where it matters                                                                              |
| Leaked chain prefix            | Medium | Human Error    | High (900)      | Privacy        | Your whole history becomes linkable           | Keep prefixes out of logs and shared refs                                                                            |
| Guessable derived address      | Medium | Human Error    | High (900)      | Privacy        | An attacker probes your status / existence    | Use a high-entropy `data` input                                                                                      |
| Mis-set rescission boundary    | Medium | Human Error    | High (900)      | Recoverability | You cut honest work or miss bad work          | Cut at genesis when the loss time is unknown                                                                         |
| Naive delegator rescission     | Medium | Human Error    | High (900)      | Recoverability | Sub-delegated creds keep being issued         | Move the boundary before the sub-grant                                                                               |
| Routing around a delegator     | Medium | Human Error    | High (900)      | Recoverability | A cred via another path stays valid           | Rescind at the root, or issue under a threshold                                                                      |
| Consumer clock drifts backward | Medium | Human Error    | High (900)      | Freshness      | You accept backdated data unknowingly         | Keep the clock NTP-synced within `CLOCK_TOLERANCE_BAND`                                                              |
| Anonymous-write flood          | Medium | Human Error    | High (900)      | Availability   | Your store fills with junk (until gated)      | Rate-limit or gate anonymous writes                                                                                  |
| Two-member identity            | Medium | Human Error    | High (900)      | Availability   | One bad device freezes you; reincept          | Add a third key to become recoverable                                                                                |
| Recovery breaks a dependent    | Medium | Human Error    | High (900)      | Recoverability | A dependent event breaks                      | Don't bury a branch your own anchors depend on (you shouldn't erase your own events)                                 |
| Leaked gated-record bytes      | Medium | Human Error    | High (900)      | Privacy        | Gated plaintext is readable once bytes escape | Encrypt sensitive content (use the exchange channel)                                                                 |
| Even-signers tie               | Low    | Human Error    | High (300)      | Availability   | A position stalls (never forks)               | Use an odd number of signers                                                                                         |
| Never-rotated witness key      | Medium | Signing        | Medium (90)     | Freshness      | A stolen witness key forges up to a year      | Rotate witness keys with margin                                                                                      |
| Under-provisioned witness set  | High   | Witnesses      | Medium (50)     | Trust          | N compromised witnesses forks you             | Provision `signers`/`threshold` for the fork-cost `N = 2·threshold − signers` you need (traded against availability) |

### Inherent trade-offs — deliberate design costs, not attacks

These are not adversarial residuals or mistakes — they are properties the design chooses on purpose:
bounded resources, structural finality, and the minimum metadata an end-verifiable system exposes.
Listed so an evaluator sees the full picture; none is a defense you can add.

| Residual                       | Axis           | The accepted trade-off                                                                                                                                                                                                                     |
| ------------------------------ | -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Config-pinned federation root  | Trust          | Trust roots arrive over an out-of-band channel — the universal bootstrap axiom (cf. CA roots). A mismatch simply fails; there is nothing to trust wrongly unless that channel itself is compromised                                        |
| Forgeable document root        | Trust          | A document root is anonymous-write, so a competing root is always mintable; legitimacy is social and a holder self-authenticates against the derived prefix — the same out-of-band bootstrap axiom as the config-pinned root, one layer up |
| Referenced content gone        | Availability   | A referenced record can read "not present" — retention is an author window, not a lifetime guarantee for the reference                                                                                                                     |
| Roster / seal caps             | Availability   | Very large rosters and long content runs between seals are refused — deliberate ceilings that bound verifier work; an over-long rebind chain is refused by the general work bound, not a per-chain cap                                     |
| Dead-branch flood              | Availability   | A signing-key adversary can waste bounded storage / traffic; it is never canonical and self-resolves                                                                                                                                       |
| Dangling-parent flood          | Availability   | A junk flood denies only the flooder's own placement, never others                                                                                                                                                                         |
| No retroactive distrust        | Recoverability | A co-signed bad event stands; you remediate forward (revoke, evict) rather than rewrite history                                                                                                                                            |
| Late sealed straggler dropped  | Recoverability | A rare legitimately-late sealed event is dropped — the price of the backdate defense                                                                                                                                                       |
| Data log severed by a recovery | Recoverability | Recovering a content-tier compromise forces burying the whole tail; every data-log event anchored in that window is severed — the price of full deadenability with no repair machinery, bounded and re-anchorable                          |
| Confirm-a-known-subject        | Privacy        | A party already holding a subject's grant instance can check that subject's status — the minimum disclosure that makes revocation checkable                                                                                                |
| Issuance volume / timing       | Privacy        | An observer of the public chain sees issuance volume and timing, never which credential or to whom                                                                                                                                         |
| Addressable sub-records        | Privacy        | A composed record's shape and its ungated leaves are addressable — the price of partial disclosure                                                                                                                                         |
| One-shot isn't deletion        | Privacy        | One-shot is delivery, not deletion — the first authorized reader keeps the bytes                                                                                                                                                           |

---

## 1. Key and reserve compromise

The most severe residuals: a stolen secret that the recovery model cannot walk back. These are the
framework's acknowledged points of no return, shared in kind with any pre-rotation identity system.

### Rotation-reserve theft → takeover — Catastrophic

- **Attack** — An identity is governed by a **`t_govern` threshold of member KELs**, each holding a
  rotation **reserve** in its own hardware apart from its everyday signing key; the reserve defends
  the signing key, not the reverse. An adversary who steals a **`t_govern` quorum** of those
  reserves authors a valid identity-governing rotation to keys they control (a single stolen reserve
  takes over only one member KEL — inert at the identity level). On a dormant chain this is silent —
  witnesses sign it as an ordinary next event, and there is no on-chain divergence to challenge; if
  the adversary rotates at the identity's next position first, the owner's later attempt is a late,
  declined sibling. There is no structural veto.
- **Mitigation** — The reserve is held separately (in device hardware), so a signing-key compromise
  alone cannot reach it. The takeover is not prevented, but it need not be silent: an owner who
  [monitors their own chain](monitoring.md) — comparing the network's effective SAID for their
  prefix against what their key state says it should be — is alerted the moment an event they did
  not author appears, and reincepts and warns relying parties fast. The guarantee the design makes
  is "no **undetected** takeover for a monitored chain," not "no takeover."
- **Lost** — Control of the prefix, permanently. Recovery is reinception under a **new** prefix plus
  out-of-band notification of every relying party. Irreversible.

### Current signing-key content forgery — Low

- **Attack** — A compromised current signing key can author content or assertions in the owner's
  name during the compromise window.
- **Mitigation** — It **cannot seal** them — sealing needs the reserve — so it cannot make them
  permanent. Authoring at the owner's position is a **fork** the owner sees at once, and sooner with
  [monitoring](monitoring.md); the owner **buries** it by sealing their own branch with a rotation,
  which the attacker, lacking the reserve, cannot counter. Burying the branch kills the forged
  content **and any issuances anchored on it, by deadness-ascent** — no separate revocation is
  needed. Requiring at least two signers for content means a single compromised device can't author
  alone.
- **Lost** — A transient window before burial in which a relying party may act on the forged content
  and then needs forward notice it was buried. **Not** permanent — permanence needs the reserve,
  which is the takeover above.

---

## 2. Witness and federation trust

Witnesses are **semi-trusted infrastructure**: trusted not to be generally compromised (the
below-threshold byzantine assumption), never trusted for end-verifiability. The residuals here are
what happens at and past that boundary.

### Witness collusion is a leg, never a forgery on its own

- **Attack** — There is no "witnesses forge events" residual, and this is worth stating because it
  is easy to overstate. Witnesses gate **first-seen** (which sibling is accepted at a position) and
  **freshness** (receipts stamped against the federation clock); they do **not** author events, and
  a verifier checks the author (userland) signatures on every event it walks. A colluding quorum
  above the below-threshold assumption can therefore only do two things, each needing something
  else: (a) **accept a fork** — but the competing events still need a valid author signature, so
  this pairs with a **key compromise** (the brick and forced-dead-key residuals); or (b) **suppress
  or hide** honest branches, which is the eclipse residual. Alone, a compromised quorum forges
  nothing.
- **Mitigation** — The below-threshold byzantine assumption is the trust root; the witnessing floor
  and fork-cost dial price the collusion, and a double-sign is provable. End-verifiability trusts
  only the data — receipts assist propagation and freshness, never authorship.
- **Lost** — Nothing on its own. Naming it keeps the compound residuals honest: every "witnesses do
  X" cost is really "a key compromise **plus** collusion."

### Signing-key theft + witness collusion → brick — Catastrophic

- **Attack** — A terminal dispute is two **accepted** sealed branches at one position; a sealed
  branch is never buried, so it forces the identity to abandon the prefix and reincept. Forging the
  rival seal needs the **current signing key**, not the reserve: a seal at a position reveals this
  epoch's key and is signed by it, so by that instant the reserve is **spent** — a competing seal at
  the same position reveals and signs with that same current key (the next reserve only authorizes
  extending _forward_). Honest witnesses **decline** the late sibling (first-seen); its only
  reachable effect is **with a colluding quorum** that accepts both. So it takes a **signing-key
  theft _and_ a federation-trust breach**. (An attacker who instead won the first-seen race with the
  still-secret next key — the reserve — gets a **takeover**, not a brick; that is the reserve-theft
  entry.)
- **Mitigation** — Both legs are expensive: honest witnesses decline the late rival, so a second
  accepted seal needs a colluding quorum — `threshold` witnesses, down to the
  `2·threshold − signers` intersection only under a full partition (lifted by a hardened larger set;
  sub-majority configs rejected), and the double-sign is **provable** from the data. The window is
  bounded by rotation frequency — rotate past a position and a rival there is dropped below the
  seal. (The honest paths to two seals — a reserve replicated across partitioned nodes, or a
  partitioned governance race — are the separate configuration residuals.)
- **Lost** — Availability of the identity: forced reinception (permanent loss of the prefix). The
  proof gives after-the-fact accountability, not prevention.

### Fork-cost — `threshold` colluders, dropping to `2·threshold − signers` under partition

- **Attack** — Forking or bricking a witnessed position needs the author's key **plus** a colluding
  witness quorum whose size is not fixed. A selected witness signs the first valid sibling it sees
  at a position and never abstains because threshold is already met — so with no partition every
  honest witness signs the legitimate seal and the rival is carried entirely by colluders: a full
  **`threshold`**. Each honest witness an attacker can **partition** onto the rival (withhold the
  legitimate seal, present the rival first) is one honest first-seen receipt the rival gains and one
  fewer colluder needed: **`threshold − k`** for `k` partitioned witnesses, bottoming at
  **`2·threshold − signers`** once the whole `signers − threshold` redundancy is split. So
  `2·threshold − signers` is the attacker's best case (a total partition), not the standing cost;
  the majority requirement is **enforced** (sub-majority configs rejected), so even that floor stays
  **at least 1**, computable in advance from the deterministic selection at the minimal majority.
- **Mitigation** — Two knobs set the exposure: the witness pool `signers` and the trust `threshold`
  (a strict majority of the pool). The fork-cost floor `2·threshold − signers` (the attacker's best
  case, at a full partition) and the availability slack `signers − threshold` (receipt failures
  tolerated before a position stalls) **sum to the threshold** — and they are the same witnesses
  viewed twice: the slack redundancy that buys availability is exactly what a partition converts
  into rival receipts. Adding a signer moves one unit from the fork-cost floor into slack; raising
  the threshold raises the sum itself, up to `signers − 1`. So fork resistance and availability
  trade one-for-one, and the operator picks the point. **At a well-secured config a large number of
  witnesses can be compromised and the attack still fails** — it takes the full quorum, and anything
  short changes nothing. The framework **warns** on a fork-cost-1 config but does not force higher
  (the operator owns the trade); a double-sign stays attributable and evictable at any size.
- **Lost** — Fork/brick exclusivity is priced between `threshold` and `2·threshold − signers`
  colluders, sliding with the attacker's partition reach. At a fork-cost-1 config one targeted
  witness (under a full partition) forks a position; at a large well-secured config the residual is
  negligible — the exposure is the operator's config choice.

### Cumulative lost-then-broken reserves — High

- **Attack** — Federation members' keys are lost (the operator can't rotate them) but left in the
  roster; an adversary breaks each lost key's reserve, mints a fresh clock-window per key, and
  cumulatively reaches the governance threshold — routing around the annual window expiry.
- **Mitigation** — Bounded only by removing lost keys promptly (a cut takes a lost key out of the
  count); an at-risk flag surfaces which member to remove. The annual expiry does **not** bound this
  path on its own.
- **Lost** — Federation governance control, if lost keys are left un-cut. Needs multiple lost keys,
  reserve breaks, and operator negligence together.

_(Escaping a compromised federation is **not a trap**, and not a residual: you rebind away with a
**`Wit`** declaring the new `{federation, federationPin}` — it self-bootstraps into the federation
it names, and the old one can't block it (witnesses can't author your events). You **keep your
prefix**. What you lose is only the graceful, no-disruption **overlap** migration (which leans on
the old federation being honest); against a compromised one you do a **synchronized hard cutover** —
all members `Wit`-rebind together. A reincept is only the fallback if you've \_also_ lost
`t_govern`, which is a separate problem.)\_

---

## 3. Eclipse and freshness

Detection is **eventual**, not synchronous: the witness beacon propagates a fork's evidence but
cannot certify the **absence** of one. But eclipse in VDTI is not a cheap network trick — you fetch
events from witnesses, so hiding data means compromising the witnesses you query. The universal
backstop is fail-secure refusal when freshness can't be confirmed.

### Eclipse at decision time — High

- **Attack** — Eclipse bites only when a fork **already exists** (someone with a key authored
  competing branches). Because you fetch events from witnesses / nodes, hiding the honest branch
  means an adversary must **control the witnesses you query and have them withhold records** — and
  multi-source means compromising _enough of your independent sources_ to withhold from all of them.
  If they succeed, you see and bind only the attacker's branch.
- **Mitigation** — Fail-secure: a chain that can't meet the multi-source freshness bar makes the
  decision **refuse** rather than proceed, so a partial eclipse yields a refusal, not a wrong bind.
  Fork _prevention_ is unaffected — only the detection leg is eclipsed, and only when a fork already
  exists. More independent sources make a full eclipse harder. (A "stale federation roster" is the
  same attack, not a separate one: a since-removed witness only hides anything if it is the
  compromised source you query — an honest one still returns the events, pinned to real federation
  events — so it collapses into this.)
- **Lost** — Under a successful full eclipse, decision-time fork-detection — the fail-secure posture
  turns it into a refusal (availability) rather than a wrong bind, and the divergence surfaces
  post-resolution when the partition heals.

### Consumer clock drifts backward — Medium

- **Attack** — A consumer whose wall clock drifts backward beyond `CLOCK_TOLERANCE_BAND` (via NTP
  failure or manipulation) reads stale as fresh and suppresses at-risk flags — silently defeating
  the dormant-forgery / backdate defense.
- **Mitigation** — Clock sync within `CLOCK_TOLERANCE_BAND` is a **deployment security control**,
  not best-effort; a live challenge-response path exists for when the federation is reachable and
  local-clock trust is undesirable. A verifier cannot defend against its own wrong clock.
- **Lost** — The entire backdate / dormant-forgery defense, for a clock-drifted consumer — an
  accepted deployment-invariant pushed to the operator.

### Just-closed-window staleness gap — Medium

- **Attack** — A key whose window closed **within** the consumer's staleness threshold can still
  stamp a receipt that reads fresh until the threshold elapses past the close; a harvested just-cut
  witness key gets a brief validity sliver.
- **Mitigation** — Tight staleness thresholds on high-value bindings; treat a recent cut as itself
  freshness-sensitive (demand extra-fresh confirmation near one).
- **Lost** — Freshness assurance for the just-closed-window interval — a time-granularity gap.

### Never-rotated witness (year-long window) — Medium

- **Attack** — A witness that never rotates keeps its receipt-signing window open for up to a year;
  a key harvested any time in that year stamps valid receipts until the auto-close.
- **Mitigation** — A hard annual cap (no unbounded open window); the operator can rotate sooner;
  once the window closes, a dormant forgery reads stale.
- **Lost** — Up to a year of soft-harvest exposure for a lazily-operated witness. Severity scales
  with operator laxity. (The flip side is a liveness cost: if **every** witness window lapses
  together, the federation reads stale — fail-secure — until a catch-up rotation lands.)

_(A future-dated federation clock — a governance-compromised federation setting the clock forward so
expired key-windows read open — is subsumed by the governance-compromise case: it presumes
governance is already breached, and consumers cap the clock at `now + CLOCK_TOLERANCE_BAND`, so its
extra reach is about a `CLOCK_TOLERANCE_BAND`. Not a standalone residual.)_

---

## 4. Issuance, delegation, and governance compromise

Compromises short of a reserve theft: bounded, revocable, or recoverable — but with real cost.

### Document governance-quorum compromise — High

- **Attack** — Compromising the **creator IEL's governance quorum** — its **`t_authorize`**
  threshold for grants and rescissions (`t_govern` on the **freeze** leg), a **quorum of rotation
  reserves** (T2), **not a single key** — captures the whole governance: the adversary can grant
  rogues, rescind honest members, or freeze the document.
- **Mitigation** — Grants and rescissions are **T2, reserve-backed** (`Gnt ← Ath` / `Trm ← Dth`,
  sealed on arrival, non-buriable), so a compromised creator **signing key (T1) cannot mint one** —
  minting reveals a rotation preimage. **One key is not enough** when `t_authorize > 1`; single-key
  governance is the avoidable degenerate. Recovery is to abandon and reincept a fresh document root
  (a new constitution `V0′`) seeded from the last good version, then notify relying parties; the old
  history stays verifiable. Member compromises, by contrast, are editor-local.
- **Lost** — Whole-document capture until reinception, whose successor legitimacy is out-of-band.

### Issuance signing-key compromise — Medium

- **Attack** — Issuance is a content-tier operation, so a compromised signing key can forge
  credentials in the issuer's name (no reserve needed).
- **Mitigation** — Bounded by the signer count (an issuer others rely on should require at least two
  signers), and every forged credential is a **revocable** assertion caught by the revocation walk
  once detected — not an ongoing authority expansion.
- **Lost** — Integrity of issuance during the window: an attacker mints revocable claims in the
  issuer's name until detected. Severity rises for a single-signer issuer.

### Editor signing-key compromise (a document) — Medium

- **Attack** — Within a compromised editor's open period, an adversary authors valid attributed
  versions as that member; they linger until the creator rescinds the period.
- **Mitigation** — Bounded and recoverable, not a whole-document reincept: the creator rescinds the
  compromised period and chooses where the boundary cuts — grandfather in-window work, or un-honor
  the malicious window at the cost of honest same-window versions — then re-adds on a fresh period
  after rotating the device.
- **Lost** — In-window malicious versions honored until rescission, plus a forced boundary trade
  (honest collateral vs malicious survival). Neither side is free.

---

## 5. Negative-check fail-open

"Is this revoked / rescinded / closed?" is answered by a **positive** match against a kill
declaration on the owner's chain. The default is fail-secure (walk the fresh chain; a withheld
object reads don't-honor). A consumer may deliberately **opt down** to a fast content-addressed
lookup — and that opt-down is where these residuals live. The opt is always down, never up.

### Fail-open negative-check opt-out — Medium

- **Attack** — A consumer that has opted down to the fast lookup treats a not-found as best-effort
  not-killed. An adversary who withholds (or eclipses the fetch of) the lookup object makes a
  revoked credential, rescinded delegation, or closed subject read as valid.
- **Mitigation** — Fail-secure is the default; the authoritative kill declaration is un-withholdable
  on the witnessed chain; the fast lookup's existence-check is a conservative proxy that errs toward
  over-refusal. The opt-down is the consumer's own latency-vs-soundness choice, made at the
  application layer.
- **Lost** — For an opted-down consumer: a killed subject read as valid when the object is withheld.

### Fail-open on a mis-tuned walk timeout — Medium

- **Attack** — A consumer runs the fail-secure walk under a timeout; an adversary induces latency so
  it times out. If the consumer's policy fails open on timeout, a killed subject slips through the
  truncated read.
- **Mitigation** — Default is fail-secure on timeout "where it matters"; the walk is bounded with no
  lossy cap. The authoritative path is the completed fresh-chain walk.
- **Lost** — A consumer whose timeout policy fails open accepts a killed subject under induced
  latency. "Where it matters" is an operator judgment, not a chain guarantee.

### As-issued resolve skips the to-tip step — High

- **Attack** — An adversary who compromises an issuer's key forges a clean linear extension of a
  dormant chain (no divergence to detect). A consumer that runs only the was-this-validly-issued
  resolve, and **skips** the mandatory to-tip freshness step, accepts a credential whose issuer is
  actually diverged or stale.
- **Mitigation** — The to-tip freshness step is **mandatory** for any trust-granting acceptance;
  as-issued alone is declared insufficient. Performed, it catches the extension via the staleness
  flag and the divergence / revocation checks, all fail-secure.
- **Lost** — Safety here rests on implementors honoring "mandatory." A consumer that binds on
  as-issued alone accepts a forged dormant extension.

---

## 6. Correlation and privacy

Addressing is correlation-resistant by construction: a record's identifier is not its chain address,
chains are walked by prefix, and a derived lookup address is a hash of a high-entropy input. The
residuals are the edges of that construction — a leaked prefix, a low-entropy input, a missing
nonce, or the standing exposure to the federation infrastructure that must route the traffic.

### Offline hash-match oracle (nonce omitted) — High

- **Attack** — A record's identifier does **not** transitively protect its referenced sub-records: a
  gated grant entry, rescind record, or private version is fetchable by its identifier. If such a
  record lacks a high-entropy nonce, an adversary who knows candidate content (a member prefix plus
  a known public group) composes it, hashes it, and compares to the committed public identifier — an
  offline confirmation oracle that de-anonymizes named members. Store-side "denied looks like
  absent" cannot defend an identifier already public on the chain.
- **Mitigation** — Every gated record on public structure must carry its own read policy **and** a
  high-entropy nonce, so the identifier is not reconstructable. The framework provides the slot; it
  cannot force an application-builder to populate it.
- **Lost** — If the nonce is omitted, offline de-anonymization of members — no chain access needed
  beyond public identifiers. Closed by construction when the nonce is present.

### Lookup-prefix exposure to federation infra — Medium

- **Attack** — Because a lookup data log is now witnessed, its prefix rides its own receipt onto the
  witness mesh. A federation member (or a below-threshold mesh compromise) that already knows a
  candidate subject can confirm the issuer-to-subject correlation by matching the prefix it
  observes, and could exfiltrate the set of prefixes it holds during a compromise window before it
  is cut.
- **Mitigation** — The prefix is unguessable and decorrelated from the public issuance and kill
  values (confirm-a-known-subject only, never invert or bulk-enumerate); all mesh traffic is
  encrypted, so exposure is to federation members only, under the below-threshold assumption; the
  data-bearing inception is never published, so the credential identifier never reaches a witness.
- **Lost** — A bounded confirm-a-known-subject correlation of lookup activity, exposed to
  semi-trusted infrastructure — and, during a compromise window, exfiltration of the prefix set it
  holds. Never the subject identity itself.

### Prefix leak → whole-chain correlation — Medium

- **Attack** — The whole correlation-resistance rests on the prefix staying secret and events being
  addressed by prefix. If an identity's prefix leaks — published, logged in a request line, or
  observed on the mesh — an observer can walk the entire chain and correlate every event to that
  identity.
- **Mitigation** — The prefix rides in the request body, never the address, to stay out of proxy
  logs; the record-identifier and prefix are separate hashes, so a logged identifier is not the
  prefix; there is no identifier-to-event index. None of this helps once the prefix itself is out.
- **Lost** — Correlation of an entire identity's history once its prefix leaks. Prefix
  confidentiality is an operational, not cryptographic, boundary.

### Low-entropy `data` → address brute-force — Medium

- **Attack** — A lookup or kill-check address is a hash of `(owner, topic, data)`; owner and topic
  are low-entropy. If the `data` input is also guessable, an adversary brute-forces the address and
  probes the store as an existence / status oracle, confirming relationships the scheme means to
  keep opaque. Hashing a low-entropy input does not help — the **input** must carry the entropy.
- **Mitigation** — Where the prefix must be unpredictable, `data` must be high-entropy; for
  credentials it is a full record identifier (high-entropy by construction). Discoverable lookup
  addresses are instead protected by owner-rooting, not entropy.
- **Lost** — For a guessable `data`, an existence / status oracle for that locus. Closed by the
  entropy discipline; a weak input reopens it.

### Confirm-a-known-subject revocation status — Low

- **Attack** — A party who already holds a subject's grant instance can compute its kill target and
  confirm whether that specific subject is revoked, even without being the intended verifier.
- **Mitigation** — You cannot invert a target back to a subject or bulk-enumerate an issuer's list;
  for a private subject whose grant instance stays secret, it never appears on the public chain, so
  a non-holder can compute nothing.
- **Lost** — The minimum disclosure needed to make revocation checkable at all: confirm what you
  already hold. Fully closed for private subjects.

### Lower-cost correlation edges — Low

- **Issuance volume / timing** — A passive observer of a public chain sees issuance volume and
  timing even though the anchors are opaque; folding issuances into mixed anchors muddies
  per-credential counts. Leaks aggregate activity, never which credential or to whom.
- **Sub-record identifier as a correlation handle** — Every sub-record is separately addressable by
  identifier, so collecting identifiers across disclosures reveals a composed record's shape and
  lets any ungated leaf be fetched. A read policy plus nonce on each gated child closes the content
  leg; the shape is the accepted price of partial disclosure.
- **Document metadata to a mesh witness** — A witness sees a creator-to-document link and
  per-participant volume/timing for a private document, but never the member identities or the
  membership graph (the rescission key is participant-blind and grant-blind; member names live
  behind gated, high-entropy identifiers).

---

## 7. Confidentiality is operational, not cryptographic

The read gate controls **access through the store**, not the readability of bytes that have escaped
it. There is no content encryption tied to a read policy (that is a forward direction).

### Leaked bytes of a gated record are readable — Medium

- **Attack** — An adversary who obtains the raw bytes of a read-gated record out-of-band (a
  misconfigured replica, a leaked cache, a compromised storage node, or a prior authorized reader
  who kept a copy) can read the plaintext. Any authorized co-author can likewise exfiltrate.
- **Mitigation** — Downstream verifiers re-check the read policy against their **own** verified
  identity set, so leaked bytes can't be presented as an authorized read; the gate keeps the
  canonical read-set uniform (an integrity property). For confidentiality, encrypt.
- **Lost** — Plaintext confidentiality of a gated record once bytes escape — the gate is
  operational, not a cryptographic seal.

### One-shot delivery isn't a deletion guarantee — Low

- **Attack** — A one-shot record instructs the store to delete after the first read; it says nothing
  about what the first reader does with the bytes it already holds.
- **Mitigation** — Server-side deletion after first read; a uniform "not present" afterward. Bounds
  re-fetch from storage, not the retained copy.
- **Lost** — No post-retrieval guarantee: a single authorized read can retain the content forever.

---

## 8. Finality and recovery cost

The design chooses structural finality over fuller recovery: a sealed kill is never retracted, a
co-signed event never un-signed, a dead prefix never restored in place. These are deliberate costs,
not gaps — retroactive undo would be a strictly worse weapon (a backdating kill-switch).

### Inherited deadness severs a data log — Medium

- **Attack** — When an owner's chain branch goes dead (buried by a recovery rotation), every
  data-log event anchored on the dead portion is severed at the earliest dead anchor; with no repair
  event, the portion after it is un-verifiable and lost.
- **Mitigation** — This is the price of full deadenability with no repair machinery: a content-tier
  compromise is fully recoverable by one rotation burying the whole tail, and every anchored event
  on it dies on ascent. The severed portion is a truncation, not a new state; the pre-sever portion
  stays live; a data log that pre-exists the fork is untouched.
- **Lost** — A bounded, un-verifiable tail: legitimate data-log work anchored during a since-buried
  window, which must be re-anchored on the recovered branch.

### Mis-set rescission bound (set once) — Medium

- **Attack** — An operator sets a rescission boundary wrong: too high grandfathers malicious
  in-window work, too low un-honors honest work. A sealed kill is never retracted, so the boundary
  can't be rewound.
- **Mitigation** — The boundary is security-critical usage doctrine (when the loss time is unknown,
  cut at genesis); the not-interleaved guarantee means a correctly-set boundary catches exactly the
  distrusted tail. A mis-set boundary is recovered operationally (reincept / reissue), never by
  retracting the kill.
- **Lost** — A mis-set boundary is unfixable in place; the operator eats either malicious survival
  or honest collateral and recovers operationally.

### Delegation-scope surprises — Medium

- **Rescinding one delegator doesn't stop a sub** — There is no cross-chain clock: each hop's
  grandfather is judged by its committed grant position. So rescinding a delegator does **not**
  automatically stop a sub-delegate it granted before the boundary — grandfathered credentials keep
  issuing. To actually stop it, the boundary must be moved before that grant. The mechanism is
  correct; the residual is an operator mental-model gap.
- **An intermediate delegator is routable-around** — Only the root delegator terminates every chain;
  an intermediate rescinds only credentials whose committed path runs through it. A credential
  routed around it isn't stopped by it. The root is the universal backstop; threshold issuance
  spanning several legs gives several parties kill authority.
- **No single-credential revoke of a rescinded issuer** — Once an issuer is rescinded, you can't
  revoke just one grandfathered credential of it (a boundary removes a contiguous suffix, not a
  non-contiguous subset). Recovery is to reincept the delegate. The accepted cost of the clean
  contiguous-boundary model.

### Burying rotation orphans a dependent anchor — Medium

- **Attack** — A seal locks a chain's own content against burial within that chain, but not that
  event's lower-layer anchors. An owner's burying rotation can bury content that a dependent chain
  anchored, leaving that dependent event verifiably broken.
- **Mitigation** — No cross-layer seal-vouched shortcut: the verifier always fully walks and
  re-resolves every anchor, so the break is detectable. The design target is end-verifiability of
  whatever state exists, not pristine data; recovery is operational (reissue).
- **Lost** — Integrity of a dependent event whose anchor is buried — detected, not prevented;
  recovered operationally.

### Lower-cost finality costs — Low

- **Retroactive per-event distrust is forbidden** — An event the quorum co-signed alongside a member
  later found compromised **stands**; remediation is forward (revoke its grants, evict the member).
  Undoing it would be a backdating kill-switch. Cost is forward-remediation effort.
- **Below-seal sealed straggler is dropped** — A competing sealed event that arrives below an
  established seal (after an eclipse or long partition) is dropped rather than honored — the defense
  that stops a total-key-compromise adversary from minting a fabricated historical fork years later.
  Cost is a rare legitimately-late sealed event.
- **Reinception loses the prefix** — A killed or rescinded prefix is permanently capped; restoration
  is a new prefix plus fresh grants, and every binding to the old one must be re-established. A
  deliberate finality with a real operational cost.

---

## 9. Availability, caps, and DoS bounds

Deliberate ceilings that trade a capability or some liveness for a bounded resource surface. Most
are not exploitable breaks — they are the bounds themselves.

### Value-bearing lookup DoS (collusion-forced) — High

- **Attack** — A value-bearing lookup — a system capability like a receive key, with no fallback
  path — has the data log's own live state as its sole authority. Witness collusion that forces that
  locus into dispute (dead) is a genuine denial of secure-receive: a sender can't safely pick a key
  and fails closed.
- **Mitigation** — A monotonic lineage field lets the owner re-establish a live key at the same
  discoverable address (the walk advances past dead lineages), capped at a fixed bound past which
  the read fails secure. (A non-owner cannot pre-empt the address: a data-log event is committed
  only batched with its owner-signed anchor, so an unanchored forgery never lands.)
- **Lost** — Availability of secure-receive at that address until the owner reincepts a fresh
  lineage — a bounded interruption, not a permanent loss, and it requires witness collusion to
  force.

### Anonymous-write flood (operator gate) — Medium

- **Attack** — An anonymous write carries no writer attestation; acceptance is gated only by
  operator-configured policy (open with rate-limits by default). A permissive deployment accepts
  unattested writes bounded only by rate limits, so an adversary floods storage / drop-box slots.
- **Mitigation** — The operator write-gate (rate-limits by default, credential-or-policy-gated under
  lockdown); identifier idempotency prevents repeat-submit inflation; two-phase storage bounds
  amplification.
- **Lost** — Spam / DoS resistance on anonymous writes is an operator-configuration property, not a
  protocol floor.

### Referenced content expires or is withheld — Medium

- **Attack** — A parent commits to a sub-record by identifier; the sub-record's retention window
  expires (or it is withheld) and it is garbage-collected. A later verifier that must expand the
  reference gets "not present," indistinguishable from never-existed.
- **Mitigation** — Author-controlled retention; the identifier commitment stays tamper-evident (the
  reference is valid, only the bytes are gone). For a kill-check, this ambiguity is exactly what the
  fail-secure / fail-open posture absorbs.
- **Lost** — Availability of still-referenced content — retention is an operational window, not a
  guarantee the bytes remain fetchable for the life of the reference.

### Lower-cost availability bounds — Low

- **Caps** — The roster is capped (a memory-exhaustion backstop for the verifier's on-walk rebuild),
  and content between seals is capped (forcing a periodic re-seal so a fork plus its burying seal
  fit one validation page). Each trades an unbounded capability for a bounded surface; each bites
  only unusually large use. (Federation **rebinds** are **not** capped per chain — an over-long
  rebind chain is refused by the general verification work bound, not a dedicated cap.)
- **Bounded dead-branch flood** — A content-tier adversary extending a dead branch spews events that
  are never canonical but are still propagated and retained — bounded on both axes (a depth cap per
  lineage forcing resolution, and retain-at-least-two-per-position). A bounded waste, not a trust
  break.
- **Even-signers tie stalls a position** — An even split with no majority stalls the position
  fail-secure (consistency over availability); a minority partition therefore stalls, never forks.
  Odd-signer guidance avoids the pure tie; a burying seal-advancer is the exit.
- **Self-denying dangling-parent flood** — Flooding versions that name parents a verifier doesn't
  hold forces bounded fetch work, but a junk flood denies only the flooder's own placement — it
  can't brick the document or deny others.

---

## 10. Degenerate configurations and bootstrap

Costs of the smallest configurations and of the trust roots that, by necessity, sit outside the
witnessing model.

### Two-member identity freeze — Medium

- **Attack** — At two members, the security floor forces every authority threshold to two — so the
  recoverability ceiling (needing fewer than all members to evict) can't also hold. A single
  compromised or lost device then withholds consent and freezes governance and recovery
  indefinitely, until reinception.
- **Mitigation** — The verifier **accepts** the two-device configuration (it is the forced common
  case) and the wallet **warns** to add a third key to become recoverable; at three or more, a
  threshold equal to the whole roster is rejected as a gratuitous hostage.
- **Lost** — Recoverability of a two-member identity — an indefinite freeze forcing reinception.
  Reversible by adopting a third key beforehand. (The single-key degenerate case is similar and is
  the accepted floor; replicating a rotation reserve across partitionable nodes is a related
  self-inflicted false-dispute the operator must avoid.)

### Unwitnessed genesis / config-pinned root — Medium

- **Attack** — A federation's genesis is unwitnessed — there is no earlier root to witness it.
  Anyone can stand up a well-formed federation; trust rests entirely on whether its prefix is in a
  consumer's config-pinned set, which is distributed out-of-band.
- **Mitigation** — Trust equals config-pinned membership; being well-formed is not being trusted;
  the prefix is a commitment to the founding roster and threshold. A federation a consumer hasn't
  pinned earns nothing.
- **Lost** — Out-of-band trust-root establishment: a consumer with a wrong or compromised config pin
  trusts the wrong federation. The inherent bootstrap axiom.

### Competing document root is always mintable — Medium

- **Attack** — A document root is anonymous-write, so its legitimacy is social. An adversary mints a
  competing root claiming to be the legitimate document or successor; nothing structural
  distinguishes the real one.
- **Mitigation** — By design, legitimacy is out-of-band; a holder of the real root
  self-authenticates any claimant against the prefix it derived. Reinception after a creator
  compromise deliberately has no structural link to the old root, which stays verifiable.
- **Lost** — No structural anti-forgery for a document root or successor — legitimacy rests on a
  social channel. (Relatedly, a creator can **name** a non-consenting party in a grant; the grief of
  being named is social and unmitigable, though authorship credit can't be fabricated.)

---

## 11. Owed work and unverified assumptions

Two forward items — a cross-implementation encoding discipline and a feature-layer obligation that
lands with the value-lookup feature. Neither is a known exploit.

- **Cross-implementation encoding drift — Low.** The synthetic marker for a forked or disputed state
  must be encoded byte-exactly across implementations; a drift would spin the anti-entropy loop
  until a node escalates to a by-prefix fetch (which bounds it). A liveness discipline, not a safety
  break.
- **Value-lookup lineaged-target discipline — Low (feature-layer, when the value-lookup feature
  lands).** A value rescission must declare the **matching lineaged** `kills[]` target; a rescission
  declaring only an on-chain `Trm`, or a non-lineaged / wrong-lineage target, leaves the kill on the
  **withholdable** leg, so a node missing that lineage's `Trm` reads the value live and serves a
  **stale** value. The primitive does not backstop this — it is a feature-layer obligation
  ([`sel/verification.md`](primitives/data/event-logs/sel/verification.md),
  [`sel/reconciliation.md`](primitives/data/event-logs/sel/reconciliation.md)).

---

## Cross-cutting assumptions

Nearly every residual above reduces to one of these standing assumptions. They are the load-bearing
premises of the whole design; naming them once keeps each entry honest about what it leans on.

- **The below-threshold byzantine assumption.** Witnesses are trusted not to be generally
  compromised. Concretely, forking or bricking a position takes a colluding quorum of **`threshold`
  witnesses, dropping to `2·threshold − signers` as a partition splits the redundancy onto the
  rival** — a floor of 1 at the enforced majority that a well-secured config lifts, so **many
  witnesses can fall and the attack still fails** as long as the colluding quorum isn't met.
  Rotation plus the provable double-sign make a breach detectable after the fact. This is the trust
  root; it is never traded for end-verifiability, which trusts only the data.
- **The current-state-compromise limit.** The design protects **past** state (finality, backdate
  defenses) and enables **forward** recovery (rotation, revocation, eviction). It does not protect
  the **present**: a compromised current key can author real, attributed state during its window. A
  **signing-key** compromise's content is **buriable and detectable** — the owner seals over the
  fork with a rotation, which the attacker, lacking the reserve, cannot counter — so what is
  **permanent** is only state the attacker can **seal**, and sealing needs the **reserve** (the
  takeover). Requiring multiple signers raises the bar; nothing erases what a **sealed** compromise
  commits.
- **Confidentiality is operational, not cryptographic.** Read policies and availability controls
  gate access **through the store**; they do not encrypt bytes against a party that already holds
  them. Content confidentiality against an authorized reader, a leaked byte stream, or a policy
  compromise is out of scope by design (encryption is the forward answer).
- **Negative checks fail secure by default; fail-open is a consumer opt-down.** The authoritative
  answer to "is this killed?" is a positive match on a walked fresh chain, where a withheld object
  reads don't-honor. A consumer may trade that soundness for latency by opting down to a fast
  lookup; the trade is the consumer's, always down and never up.
- **Entropy and nonce discipline are the author's to supply.** Unpredictability of a private address
  or the un-reconstructability of a gated identifier rests on a high-entropy input the framework
  provides a slot for but cannot force. A low-entropy input or an omitted nonce reopens brute-force
  and offline-oracle correlation.
- **Deployment invariants are the operator's to hold.** A consumer's clock synced within
  `CLOCK_TOLERANCE_BAND`, the correct config-pin set, promptly cutting lost keys, an odd and
  well-sized witness set, not replicating a reserve across partitionable nodes, and
  [monitoring one's own chain](monitoring.md) for unexpected activity — these are security controls
  the framework assumes but cannot enforce from inside the data. Monitoring is the one that turns
  the silent-takeover residuals from undetected into detected.

---

_This catalog is compiled from the current design. Its cost ranking is a first pass for review, not
a settled verdict; completeness and severity are both open to challenge. When a new mechanism lands
or a trade changes, its residual belongs here._
