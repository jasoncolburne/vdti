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
- **SEL** — SAD Event Log: one owner's single-owner data log, rooted in an owning IEL.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#event-taxonomy))
- **credential (cred)** — a bounded, revocable claim one identity issues to another; a
  **direct-anchored SAD** (the issuer anchors its issuance commitment on its own IEL), revoked by a
  `kills[]` declaration. ([`documents.md`](primitives/policy/documents.md))
- **document** — a standalone SAD carrying application content plus its authorization conditions.
  ([`documents.md`](primitives/policy/documents.md))
- **policy** — the authorization language that lives on a document (leaves + composers), never on a
  log primitive. ([`policy.md`](primitives/policy/policy.md))
- **manifest** — the SAID of a SAD that groups an event's downward commitments **by named role**.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role))
- **lookup-SEL** — a SEL whose locus is blind-recomputable from `derive(owner, topic, data)`; it
  backs the fail-open O(1) opt-out of a revocation / rescission check.
  ([`protocol-doctrine.md`](protocol-doctrine.md#negative-checks-are-positive-lookups))
- **custody** — a standalone SAD's per-object authority (who may write / read), via a top-level
  `custody` field (`owner` + `topic` writer-binding, anchored in a SEL; `readPolicy` read gate).
  ([`custody.md`](primitives/data/sad/custody.md))
- **availability** — a standalone SAD's per-object replication scope, TTL, and one-shot delivery.
  ([`availability.md`](primitives/data/sad/availability.md))

### Event kinds

The full set across KEL / IEL / SEL. A kind's precise role varies per log — the taxonomy tables are
authoritative. ([`event-shape.md`](primitives/data/event-logs/event-shape.md#event-taxonomy))

| Kind  | Meaning                                                                                                                                                                                                      |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `Fcp` | Founder / federation inception — a pre-federation founder KEL root, and the federation IEL's inception marker.                                                                                               |
| `Icp` | Inception — a chain's first event (KEL device keys / IEL roster + thresholds / SEL data root).                                                                                                               |
| `Ixn` | Interaction — content; anchors lower-layer SAIDs. The divergeable content kind — tier-1, buriable (first-seen; on the SEL the floor `Pin` is tier-1 too).                                                    |
| `Rot` | Rotation (KEL) — reveals the next signing key, commits the next reserve; signed with the reserve. Tier 2, seal-advancing.                                                                                    |
| `Wit` | Witness / federation — a user chain's federation (re)bind, or federation-IEL governance (witness rotation + roster). It **is** the rotation. Tier 2, seal-advancing.                                         |
| `Evl` | Evolve (IEL) — a roster / threshold change, carried as a delta; a `cut` `Evl` also evicts. Tier 2.                                                                                                           |
| `Ath` | Authorize (IEL) — the "authorize a party to act" anchor. Carries `delegates` (a positive inclusion list of delegate prefixes) and/or `anchors` (the SEL `Gnt` grant it seals). Tier 2, `t_authorize`.        |
| `Gnt` | Grant (SEL) — a doc-membership grant; opens editor / commenter validity periods. The additive twin of the SEL `Trm` rescission; anchored by an IEL `Ath`. Tier 2, seal-advancing.                            |
| `Rev` | Revoke (IEL) — the sealed kill-anchor for an **owned artifact**; carries a `kills[]` declaration and seals a SEL `Trm` that revokes a credential. Tier 2, `t_govern`.                                        |
| `Dth` | Deauthorize (IEL) — the sealed kill-anchor for a **granted authorization**; carries a `kills[]` declaration and seals a SEL `Trm` that rescinds a delegation or doc-membership grant. Tier 2, `t_authorize`. |
| `Pin` | Pin (SEL) — the floor re-pin to the owner IEL's current tip; carries a SEL's serial-1 issuance floor. Tier 1.                                                                                                |
| `Trm` | Terminate — terminal kill (KEL / IEL identity-kill; SEL revocation / closure / rescission).                                                                                                                  |

### Chain structure

- **seal / seal-advancing event** — a sealed (tier-2) event that advances the chain's trust
  boundary; carries `previousSeal`. ([`system-thesis.md`](system-thesis.md#forks-are-seal-bounded))
- **spine** — the `previousSeal`-linked chain of seal-advancing events; a sealed divergence is a
  single visible spine fork.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#divergence-is-scoped-to-content))
- **anchor** — a commitment from an event to the SAID of the layer below (manifest `anchors`);
  kind-strict both directions.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role))
- **pin / pins / federationPin** — an event's up-pins to the tips it depends on (a SEL's owner IEL
  event; an IEL's member KEL events; the as-of federation position).
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#cross-cutting-fields))
- **branch / competing branch / retained / losing branch** — the shapes of a divergence: the kept
  chain versus the buried ones (buried by position + descent below a burying seal, retained as
  non-canonical evidence). ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **threshold vector** — an IEL's `{t_use, t_govern, t_authorize}` — the **count** an act of each
  kind requires (orthogonal to tier).
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#tiers--the-two-tier-capability-model))
- **roster** — an identity's set of member prefixes (a delta on each change); for a federation, its
  witness KELs.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role))

### Federation and witnessing

- **federation** — a restricted IEL (`Fcp` / `Wit` / `Trm`) whose roster is witness KELs; it
  propagates and time-stamps, it never decides.
  ([`protocol-doctrine.md`](protocol-doctrine.md#federation-convergence))
- **witness / receipt** — a federation member that signs a receipt over `(prefix, serial, said)`,
  the multi-source freshness evidence for a chain.
  ([`system-thesis.md`](system-thesis.md#federation-convergence))
- **beacon** — the receipt broadcast that enumerates a position's competing branches so a one-branch
  holder can fetch and walk them.
  ([`protocol-doctrine.md`](protocol-doctrine.md#federation-convergence))
- **federation clock** — a coarse, consensus-attested timestamp (the `clock` role) that time-bounds
  witness key-windows for freshness.
  ([`protocol-doctrine.md`](protocol-doctrine.md#federation-convergence))

### Chain states

- **Active / Forked / Disputed / Terminated** — the four per-node chain states, each **derived** by
  a data-local walk over the events a node holds, never a stored flag. **Active**: a linear, live
  chain. **Forked**: a live fork with ≤ 1 sealed branch past it — recoverable by a burying
  seal-advancer on the winning branch. **Disputed**: a fork with ≥ 2 sealed branches — terminal
  (reincept). **Terminated**: killed by a `Trm`. Forked and Disputed are **distinct, detectable
  states** — the walk that tells them apart (≤ 1 vs ≥ 2 sealed past the fork) is how the state is
  computed, not a "reading" layered on one divergent state.
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
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#tiers--the-two-tier-capability-model))
- **sealed event** — a tier-2 event; **seal-advancing** except the tier-2 inception (which roots the
  spine but advances no seal). Never buried or overturned.
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **divergence and recovery** — divergence is permanent and visible; recovery is a burying
  seal-advancer that buries the losing branch by position + descent, scoped to tier-1 content.
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
- **effective-SAID** — a single confirmed tip yields its real SAID; a chain with no single tip
  yields a type-tagged synthetic recoupled to the verdict (`forked` / `disputed`); the universal
  "has trust-relevant state changed?" key.
  ([`protocol-doctrine.md`](protocol-doctrine.md#effective-said-comparison))
- **keep-all-data / data-local detection** — nodes retain competing branches as evidence, so any
  verifier detects a fork or dispute from the data alone.
  ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **burial by position / deadness-descends** — a burying seal-advancer locks the losing branch's
  first event below the seal; its whole subtree is dead by descent, so later growth needs no
  follow-up. ([`reconciliation.md`](primitives/data/event-logs/kel/reconciliation.md))
- **kind-strict anchor matrix** — each lower-layer kind is anchored by exactly the upper kind that
  reveals the matching capability; no higher-tier stand-in.
  ([`event-shape.md`](primitives/data/event-logs/event-shape.md#the-manifest--what-an-event-commits-to-grouped-by-role))
- **fork-cost / majority floor** — a strict witness majority (`threshold > signers/2`) makes two
  conflicting content siblings un-co-witnessable, preventing the fork.
  ([`protocol-doctrine.md`](protocol-doctrine.md#federation-convergence))
- **negative checks are fail-secure declarations** — "is X revoked / rescinded?" is answered by
  forward-matching X's derived `target` in the `kills[]` on the owner's fresh witnessed IEL
  (fail-secure by default), with a fail-open O(1) lookup-SEL read as the opt-out — never a
  scan-for-absence.
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
