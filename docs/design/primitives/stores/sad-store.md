# SadStore — the dumb SAD store

`SadStore` is the persistence trait for standalone SADs. It is **dumb**: content-addressed put/get,
paginated, and it **never verifies, never checks a root, never evaluates a gate** — admission and
serving logic live one layer up, in the [`SadServer`](../../compositions/sad-server.md).

## The trait

| Operation      | Returns                                                                                            |
| -------------- | -------------------------------------------------------------------------------------------------- |
| `page(since)`  | the update-ordered listing of held SAD SAIDs — the anti-entropy enumeration                        |
| `get(said)`    | the SAD's bytes by SAID (a SAD is content-addressed and self-verifying, so a point read is honest) |
| `put`          | store bytes by their SAID                                                                          |
| `exists`       | an existence probe by SAID                                                                         |
| `delete(said)` | remove the bytes — a **capability** the composing server grants or withholds                       |

## Capabilities, not deployment rules

Three of the trait's operations are reachable only through a handle the **composing server** grants
— encoding each as a capability is what keeps a wire adapter from mapping it onto a public face by
default:

- **`delete` is granted or withheld by the composing server.** A federation `sadd` runs deletes
  **off** — the federation never deletes stored data; an off-federation `sadd` runs deletes **on**
  (`once` / `expiry`, and the deploying application's own delete predicate —
  [`sad-server.md`](../../compositions/sad-server.md)).
- **`page` is never on a public face — the grant is `in-process | mesh`, never `public`.**
  Enumeration is the one store operation whose _existence_ is the leak: a public `page(since)` on an
  inbox would enumerate every message SAID, hence every payload address, defeating digest-secrecy
  without guessing anything. A federation node exposes `page` over the sync daemon's authenticated
  mesh; an off-federation `sadd` exposes **no enumeration at all** — its only listing is the
  recipient-scoped, gated `deposits` query ([`sadd.md`](../../substrate/infrastructure/sadd.md)).
- **`exists` answers under the serve gate on any public face.** Ungated, it is a read-receipt oracle
  (a sender polls until the recipient drains), it survives un-sharing, and it confirms an object
  without passing any gate. So the public probe answers "held" only where a fetch by this requester
  would succeed — everything else is the uniform **"not present"**, so expired, consumed, and
  never-existed stay indistinguishable. The ungated wider answer — held-or-not, regardless of gates
  — is **mesh-only**, for sync and dedup.

**A remote `SadStore`** — a store daemon's API surfaced as a trait implementation, the cascading
store's remote tier — therefore implements `get` and gated-`exists` and **no `page`**; the trait
does not type-check a public enumeration into existence.

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
