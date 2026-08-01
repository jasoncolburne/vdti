# LogStore — the dumb chain-log store

`LogStore` is the persistence trait for chain events and their receipts — one trait for the KEL,
IEL, and SEL (the storage operations are identical; the per-primitive differences — merge,
verification, witnessing — live one layer up, in the
[`LogServer`](../../compositions/log-server.md)). It is **dumb**: it stores and returns bytes,
paginated, and **never verifies, never resolves an anchor, never checks a root**. Every correctness
rule runs above it, in a server or a consumer's own walk.

It decides nothing about **where** a write goes, either. The merge layer settles that before the
call: its routing — a normal append, a new chain, or the full dedupe / fork-formation / recovery
path — **is** the placement, computed under the per-prefix advisory lock against the verification
token it already holds
([`logsd.md` §The merge write path](../../substrate/infrastructure/logsd.md#the-merge-write-path)).
A store that reported placement back would hand the caller what the caller just decided; a store
that pronounced the verdict would be a store trusted about correctness, which no store is.

## The trait

| Operation                    | Returns                                                                                                                                                                                     |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `page(prefix, since, limit)` | one page of a prefix's events, with their receipts — a read **within** one prefix; the cursor is serial-scoped and **inclusive** of the floor serial                                        |
| `list(since)`                | the **prefix listing** the anti-entropy enumeration pages — one entry per prefix whose held state changed, ordered by the store's own commit-ordered update ordinal                         |
| `insert(events)`             | persists a **decided** write — the merge layer's promote, atomic with the ancestry it drags — inside the caller's transaction; it reports that the rows are durable, never a domain outcome |
| `effective(prefix)`          | the **compare key** — the real tip SAID when the chain holds a single confirmed tip, the **verdict-tagged synthetic** when it does not                                                      |

Every read is **fully paginated** — no unbounded read exists on the trait; an unbounded read is a
resource-exhaustion surface, not a convenience.

**There is no point `get(prefix, said)`.** A chain event is verifiable only by walking its chain
from inception, accumulating roster, threshold, and branch state — nothing verifies in isolation, so
a point read has no honest consumer. (A SAD is content-addressed and self-verifying, which is why
[`SadStore`](sad-store.md) _does_ carry `get(said)`.)

**A server gets a scoped handle, and migration authority is type-enforced.** `LogStore::reader()`
carries `page` / `list` / `effective`; `LogStore::writer(scope)` adds `insert` plus **migration**
authority for that scope. The handle grants migration rights, never exclusive append — a scope has
several runtime writers, serialized by the per-prefix advisory lock
([`log-server.md` §Migration ownership](../../compositions/log-server.md#migration-ownership--one-owner-several-writers)).

## `effective` is a bounded read — not a walk, and not the raw tip

`effective` returns the value anti-entropy compares: **the real tip SAID** for a
single-confirmed-tip chain, or the **verdict-tagged synthetic** (`forked:` / `disputed:` — qualified
by prefix and divergence position, never a digest over the competing tips) when no single tip exists
([effective-SAID comparison](../../protocol-doctrine.md#effective-said-comparison)). A raw tip
cannot express a fork at all, and the one consumer that must read forks — the sync loop — composes
**stores**, so the verdict-tagged value is the trait's to return.

The read is bounded, and its shape is fixed — there is one way to do it:

- **The floor is the derived seal, and it is total.** The derived seal is the highest clean
  seal-advancer, bottoming out at ⊥ — the inception is the first element above the bottom, so there
  is no young-log special case and no NULL guard
  ([`kel/log.md` §The clean seal, ⊥, and the bounded verdict window](../data/event-logs/kel/log.md#the-clean-seal--and-the-bounded-verdict-window)).
  The derived-seal test is **lineage-scoped**: the highest accepted seal-advancer **through which
  every accepted sealed branch's lineage passes** — ancestor-or-member, since on a resolved fork the
  winning branch's own burying seal-advancer is a member of its lineage, not an ancestor. A
  window-scoped test ("a competitor exists in the resulting serial window") reads a cross-serial
  `Disputed` as Active and is wrong.
- **The read is a forward traversal from the floor position, never a serial-range filter.** One
  indexed read on `previous = floor.previous` yields the floor row **and its siblings** (an
  inception floor has no `previous` — the seed read there is serial 0 for the prefix, or every young
  chain reads an empty window); then descend children by `previous`, **pruning each lineage at its
  first dead-on-ascent row** — the walk's own test: lost first-seen at an earlier position, or an
  attach point (the lineage's **last on-spine ancestor**, never its immediate parent) below an
  accepted seal, including a content sibling at an accepted seal-advancer's own position. The floor
  row itself is the anchor and is **never tested** — only its siblings and descendants classify.
  Each branch stops at its **first accepted seal above the floor** — nothing the verdict needs sits
  above a branch's first seal. A `serial ≥ floor` range filtered afterwards has an **unbounded
  input** — the retained dead lineages an abuser inflated — paid by every peer on every sync cycle;
  the traversal's pruning is what makes the read's cost **O(live rows + rotations above the floor)**
  indexed lookups.
- **The window is never empty, and a one-element window means the tip is the floor** — the inclusive
  floor is what makes the bare-inception and just-rotated cases one rule.
- **The window is bounded by `MINIMUM_PAGE_SIZE = 259`** under the two-per-rail ceiling — ≤ 65 rows
  Active, ≤ 129 live-Forked, ≤ 259 Disputed
  ([`kel/log.md`](../data/event-logs/kel/log.md#the-clean-seal--and-the-bounded-verdict-window)).
- **`effective` is defined over prefixes holding ≥ 1 accepted event.** A zero-accepted prefix is
  absent from announce, compare, and freshness — a whole staged or dragged-but-not-yet-accepted
  chain has no compare key until acceptance reaches it.
- **Acceptance is re-checked, not assumed.** The receipt join behind "accepted" re-checks **full
  countability per receipt, exact-match against the chain-committed witness-config included** — the
  receipt admission gate bounds and pre-filters what is held, and deliberately admits some
  non-countable rows as collusion evidence, so no verdict consumer counts held receipts raw
  ([`log-server.md` §The receipt admission gate](../../compositions/log-server.md#the-receipt-admission-gate)).

The traversal is **one mechanism shared with the serve path's live-region step** — same population,
same prune — wired to one boundary: the last clean seal and the derived seal are one event, and
wiring serving to one and `effective` to the other would silently diverge exactly on `Disputed`
chains
([`log-server.md` §Serving](../../compositions/log-server.md#serving--the-acceptance-gate-and-the-spine)).

## `list(since)` — the enumeration, ordered by commit

`list(since)` pages the store's prefixes by the store's **own local, monotone update ordinal** — one
listing entry per prefix, **restamped when a receipt lands, not only an event** (a receipt changes
held state). The ordinal is assigned in **commit order** by a **single-writer stamper**: allocation
order is not commit order (allocation is cached and non-transactional), so an allocation-ordered
listing permanently hides a lower ordinal that commits after a scan — and a data-time ordering (a
witnessed timestamp) permanently misses a late-gossiped old event. Serializing allocation is
rejected — that is the global write lock this design avoids; the mechanism is the implementation's
(logical decoding, or a post-commit stamping step). The store publishes
`(incarnation, resumePoint, head)` beside the listing — the restore-recovery contract the sync layer
consumes ([`gossipd.md`](../../substrate/infrastructure/gossipd.md)); `head` is the **stamper's
high-water mark**, never `max(ordinal)` and never a row count.

## What the store never does

- **Never verifies.** No signature check, no anchor resolution, no root confirmation — a
  [verification walk](../../protocol-doctrine.md#verification-tokens-as-proof-of-verification) is a
  separate, stateful, page-fed walker that composes `page` and `effective`.
- **Never decides retention or acceptance.** The two-per-rail floor and ceiling are the merge
  layer's ([`kel/merge.md`](../data/event-logs/kel/merge.md)); on a federation node no role can
  delete what the store holds
  ([`architecture.md` §Dependencies](../../substrate/infrastructure/architecture.md)).
- **Never answers "is this canonical?"** — the store's question is "must this survive?"; canonicity
  is computed by the walk from receipts and is never inferred from which store, or which table, a
  row sits in.

## Cross-references

- [`../../compositions/log-server.md`](../../compositions/log-server.md) — the logic layer over this
  store: merge, acceptance, the receipt gate, serving.
- [`sad-store.md`](sad-store.md) / [`blob-store.md`](blob-store.md) — the sibling persistence
  traits; the three stores are acyclic leaves with no cross-dependency.
- [`../data/event-logs/kel/log.md`](../data/event-logs/kel/log.md) — the derived seal, ⊥, the
  bounded verdict window, and the constants.
- [`../../protocol-doctrine.md`](../../protocol-doctrine.md) — the effective-SAID comparison and the
  retention doctrine.
