# SadStore — the dumb SAD store

`SadStore` is the persistence trait for standalone SADs. It is **dumb**: content-addressed put/get,
paginated, and it **never verifies, never checks a root, never evaluates a gate** — admission and
serving logic live one layer up, in the [`SadServer`](../../compositions/sad-server.md).

## The trait

| Operation          | Returns                                                                                            |
| ------------------ | -------------------------------------------------------------------------------------------------- |
| `enumerate(since)` | the update-ordered listing of held SAD SAIDs — the anti-entropy enumeration                        |
| `get(said)`        | the SAD's bytes by SAID (a SAD is content-addressed and self-verifying, so a point read is honest) |
| `put`              | store bytes by their SAID                                                                          |
| `delete(said)`     | remove the bytes — a **capability** the composing server grants or withholds                       |

## Capabilities, not deployment rules

Two of the trait's operations are reachable only through a handle the **composing server** grants —
encoding each as a capability is what keeps a wire adapter from mapping it onto a public face by
default:

- **`delete` is granted or withheld by the composing server.** A federation `sadd` runs deletes
  **off** — the federation never deletes stored data; an off-federation `sadd` runs deletes **on**
  (`once` / `expiry`, and the deploying application's own delete predicate —
  [`sad-server.md`](../../compositions/sad-server.md)).
- **`enumerate` is never on a public face — the grant is `in-process | mesh`, never `public`.**
  Enumeration is the one store operation whose _existence_ is the leak: a public `enumerate(since)`
  on an inbox would enumerate every message SAID, hence every payload address, defeating
  digest-secrecy without guessing anything. A federation node exposes `enumerate` over the sync
  daemon's authenticated mesh; an off-federation `sadd` exposes **no enumeration at all** — its only
  listing is the recipient-scoped, gated `deposits` query
  ([`sadd.md`](../../substrate/infrastructure/sadd.md)).

**There is no existence probe.** A `get` a gate refuses returns the uniform **"not present"** —
expired, consumed, gated, and never-existed are one answer — and no operation offers a cheaper way
to ask what that fetch just declined. A probe would be a read-receipt oracle (a sender polls until
the recipient drains), it would survive un-sharing, and gating it identically to `get` would leave
it answering exactly what `get` answers while every wire adapter carried a standing obligation to
keep the two gates in step. Cheapness is the point: unguessability is a **feature-layer** discipline
([`custody.md`](../data/sad/custody.md)), not a general property, so a low-entropy SAD is
dictionary-confirmable — and a probe is what makes that dictionary affordable. Sync needs none of
it: anti-entropy is **pull by enumeration** (`enumerate(since)`, then fetch), which asks a peer what
it holds rather than whether it holds one thing, and cross-submitter dedup does not exist by design
(a per-submitter `nonce` gives one blob two keys —
[`shapes.md` §The blob bundle](../data/sad/shapes.md#the-blob-bundle--access-and-availability-on-the-stored-object)).

**A remote `SadStore`** — a store daemon's API surfaced as a trait implementation, the cascading
store's remote tier — therefore implements `get` and **no `enumerate`**; the trait does not
type-check a public enumeration into existence.

## What the store never does

No verification, no rooting, no custody evaluation, no availability enforcement — those are the
[`SadServer`](../../compositions/sad-server.md)'s. A bare `SadStore` used directly is a **cache
tier**: the client placed what is there and re-verifies on read (end-verifiability); running a
server is what makes a store an admission floor.

## Cross-references

- [`../../compositions/sad-server.md`](../../compositions/sad-server.md) — admission (the rooting
  floor), the three-gate serve rule, availability, deletes.
- [`log-store.md`](log-store.md) / [`blob-store.md`](blob-store.md) — the sibling traits.
- [`../data/sad/rooting.md`](../data/sad/rooting.md) — the admission floor a `SadServer` enforces
  over this store.
