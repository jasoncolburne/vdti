# Blocking a prefix — the last resort against a valid-identity flood

[Rooting](../../primitives/data/sad/rooting.md) makes the SAD store refuse data that no accepted
root vouches for, and it raises the cost of a **fake** identity. It does nothing about a **real**
one: a resourced adversary can incept prefixes, anchor SADs on their own chains, and flood the store
with perfectly valid, rooted data. The per-prefix event budget bounds one prefix and the per-IP
limit bounds one address, but neither bounds a spammer spread across many of each. The last resort
is collective and local: **a federation can refuse to witness an abusive prefix.**

This is the decentralized answer to "how do you stop a valid spammer." There is no global authority
to ban anyone — that would not be decentralized — so a block is **local, quorum-gated, and
reversible**: a federation governs its own witnessing, declines to advance an abuser's chains, and
the abuser can always [rebind](witnessing.md#rebinding) to another federation and keep its prefix.
Accountable local refusal plus permissionless escape is the shape decentralization actually admits.

## What a block does, and does not

A block withholds **advancement**, never **information**:

- **It stops witnessing.** Once a prefix is blocked, the federation's witnesses decline to witness
  that prefix's new events ([§The witness check](#the-witness-check)), so it can no longer advance a
  chain — no new anchors, no new roots, no flood — in this federation. It is **forward-only**:
  already-witnessed history stands, exactly as everywhere else the design refuses retroactive
  change.
- **It never stops serving.** The store still serves every byte it already holds, always
  end-verifiable ([`rooting.md`](../../primitives/data/sad/rooting.md#adversarial-framing)). A block
  is about what the federation will _witness next_, not about hiding data — serving is never
  conditioned on a block.

## The mechanism — a per-prefix toggle at a derived address

A block is not a public list. Each denial is its own small **SEL** at an address **derived** from
the blocked prefix, owned by the federation:

`derive(authority = id(federation), topic = vdti/sel/v1/topics/block, data = blocked-prefix)`
([`../../primitives/data/event-logs/sel/log.md` §Prefix derivation](../../primitives/data/event-logs/sel/log.md#prefix-derivation)).

The block state **toggles**, reusing the re-establishable-value **lineage walk** the receive-key
directory already runs
([`../../primitives/data/event-logs/sel/verification.md` §The lineage walk](../../primitives/data/event-logs/sel/verification.md#the-lineage-walk)),
polarity inverted — because that walk is meaning-blind, the same machinery serves a receive key (a
live lineage means _available_) and a block (a live lineage means _blocked_):

- **Block on** — the federation incepts a lineage and seals it (`Icp` + `Gnt`, the `Gnt` carrying an
  optional **reason**), anchored by an **`Ath`** on the federation IEL.
- **Block off** — a **`Trm`** kills the live lineage, anchored by a **`Dth`**; the walk advances
  past the dead lineage to "no live lineage," which reads **not blocked**.
- **Re-block** — a fresh lineage at the next counter, block-on again.

Resolving is the ordinary lineage walk: the lowest **live** lineage reads **blocked** (carrying its
reason); a gap or an all-dead run below the cap reads **not blocked** — the determinate no-block
case, so an ordinary prefix is never caught. A prefix churned past `MAXIMUM_SEL_LINEAGE = 64` —
pathological, nothing legitimate toggles that often — reads **blocked, fail-secure**: the
indeterminate case denies.

The block is **reversible** and **monotone-until-toggled** — it never auto-expires (that would
silently un-block an abuser), only a `Dth`/`Trm` lifts it.

## `t_authorize` on the federation IEL

The federation IEL is a [restricted IEL](witnessing.md) that, until now, carries only its governance
`Wit`s (rotations and roster deltas, at `t_govern`). A block adds one capability: the federation IEL
**admits `Ath` / `Dth` at a `t_authorize` threshold** the federation configures — reserve-backed, so
a stolen signing key cannot forge a block, but lighter than full governance, so blocking stays
**agile**. The operators "agree" by meeting `t_authorize`; the federation sets it where it likes —
lower than `t_govern` for a fast response, higher for caution. Crucially, a federation's `Ath` /
`Dth` may anchor **only a `topics/block` grant / kill** — never a delegation: a federation grants
authority to no other identity, so trust stays per-federation and non-transitive, and a block on a
prefix is the one non-governance thing it authorizes. Everything else — first-seen, the witnessing
floor, the clock — is the federation IEL's existing machinery, unchanged.

## The witness check

Witnesses are reporters, not deciders ([`witnessing.md`](witnessing.md)) — and a block is a
reporter's decision about what to attest, so it rides the **signing** path, not the counting one.
Before a selected witness signs an event, alongside the structural-validity and seal-cap checks it
already runs, it **declines to witness an event authored by a blocked prefix**: it derives the block
address from the event's authoring identity, resolves the lineage walk, and if the walk reads
blocked, it does not sign. Below `threshold`, the prefix's event never becomes witnessed-in-full, so
it cannot advance.

Because the check runs before witnessing **every** event, it must be cheap. The witness holds the
block state **cached on demand, per author it has seen** — a memoized constant-time lookup keyed on
the event's authoring prefix, refreshed as block SELs toggle. It never enumerates the full set of
blocked prefixes — the derived addresses are not listable (below), and it never needs to: each check
derives the one address for the one author in front of it.

## Non-enumerable — accountable, not a public shame-list

The derived address is what balances accountability against a wrongful block. There is **no
browsable block-list**: an observer cannot enumerate who a federation has blocked, because each
block sits at an address derived from its prefix, so finding one means already knowing the prefix.
What stays **verifiable** is exactly what should: the accused can check its own block (and read the
reason), and a relying party who knows a prefix can check it — accountability where it counts —
while a **mislabel never publishes an honest prefix on a public list**. The federation IEL still
shows blocking **activity** (the `Ath`/`Dth` anchors, so volume and timing) to a mesh observer,
never the prefixes — the same shape as the issuance-volume correlation the design already prices
([`../../residuals.md` §6](../../residuals.md#6-correlation-and-privacy)).

## Serve, block, and store

`vdtid` short-circuits a blocked author on the way in: a submission whose authoring prefix reads
blocked is **fast-rejected before the merge lock**, the same shape as the other pre-lock request
bounds
([`../infrastructure/vdtid.md` §Request bounds](../infrastructure/vdtid.md#request-bounds-and-rate-limits)).
This is a witnessing-side refusal, so it never touches the serve path — held data is still served.

## Operator posture

Every operator wants the flood stopped — no one wants their infrastructure used for spam — so the
block is a **cooperative** act, and its ergonomics matter: the console flow where one operator
proposes a block and others co-sign until `t_authorize` is met should be low-friction. That is
tooling on top of the primitive, not part of it; the primitive is the `t_authorize` `Ath`/`Dth`
above.

## Adversarial framing

- **Censorship costs a governance-scale quorum.** A block takes a `t_authorize` reserve quorum, so a
  below-threshold malicious witness set cannot block an honest prefix. A federation whose governance
  is compromised _can_ block an honest prefix — but only as **visibly** (the anchors are on its
  public IEL) and **escapably** (the target rebinds away) as any other governance compromise, so it
  folds into the existing governance-compromise residual rather than opening a new class
  ([`../../residuals.md` §4](../../residuals.md#4-issuance-delegation-and-governance-compromise)).
- **Escape is always available.** A block is federation-local, and a prefix survives its federation
  by rebinding ([`witnessing.md` §Rebinding](witnessing.md#rebinding)), keeping its prefix. So a
  determined abuser is whack-a-moled across federations, not globally silenced — the accepted
  decentralized cost, and the honest limit of what a decentralized system can do to a valid
  identity.
- **It catches concentrated abusers, not a diffuse swarm.** Blocking a few high-volume prefixes is
  cheap; a diffuse sybil swarm of many low-volume prefixes is bounded instead by the cost of
  inception (every prefix is a witnessed inception), the per-prefix event budget, and, past those,
  the lockdown posture (credential-gated participation). Block is the targeted tier; lockdown is the
  heavy tier ([`../../residuals.md` §9](../../residuals.md#9-availability-caps-and-dos-bounds)).
- **A block is not a fork or a takeover.** Witnesses declining to sign is within their reporter role
  — they author nothing in the blocked prefix's name and forge no event. The block SEL is the
  federation's own witnessed chain; a second competing state at one lineage is resolved by the same
  first-seen the rest of the system runs.

## Cross-references

- [`witnessing.md`](witnessing.md) — the witness signing decision the block check joins, the
  federation IEL's governance, and rebinding (the escape).
- [`../../primitives/data/event-logs/sel/log.md`](../../primitives/data/event-logs/sel/log.md) — the
  derived-address SEL the block is;
  [`sel/verification.md`](../../primitives/data/event-logs/sel/verification.md) — the lineage walk
  it reuses.
- [`../../primitives/data/event-logs/tags-and-topics.md`](../../primitives/data/event-logs/tags-and-topics.md)
  — the `vdti/sel/v1/topics/block` topic.
- [`../infrastructure/vdtid.md`](../infrastructure/vdtid.md) — the pre-lock fast-reject of a blocked
  author.
- [`../../primitives/data/sad/rooting.md`](../../primitives/data/sad/rooting.md) — the first front,
  whose valid-identity residual this closes.
- [`../../residuals.md`](../../residuals.md) — the censorship, escape, and diffuse-swarm costs.
