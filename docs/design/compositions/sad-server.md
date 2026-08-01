# SadServer — the SAD composition

`SadServer` is the logic layer over a [`SadStore`](../primitives/stores/sad-store.md): admission,
the serve gates, availability, and the delete capability. With `SadClient` and its `Source` /
`Sink`, it is the SAD stack between the dumb store and the daemons that compose it — a federation
[`sadd`](../substrate/infrastructure/sadd.md) runs it with deletes **off**, an off-federation `sadd`
with deletes **on**. Running a server **is** the admission floor — no deploy knob turns it off; a
bare store with no server is a **cache tier**, where the client placed what is there and re-verifies
on read.

The no-trusted-backend-RPC rule is [`log-server.md`](log-server.md)'s: a `SadServer` confirming a
root against a chain reaches the `LogStore` directly — a read, end-verified — never a `LogServer`'s
answer.

## Admission is three things, not one

1. **Reject event kinds outright.** Event bodies never enter the SAD store — keeping them out is
   what makes the serve rule below **physically unable** to leak one; the write-path rejection is
   the backstop beneath the serve-path allowlist, so even a mis-deployed allowlist cannot serve an
   event body.
2. **Recompact and recompute.** A submission may travel expanded; the SAID is defined over the
   fully-compacted form, so the server recompacts, verifies each child, recomputes the SAID, and
   rejects a mismatch — the bytes on the wire are not the bytes the SAID is over
   ([`compaction.md`](../primitives/data/sad/compaction.md)).
3. **The admission floor, dispatched on the committing-doc context.** The discipline is uniform; the
   check is contextual: **rooting** (an event root or accepted parent —
   [`rooting.md`](../primitives/data/sad/rooting.md)) for a `file` or any committed SAD; the
   **`senderPin` signature** for an off-federation inbox deposit; the **`chat-membership`
   per-requester check** for a deposit gated by a `chat-membership` SEL (a sender-less class — it
   has no `senderPin`); the **submitter's own live signature** for an off-federation unrooted root.
   There is no anonymous class on the federation
   ([`rooting.md`](../primitives/data/sad/rooting.md)).

To run the floor, an off-federation server **composes a federation client configured with the set of
trusted federation prefixes** — it queries public federation data and end-verifies it, the consumer
pattern, never backend RPC. A requester bound to a federation outside that set is **`unresolvable`**
— a distinct refusal, never "not Active," so a client can tell "this store does not trust your
federation" from "your chain is forked"; a chain rooted on an untrusted federation is denied from
its inception.

**Long walks are resumable.** Confirming a root can mean walking a chain from inception, so
admission runs under the token-bundle discipline
([`log-server.md` §Capability tokens and token bundles](log-server.md#capability-tokens-and-token-bundles)).

**Derived indexes are local state — and they are authorization inputs.** A deposit is indexed by the
scope it was deposited to — for mail, the recipient derived at admission from the ESSR envelope's
signed-cleartext recipient; for chat, the group the server **verified at admission** (the submitter
names a `chat-membership` SEL, and the server walks the message's lane back to its anchored root to
confirm the lane roots in that SEL — resumably, one hop in the steady state, **verified on write,
never on read**). Both are store-local derived state claiming no verifiability to any reader — say
so, or the next reader sees a service-invented identifier — but they are **not** in the
nothing-trusts carve-out the rate counters live in: the `deposits` listing and the serve gate's
feature dispatch **run against them**, which makes them authorization inputs. What makes that safe
is that the server **derived them by verification**, and a reader still walks the lane itself and
catches a wrong record. A **replicating peer re-derives them; it never inherits them** — a
forwarder's signature vouches for admission, never for a gate's input
([`exchange.md` §The session mode](../features/exchange.md#the-session-mode--chat)).

## The serve gate is three gates

Canon's layered, default-deny rule, and it survives the decomposition intact — **live on the
federation face as much as off it**:

1. the **served-kind allowlist**
   ([`kinds.md` §Fetch by SAID](../primitives/data/sad/kinds.md#fetch-by-said--what-the-store-hands-back));
2. the SAD's own **custody `readers`** gate ([`custody.md`](../primitives/data/sad/custody.md));
3. the **owning feature's serve-time gate, dispatched on the SAD's `kind`** — a chat message SAD
   carries no `custody` at all, so a custody-only gate would serve it to anyone; the check it needs
   is the same generic [`membership`](../primitives/protocols/membership.md) resolution the blob
   `access` dispatch runs. **`SadServer`'s serve gate and the blob `access` dispatch are one
   mechanism** — `roster` (a single identity's current devices) or `membership` (grant-chain sets) —
   encoded once ([`blob-server.md`](blob-server.md)).

There is **no existence probe** — a fetch a gate refuses returns the uniform "not present", and no
cheaper operation answers the question the fetch just declined
([`sad-store.md`](../primitives/stores/sad-store.md)). The serve gate is **operational, never the
confidentiality boundary** — confidentiality is encryption; the gate bounds store-side harvesting.
And it refuses a requester whose identity's chain is not Active, for a requester outside that
identity's own roster ([`iel/verification.md`](../primitives/data/event-logs/iel/verification.md)).

## Availability and deletes

- **Availability enforcement** — `expiry` garbage-collects past its instant; a `once` SAD is removed
  on first successful read; expired, consumed, and never-existed are one uniform "not present."
  Off-federation only: a federation `sadd` **refuses** a submission declaring either axis
  ([`availability.md`](../primitives/data/sad/availability.md)).
- **`delete(said)` is authorized by the deploying application, never by a rule here.** The server
  supplies the capability and the live check that resolves a signed request to an identity; the
  application supplies `mayDelete(object, requester)`, compiled into its own store binary — mail's
  is one line (the requester equals the envelope's `recipient` — the acknowledge flow), drive's is
  `custody.owner`; each lives in its own doc. Two bounds the SAD layer **does** state:
  **`custody.readers` never authorizes `delete`** (the union admits on any match — a delete rule
  over it would hand a cross-identity delete to every reader of a shared document), and
  **`custody.owner` names the _sender_ on a mail message and is usually absent there**, so "the
  owner may delete" reads obviously right and is wrong for mail.
- **`deposits`** — the recipient's discovery poll, an **off-federation** query: enumerate the SADs
  deposited for a scope at this store, gated the same way the serve is — `roster` for an identity's
  inbox, `membership` for a group — live-signed, `since`-cursored. A federation node holds no inbox
  and serves no `deposits`.

## Cross-references

- [`../primitives/stores/sad-store.md`](../primitives/stores/sad-store.md) — the dumb store and its
  capabilities.
- [`log-server.md`](log-server.md) — parking, token bundles, the no-trusted-RPC rule.
- [`../primitives/data/sad/rooting.md`](../primitives/data/sad/rooting.md) /
  [`custody.md`](../primitives/data/sad/custody.md) /
  [`availability.md`](../primitives/data/sad/availability.md) — the rules this composition enforces.
- [`../substrate/infrastructure/sadd.md`](../substrate/infrastructure/sadd.md) — the deployable.
