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

**There is no existence probe, because nothing needs one.** Gated identically to `get` — which it
would have to be — a probe answers exactly what `get` answers, so it is a second operation for one
question, and a standing obligation on every wire adapter to keep two gates in step forever. Sync
does not want it either: anti-entropy is **pull by enumeration** (`enumerate(since)`, then fetch),
which asks a peer what it holds rather than whether it holds one named thing, and cross-submitter
dedup does not exist by design — a per-submitter `nonce` gives one blob two keys
([`shapes.md` §The blob bundle](../data/sad/shapes.md#the-blob-bundle--access-and-availability-on-the-stored-object)).
Redundancy is the whole argument; the absence needs no security case.

The one place the two operations would genuinely differ is **`once`**: a `get` against a
destructive-read object **consumes** it, so with no probe, checking whether a one-shot deposit is
still there is what removes it. That cuts both ways and is stated, not solved — an honest client
cannot look without taking, and neither can anyone else. A refused or exhausted fetch is the uniform
**"not present"** ([`availability.md`](../data/sad/availability.md)), so gated, expired, consumed,
and never-existed remain one answer.

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
