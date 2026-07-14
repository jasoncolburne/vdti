# Glossary

An orientation cheat sheet: one-line definitions with a pointer to the doc that owns each idea. Two
parts — **Terms** (the named artifacts the system is built from) and **Concepts** (the principles
that govern how they behave). The definitions here orient a new reader; the **linked doc is
canonical** wherever they differ.

## Terms

### Primitives and data

- **SAD** — Self-Addressed Data: a serializable record whose own identifier is derived from its
  content; every content-bearing object in VDTI is a SAD. ([`sad.md`](primitives/data/sad/sad.md))
- **SAID** — Self-Addressing Identifier: the content-derived handle that names a SAD (a qualified
  Blake3-256 hash of its canonical bytes). ([`said.md`](primitives/data/sad/said.md))
- **prefix** — a chain's stable identifier, derived from its inception content and copied forward on
  every event; entities are named by prefix. ([`said.md`](primitives/data/sad/said.md#derivation))
- **KEL** — Key Event Log: a single device's chain of signed key events; the self-authorizing root.
  ([`kel/log.md`](primitives/data/event-logs/kel/log.md))
- **IEL** — Identity Event Log: one identity as a threshold over its member KELs; carries the roster
  and threshold vector.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#event-taxonomy))
- **SEL** — SAD Event Log: one owner's single-owner data log — its **own witnessed chain**, rooted
  in (and anchored to) an owning IEL. ([`sel/log.md`](primitives/data/event-logs/sel/log.md))
- **credential (cred)** — a bounded, revocable claim one identity issues to another; a
  **direct-anchored SAD** (the issuer anchors its issuance commitment on its own IEL), revoked by a
  `kills[]` declaration. ([`documents.md`](primitives/policy/documents.md))
- **document** — a standalone SAD carrying application content plus its authorization conditions.
  ([`documents.md`](primitives/policy/documents.md))
- **policy** — the authorization language that lives on a document (leaves + composers), never on a
  log primitive. ([`policy.md`](primitives/policy/policy.md))
- **manifest** — the SAID of a SAD that groups an event's upward commitments **by named role**.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role))
- **lookup-SEL** — a SEL whose **locus** — its derived lookup address (prefix) — is
  blind-recomputable from its inception content `(owner, topic, data)`; a revocation / rescission
  check reads it first (O(1), present → killed) and may fail-open on it — trusting a miss — instead
  of walking. ([`protocol-doctrine.md`](protocol-doctrine.md#negative-checks-are-positive-lookups))
- **custody** — a standalone SAD's per-object authority (who may write / read), via a top-level
  `custody` field (`owner` + `topic` writer-binding, anchored in a SEL; `readPolicy` read gate).
  ([`custody.md`](primitives/data/sad/custody.md))
- **availability** — a standalone SAD's per-object replication scope, TTL, and one-shot delivery.
  ([`availability.md`](primitives/data/sad/availability.md))

### Event kinds

The full set across KEL / IEL / SEL. A kind's precise role varies per log — the taxonomy tables are
authoritative. ([`event-shape.md`](primitives/data/event-logs/event-shape.md#event-taxonomy))

| Kind  | Meaning                                                                                                                                                                                                                                                                                                                                                              |
| ----- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `Fcp` | Founder / federation inception — a pre-federation founder KEL root, and the federation IEL's inception marker. Roots the spine; advances no seal.                                                                                                                                                                                                                    |
| `Icp` | Inception — a chain's first event (KEL device keys / IEL roster + thresholds / SEL data root). Roots the spine; advances no seal.                                                                                                                                                                                                                                    |
| `Ixn` | Interaction — content; anchors higher-layer SAIDs. The divergeable content kind — Tier 1, buriable (first-seen; on the SEL the `Pin` re-pin is tier-1 too). A SEL `Ixn` **always** carries payload (required) — a pure re-pin is a `Pin`.                                                                                                                            |
| `Rot` | Rotation (KEL) — reveals the next signing key, commits the next reserve; signed with the reserve. Tier 2, seal-advancing.                                                                                                                                                                                                                                            |
| `Wit` | Witness / federation — a user chain's federation (re)bind, or federation-IEL governance (witness rotation + roster). It **is** the rotation. Tier 2, seal-advancing.                                                                                                                                                                                                 |
| `Evl` | Evolve (IEL) — a roster / threshold change, carried as a delta; a `cut` `Evl` also evicts. Tier 2, `t_govern`, seal-advancing.                                                                                                                                                                                                                                       |
| `Ath` | Authorize (IEL) — the "authorize a party to act" anchor. Carries `delegates` (a positive inclusion list of delegate prefixes) and/or `anchors` (the SEL `Gnt` grant it seals). Tier 2, `t_authorize`, seal-advancing.                                                                                                                                                |
| `Gnt` | Grant (SEL) — seals a **typed value**: `manifest.grant` names a grant-value SAD kinded under `vdti/sel/v1/grants/*`. A value-bearing lookup is established `{Icp, Gnt}` at T2 (the doc-membership grant and the exchange receive-key are instances). The additive twin of the SEL `Trm` rescission; anchored by an IEL `Ath`. Tier 2, `t_authorize`, seal-advancing. |
| `Sea` | Re-seal (SEL) — the **neutral** burying seal-advancer: advances the seal past a content fork without granting or terminating; anchored by an IEL `Evl` (`Sea ← Evl`). Tier 2, `t_govern`, seal-advancing.                                                                                                                                                            |
| `Rev` | Revoke (IEL) — the sealed kill-anchor for an **owned artifact**; carries a `kills[]` declaration and seals a SEL `Trm` that revokes a credential. Tier 2, `t_govern`, seal-advancing.                                                                                                                                                                                |
| `Dth` | Deauthorize (IEL) — the sealed kill-anchor for a **granted authorization**; carries a `kills[]` declaration and seals a SEL `Trm` that rescinds a delegation or doc-membership grant. Tier 2, `t_authorize`, seal-advancing.                                                                                                                                         |
| `Pin` | Pin (SEL) — the **pin-only re-pin** to the owner IEL's current tip at **any serial** (carries no manifest); its serial-1 instance is the issuance floor. A pure re-pin is always a `Pin`, never a payload-less `Ixn`. Tier 1.                                                                                                                                        |
| `Trm` | Terminate — terminal kill (KEL / IEL identity-kill; SEL revocation / closure / rescission). Tier 2, seal-advancing (terminal); `t_govern` (identity-kill / SEL revoke) or `t_authorize` (SEL rescind).                                                                                                                                                               |

### Chain structure

- **seal / seal-advancing event** — a sealed (tier-2) event that advances the chain's trust
  boundary; carries `previousSeal`. ([`system-thesis.md`](system-thesis.md#forks-are-seal-bounded))
- **locked portion** — the part of a chain before its most recent sealed event; structurally
  immutable within its own chain (a recovery cannot bury it). Each sealing event ratchets the lock
  forward. ([`protocol-doctrine.md`](protocol-doctrine.md#forks-are-seal-bounded))
- **sealing event** — the same object in its **act** sense: a tier-2 event that _seals the chain_
  (advances the seal) as it lands — on the KEL `Rot` / `Wit` / `Trm`, on the IEL `Evl` / `Ath` /
  `Rev` / `Dth` / `Wit` / `Trm`, on the SEL `Gnt` / `Trm` / `Sea` — a synonym of **seal-advancing
  event**. "**Sealed**" names the resulting state (a sealed branch, the sealed spine); "**sealing**"
  names the act (a sealing event advances the seal).
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#divergence-is-scoped-to-content))
- **spine** — the `previousSeal`-linked chain of seal-advancing events; a sealed divergence is a
  single visible spine fork.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#divergence-is-scoped-to-content))
- **content rail** — the tier-1 issuance stream a chain accumulates between seals (`Ixn` content
  carried via `anchors[]`); serializing it is a liveness discipline, not a safety one.
  ([`protocol-doctrine.md`](protocol-doctrine.md#forks-are-seal-bounded))
- **seal-cap** — the merge rule that a new event's parent must sit at-or-after the chain's tracked
  seal (`parent_serial >= seal_serial`); a submission whose parent sits in the locked portion is
  rejected as a canonical extension. The post-seal window is separately bounded — a busy chain
  re-seals — so a fork-and-recover always fits one page.
  ([`protocol-doctrine.md`](protocol-doctrine.md#forks-are-seal-bounded))
- **anchor** — a commitment from an event to the SAID of the layer above (manifest `anchors`);
  kind-strict both directions.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role))
- **pin / pins / federationPin** — an event's down-pins to the tips it depends on (a SEL's owner IEL
  event; an IEL's member KEL events; the as-of federation position).
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#cross-cutting-fields))
- **branch / competing branch / retained / losing branch** — the shapes of a divergence: the kept
  chain versus the buried ones. **"Retain" has two senses, disambiguated by context:** an entity
  **retains** the branch it keeps **canonical** (the recovery rule), while a buried loser is
  **retained** as non-canonical **evidence** (buried by position + ascent below a burying seal).
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **threshold vector** — an IEL's `{t_use, t_govern, t_authorize}` — the **count** an act of each
  kind requires (orthogonal to tier).
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#structural-authorization--the-three-mechanisms))
- **authorization floor** — the bound `t_govern, t_authorize > |roster|/2` (a strict majority of the
  roster), so any two authorizing quorums overlap and a sealed fork always names a double-dealer.
  Distinct from the witnessing floor (`> signers/2`, over witness signers).
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#structural-authorization--the-three-mechanisms))
- **forward-only floor** — a per-chain pin floor: a chain's down-pins never move backward, so
  authority can only ratchet to a later position (the emergent floor on `federationPin`; the SEL's
  serial-1 issuance floor). A **floor** in this sense is a position bound — distinct from the
  authorization / witnessing floors, which are threshold counts.
  ([`protocol-doctrine.md`](protocol-doctrine.md#pin-everything-to-current-floored-per-chain))
- **content (the SEL discriminator)** — `content: true` on a **content** SEL's `Icp` (its v1 an
  `Ixn` / `Pin`), **omitted** on a lookup (never present-and-false — a lookup omits the field
  entirely). Verifier-enforced against the v1's tier (the biconditional `content: true` ⟺ v1-T1),
  and it rides the whole-content prefix — so content and lookups derive to **distinct addresses**
  and a content squat at a lookup address is impossible by construction.
  ([`sel/log.md`](primitives/data/event-logs/sel/log.md#the-content-and-lineage-fields))
- **lineage** — a value lookup-SEL's **re-establishment counter** (`Icp` only), carried **only** by
  a **re-establishable value** lookup (base `lineage: 0`, then `1, 2, …`, each a distinct prefix). A
  deterministic-prefix SEL can't reroll a nonce to re-incept, so a rescinded value re-incepts at the
  next `lineage`. It is found by the **positive walk** — walk `lineage: 0, 1, …`, advance past a
  dead lineage — a `Trm` on that lineage's chain, `Disputed`, severed, **or** its **lineaged**
  `kills[]` target — and stop at the lowest live one (a `Trm` advances: it kills one lineage, not
  the address); cap `MAXIMUM_SEL_LINEAGE = 64`. A value rescission is a monotone `Trm` whose `Dth`
  declares the lineaged target `hash('…:{lineage}')`, so the positive walk **consumes** the
  per-lineage negative check. A **monotone** lookup (a cred revocation, a delegate / doc-member
  rescission, or a non-re-establishable value) carries no `lineage` field and a **non-lineaged**
  target, and **content** never carries `lineage` either (content uses `content: true`).
  Load-bearing for value-bearing lookups (a KEM key whose positive resolution has no owner-IEL
  fallback). ([`sel/log.md`](primitives/data/event-logs/sel/log.md#the-content-and-lineage-fields))
- **roster** — an identity's set of member prefixes (a delta on each change); for a federation, its
  witness KELs.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role))
- **governance** — the **narrow** roster/authority sense — **not** the whole sealed spine, and
  **not** the whole `t_govern` count class. It names the acts that reshape _who and how many_ govern
  an identity: a **roster / threshold change** (`Evl`) and the **federation** bind/rotation (the
  `Wit`). The kinds that draw their required count from `t_govern` are `Evl` / `Rev` / `Wit` /
  `Trm`, but a **kill** (`Rev` / `Dth`) and the **terminal** (`Trm`) are their **own** categories —
  the docs enumerate them separately ("establishment / governance / kill / terminal"). Every
  governance act **is** a sealing event; not every sealing event is governance. So "federation
  governance", "a governance act", and "governance-shaped payload" mean this narrow sense — never
  "any sealed event". ([`protocol-doctrine.md`](protocol-doctrine.md#structural-authorization))

### Federation and witnessing

- **federation** — a restricted IEL (`Fcp` / `Wit` / `Trm`) whose roster is witness KELs; it
  propagates and time-stamps, it never decides.
  ([`federation/bootstrap.md`](federation/bootstrap.md))
- **witness / receipt** — a federation member that signs a receipt over `(prefix, serial, said)`,
  the multi-source freshness evidence for a chain.
  ([`federation/witnessing.md`](federation/witnessing.md))
- **witnessing floor** — `threshold > signers/2`, a strict majority of the selected witnesses; it
  makes any two threshold-quorums at a position overlap, so a content fork cannot form.
  ([`federation/witnessing.md`](federation/witnessing.md))
- **fork-cost** — `2·threshold − signers`, the number of selected witnesses an attacker must own and
  expose to manufacture a fork on a witnessed chain.
  ([`federation/witnessing.md`](federation/witnessing.md))
- **beacon** — the receipt broadcast that enumerates a position's competing branches so a one-branch
  holder can fetch and walk them. ([`federation/witnessing.md`](federation/witnessing.md))
- **federation clock** — a coarse, consensus-attested timestamp (the `clock` role) that time-bounds
  witness key-windows for freshness. ([`federation/witnessing.md`](federation/witnessing.md))
- **gossip** — the witness-mesh transport: roster-wide push-gossip for witnessed events, and
  sub-gossip among a position's selected witnesses for one still gathering receipts; encrypted and
  roster-scoped. ([`federation/topics.md`](federation/topics.md))

### Chain states

- **Active / Forked / Disputed / Terminated** — the four per-node chain states, each **derived** by
  a data-local walk over the events a node holds, never a stored flag. **Active**: a linear, live
  chain. **Forked**: a live fork with ≤ 1 sealed branch past it — recoverable by a burying
  seal-advancer on the winning branch. **Disputed**: a fork with ≥ 2 **accepted** sealed branches at
  the last seal — terminal (reincept); a below-seal sealed straggler is dropped (backdate-safe).
  **Terminated**: killed by a `Trm`. Forked and Disputed are **distinct, detectable states** — the
  walk that tells them apart (≤ 1 vs ≥ 2 accepted sealed at the last seal) is how the state is
  computed, not a "reading" layered on one divergent state.
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **`Terminated` vs `Terminal` vs `Trm`** — three near-homographs, one letter apart, with distinct
  meanings: **`Terminated`** is the fourth chain **state** (a chain ended by a `Trm`);
  **`Terminal`** is the merge **rejection** for an event chaining _from_ a `Trm` (which admits no
  successor); **`Trm`** is the terminate **event kind**.
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **reincept** — the operational exit from a **Disputed** chain (or a federation schism): stand up a
  fresh prefix and rebind, since no divergent branch can be chosen. Recovery is forward — never a
  repair of the old prefix.
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))

## Concepts

- **end-verifiability over data-from-any-source** — trust attaches to the data (SAID + signature +
  linkage), not the source; a verifier recomputes rather than trusts.
  ([`system-thesis.md`](system-thesis.md#end-verifiability))
- **tamper-evidence** — a SAD's identity is its content hash, so any change surfaces as a SAID
  mismatch, transitively through the reference graph.
  ([`sad.md`](primitives/data/sad/sad.md#adversarial-framing))
- **the two tiers (T1 / T2)** — the cryptographic capability to forge an event, set by
  danger-or-permanence: the signing key (tier 1) or the rotation reserve (tier 2).
  ([`protocol-doctrine.md`](protocol-doctrine.md#tiers))
- **rotation reserve** — the tier-2 secret each event pre-commits (`rotationHash`) and the next
  `Rot` reveals; forging a key change needs the reserve, not the signing key. The reserve defends
  the signing key. ([`protocol-doctrine.md`](protocol-doctrine.md#tiers))
- **first-seen** — the merge policy for tier-1 content: the first structurally-valid sibling at a
  position wins and later ones are declined, so a content fork never goes live.
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **record-both** — the merge policy for tier-2 sealed events: competing **witnessed** sealed
  branches are both retained as evidence, so a sealed fork at the last seal surfaces as Disputed
  rather than being silently dropped (a below-seal straggler is dropped, backdate-safe).
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **deferred-pending** — a structurally-valid event held but **not yet accepted**: it has not
  reached threshold receipts (a witness-declined sibling, or a fresh submission still gathering
  receipts). It is retained and gossiped, does **not** advance the tip or seal, and is **never
  counted** toward a verdict — until it reaches threshold (then it re-enters routing) or is dropped.
  ([`merge.md`](primitives/data/event-logs/kel/merge.md#merge-outcomes))
- **Ignored** — the merge outcome for a well-formed event the witnesses **decline**: a second
  content or sealed sibling at a position, or an extension of a Disputed / Terminated chain. Nothing
  lands. ([`merge.md`](primitives/data/event-logs/kel/merge.md#merge-outcomes))
- **sealed event** — a tier-2 event; **seal-advancing** except the tier-2 inception (which roots the
  spine but advances no seal). Never buried or overturned.
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **divergence and recovery** — divergence is permanent and visible; recovery is a burying
  seal-advancer that buries the losing branch by position + ascent, scoped to tier-1 content.
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **the seal is the trust boundary** — everything at-or-below the last seal is final; a divergence
  above it grounds new trust only once cleanly sealed past.
  ([`system-thesis.md`](system-thesis.md#forks-are-seal-bounded))
- **resolution by tier, not identity** — chain data can't tell operator from adversary, so a
  divergence resolves on tier (which branch is sealed), never on presumed legitimacy.
  ([`system-thesis.md`](system-thesis.md#divergence-is-resolved-by-tier-a-divergent-chain-freezes-further-origination))
- **origination-freeze vs pure-walk reading** — a live fork freezes what a node originates, but the
  reading stays a pure function of held events (the seal derived from them).
  ([`system-thesis.md`](system-thesis.md#divergence-is-resolved-by-tier-a-divergent-chain-freezes-further-origination))
- **effective-SAID** — a single **confirmed** tip yields its real SAID; a chain with no single tip
  yields a type-tagged synthetic recoupled to the verdict (`forked` / `disputed`); the universal
  "has trust-relevant state changed?" key.
  ([`protocol-doctrine.md`](protocol-doctrine.md#effective-said-comparison))
- **confirmed tip** — a chain tip **witnessed at threshold (accepted)**; the acceptance boundary
  that Active and the effective-SAID's real-SAID arm read against. An unwitnessed or below-threshold
  tip is **not** confirmed (a non-witness never even holds a sub-threshold event — query-scoping).
  ([`protocol-doctrine.md`](protocol-doctrine.md#federation-convergence))
- **witnessed vs accepted** — **witnessed**: a selected witness signed a first-seen receipt.
  **accepted**: witnessed **at threshold** (a `confirmed tip`). The Active / `Disputed` boundary and
  the effective-SAID read against **accepted**, never merely witnessed — `Disputed` needs ≥ 2
  **accepted** sealed branches (which is why it takes collusion / a provable double-sign), and a
  below-seal or sub-threshold sealed event is witnessed-but-not-accepted → dropped, never
  `Disputed`. ([`protocol-doctrine.md`](protocol-doctrine.md#federation-convergence))
- **keep-all-data / data-local detection** — nodes retain competing branches as evidence, so any
  verifier detects a fork or dispute from the data alone.
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **burial by position / deadness-ascends** — a losing branch is dead from its first-seen loss (or
  below a burying seal); its whole subtree is **dead on ascent**, so later growth needs no follow-up
  — and a seal forged on a dead lineage is dead too (**you can't seal a buried chain**), which
  collapses every dispute to a same-position seal fork.
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **severance / truncation** — when an owner IEL buries a branch a SEL is anchored to, the SEL is
  **severed** at the earliest dead anchor: the post-sever portion can't be tied to a live anchor
  lineage, so it is un-verifiable — a **truncation** (the SEL shrinks to its last live-anchored
  event), not a fifth chain state, and there is no repair.
  ([`sel/log.md`](primitives/data/event-logs/sel/log.md#severance--a-dead-owner-iel-anchor-truncates-the-sel))
- **kind-strict anchor matrix** — each higher-layer kind is anchored by exactly the lower kind that
  reveals the matching capability; no higher-tier stand-in.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role))
- **fork-cost / witnessing floor** — a strict witness majority (`threshold > signers/2`) makes two
  conflicting **same-kind** siblings (content or sealed) un-co-witnessable, preventing the fork.
  ([`protocol-doctrine.md`](protocol-doctrine.md#federation-convergence))
- **position gate** — first-seen witnessing at a chain's own `(prefix, serial)` — the **universal**
  fork-prevention primitive, applied to **every event, content _and_ sealed**. On a keyless IEL it
  is stated explicitly (the witnessing floor `> signers/2` at its own position), so two disjoint
  member sub-quorums cannot both land an event at one IEL serial; a KEL gets it for free (its own
  key is witnessed at the KEL position directly); the federation IEL realizes it via exclude-self
  peer-witnessing.
  ([`merge.md`](primitives/data/event-logs/iel/merge.md#the-content-versus-sealed-split))
- **negative checks are fail-secure declarations** — "is X revoked / rescinded?" is a positive
  lookup, never a scan-for-absence. A check reads the derived lookup-SEL first (O(1), present →
  killed); on a **miss** it is **fail-secure by default** — confirm by forward-matching X's derived
  `target` (which **mirrors the killed address** — non-lineaged for a monotone kill, lineaged
  `…:{lineage}` for a value rescission, `:content` for a content app-SEL closure) in the `kills[]`
  on the owner's fresh witnessed IEL — with **fail-open** (trust the miss) as the opt-out, never up.
  ([`protocol-doctrine.md`](protocol-doctrine.md#negative-checks-are-positive-lookups))
- **as-of authority / pin-everything-to-current** — authority is judged by the append-only anchoring
  position, never a self-asserted pin; every event pins its dependencies' current tips.
  ([`documents.md`](primitives/policy/documents.md#the-anchoring-position--fixing-the-issuer-context))
- **as-issued vs current** — the two document-evaluation modes: authority as of issuance, or live at
  the current tip.
  ([`evaluation.md`](primitives/policy/evaluation.md#one-shared-composer-two-leaf-resolvers))
- **correlation resistance** — deriving `prefix` and `said` via two hashes keeps a logged inception
  SAID from leaking the chain's lookup key. ([`said.md`](primitives/data/sad/said.md#derivation))
- **fail-secure, not safe** — under partition or missing evidence a loss-of-trust decision refuses
  rather than proceeds; disagreement drives a fetch, never false agreement.
  ([`system-thesis.md`](system-thesis.md#fail-secure-not-safe))
- **the verifier is the trust boundary** — every chain-validity rule lives in the verifier walk;
  services, databases, and peers are never trusted.
  ([`system-thesis.md`](system-thesis.md#the-verifier-is-the-trust-boundary))
- **compromise is permanent** — a key compromise can't be un-done retroactively; remediation is
  forward (rotate, revoke, evict, reincept).
  ([`system-thesis.md`](system-thesis.md#compromise-is-permanent))
