# Membership — a gated set of identities, checked one at a time

**Membership** answers one question, for one identity at a time: **is this party a current member of
this group?** A chat asks it to gate who may deposit and drain messages; a shared document asks it
to gate who may read or write. It is deliberately **not** a list you can read off — the set has **no
cap**, and no party ever holds it whole. You bring the identity you care about and check _that one_.

Membership is the **authorization** half of a group. It is not the keying half: handing a member a
shared decryption key means wrapping that key to each member, which forces enumerating them — a
**bounded** act that belongs to [group-key](group-key.md), not here. Membership stays unbounded
because it never enumerates.

## The grant chain

A group's membership lives on a **grant chain** the group's governing identity owns. Each event on
it seals a **membership delta** — `{ grants, rescinds }`:

- **`grants`** — identities admitted, each as a **blinded per-member commitment** (the same
  `{ said, nonce, data }` claim construction [credentials](../../features/credentials.md) use for
  per-predicate gating): the commitment names the member without publishing who, so an onlooker
  reading the chain learns a count, never a roster.
- **`rescinds`** — identities removed, each a blinded target, optionally carrying a **grandfather
  boundary** (below).

A membership change is one such delta. There is no separate "add" and "remove" event — one delta
carries both, the way an identity's own roster change carries adds and cuts together.

## Checking one member — the two modes credentials already use

Membership reuses the credential **accept** shape wholesale: a party is a current member iff its
**grant is validly recorded and not since rescinded**. That check runs in either of two modes, the
same fail-secure / fail-open split a credential's revocation check uses:

- **The fail-secure walk (default).** Walk the group's grant chain with the party as a **known
  search** — you are looking for exactly this identity's grant, and for any later rescind of it —
  against the multi-source-fresh chain. In some grant delta and not since rescinded → a member; in
  none → not. This is the sound reading: hiding a rescind would take a stale chain, which the
  freshness bar already refuses. For this to stay the **default**, the non-member store must be able
  to **run** it holding only the requester's prefix: the per-member commitment is **blinded from
  inputs the store also has** (the requester's prefix + the group), so the store **recomputes** the
  target and matches it against the chain — it never rests on a per-member secret the request does
  not carry (which would make the walk non-performable and silently force the fail-open path).
- **The O(1) happy path (opt-out).** A rescinded member has a **content-addressed rescission
  lookup** — a tiny `{ inception, termination }` log derived from
  `{ group, the rescission topic, the member }` — whose termination **pins to the grant delta that
  rescinded it** (its pin is that delta event's `previous`, so the pin points straight at the delta
  carrying the rescind). Fetch it: **found → rescinded**, no walk. The grant side is symmetric — a
  member's grant is located directly by its own pin. A consumer under a latency budget opts down to
  this; **not-found reads best-effort not-rescinded**, so it is a deliberate step down from the
  walk, never a step up.

Both modes check **one identity at a time**. Neither ever builds the set.

## No cap, no enumeration

The set is **unbounded** — a document may be readable by an open-ended audience — so it is **never
materialized**. Every operation is a check against a **known** identity: the store gates a deposit
or a fetch by the **requester**, which presents itself, so the store confirms that one party's
membership and nothing else. There is no operation that asks "who are all the members," because the
answer has no bound and no party is entitled to it. This is what lets a downloader of the chain
learn only a count, and what keeps the check cheap regardless of how large the audience grows.

Where a group genuinely must reach every member — wrapping a shared key — that enumeration is
[group-key](group-key.md)'s **bounded wrap roster**, a separate structure. Membership never does it.

## Rescission and the grandfather boundary

Removing a member is a `rescinds` entry. Two flavors, set by the feature:

- **Immediate** — the member is out at once. A keyed group (chat) uses this: forward secrecy comes
  from the epoch turning in the same act, so nothing the removed member holds opens anything new.
- **Grandfathered** — the rescind carries a **boundary**: content the member authored (or was
  entitled to) **before** the boundary stays honored, only its reach past the boundary is cut. A
  shared document uses this so a removed editor's earlier versions do not retroactively vanish. The
  boundary is itself blinded when it would otherwise identify a participant, riding behind the read
  gate; a non-identifying boundary rides in the open.

Either way the removal is one `rescinds` entry plus, for the happy path, the member's
content-addressed rescission lookup.

## Two instances

Features name their membership sets on the shared `vdti/{component}/v1/{category}/{name}`
convention, and the two that exist are parallel:

- **`chat-membership`** — the set a chat's store checks to gate deposit and fetch. Bounded in
  practice (the chat is a keyed group, so group-key already caps it), but checked the same
  one-at-a-time way.
- **`document-membership`** — the set a shared document's store checks to gate read and write.
  Genuinely unbounded (an open readership), grandfather-rescinded.

The read-versus-write distinction, and the exact per-instance shapes, are the composing feature's;
membership provides the one checked-set mechanism both sit on.

## The cap is keying's, not membership's

The reason chat feels "limited" and an open document does not is **not** a property of membership —
it is a property of **key distribution**:

- A feature that hands members a **shared decryption key** must wrap it to each of them, which means
  enumerating them → a **bounded** roster ([group-key](group-key.md)). Chat, and any encrypted
  shared document behind a shared key, are capped for this reason.
- A feature that encrypts nothing — or delivers content **per request**, sealed to the one member
  who asks — never enumerates, so its membership stays **unbounded**.

So a **keyed** feature composes **both** — group-key's bounded wrap roster (to distribute the key)
and a membership instance (to authorize a requester) — while an **unkeyed** feature composes
**only** membership. The two are different structures with opposite shapes; a feature that needs
both uses both.

## The boundary — what membership is not

- **Not the wrap roster.** Enumerating members to wrap a key is [group-key](group-key.md)'s bounded
  roster. Membership never enumerates.
- **Not a policy.** Membership answers "is this one identity in the set," a single-party lookup —
  not a multi-party expression evaluated live. Document authorization above it (who may do what) is
  the policy layer's; membership is the set it draws on.
- **Not keying, delivery, or the content structure.** What a group encrypts, how it delivers, and
  how its content threads (the [authored DAG](authored-dag.md)) are the composing feature's;
  membership only says who is in.

## Cross-references

- [`../../features/credentials.md`](../../features/credentials.md) — the grant / blinded-commitment
  and the fail-secure-walk / fail-open-lookup accept shape membership reuses.
- [`group-key.md`](group-key.md) — the bounded wrap roster that distributes a keyed group's shared
  key; the enumeration membership deliberately does not do.
- [`../data/sad/custody.md`](../data/sad/custody.md) — a SAD's `readers` names a membership set: the
  read-authorization pointer into this primitive.
- [`authored-dag.md`](authored-dag.md) — the per-writer content structure a group's messages or
  versions form; membership gates who may append to it.
- [`../data/event-logs/sel/log.md`](../data/event-logs/sel/log.md) — the single-owner log the grant
  chain and the content-addressed rescission lookups ride.
