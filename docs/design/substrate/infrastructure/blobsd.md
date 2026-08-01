# blobsd — the blob store daemon

`blobsd` is the **off-federation blob store daemon**: it admits bundle-committed blobs, gates their
serving on the bundle's declared `access`, and runs deletes under the deploying application's
predicate. It deploys the [`BlobServer`](../../compositions/blob-server.md) composition over a
[`BlobStore`](../../primitives/stores/blob-store.md). It is independently deployable, **not part of
a federation node**, with **no witness role and no HSM** — though not "no identity": a deployment
that joins a service fleet is a **member device of that fleet's IEL**, and any node whose dial a
client authenticates publishes a transport-key SAD signed by its **node KEL**
([`architecture.md`](architecture.md)). What it lacks is the witnessing apparatus.

`blobsd` is an **end-verifying consumer of the federation**: it queries public federation data —
chains, witness KELs, receipts — to verify, but, not being a witness, it is never served
`access`-gated documents. Anything gated is supplied by the submitter or requester, and `blobsd`
verifies it (self-verifying data; trust nothing). It **does** enforce an `access` serve gate on its
own serve — a current-membership live check (§The serve gate) — which is a different direction from
being _served_ gated data.

The tenet everything here rests on: **everything is a SAD, everything is verified, everything is
anchored to a signature.** The store holds nothing unanchored — a blob is opaque, so it is
legitimate **only because a verified, anchored document commits it**. No orphans, no
service-invented identifiers, no unverifiable local structures making a security claim.

## The stored objects — bundle, payload, and the object index

The blob model is the SAD layer's
([`sad.md` §Bulk opaque bytes](../../primitives/data/sad/sad.md#bulk-opaque-bytes--the-content-addressed-blob),
[`shapes.md` §The blob bundle](../../primitives/data/sad/shapes.md#the-blob-bundle--access-and-availability-on-the-stored-object)):
the client composes a **bundle** carrying the blob's access and availability, the stored object is
the **payload** `bundle.said ‖ blob`, and the **storage key `S = hash(payload)`** is what the
committing document commits. `blobsd` stores exactly **two** content-addressed things — the bundle
(by `bundle.said`) and the payload (by `S`) — and nothing else. In particular, **never the
committing document `D`**: holding `D` would build a correlation surface (who mailed whom, which
group a blob belongs to) out of data the store has no need to retain. The consequence is structural:
**every `D`-relative check is one-shot, at admission** — `D ⊇ payload`, the `access`-matches-`D`
check, and the bundle-kind-matches-`D`'s-kind check all run while the submitter's `D` is in hand,
and are never re-run. At serve time the bundle must therefore carry everything the gate needs, which
is why `access` rides the bundle rather than being resolved from `D`.

The `BlobStore` keeps an **object index**, and the replication listing rides it. It has to: `once`
needs a burn flag, `expiry` needs a GC horizon, and the bundle ↔ payload GC pairing needs both
sides — none of which a bare object store gives. So the index exists already, and it is where the
**commit-ordered enumeration ordinal** lives, giving `BlobStore` an `enumerate(since)` beside
`SadStore`'s — without it a replicated deployment syncs the message SAD and not the payload, which
is the half that holds the bytes. The index is store-local derived state; nothing a reader trusts
lives in it.

Because the bundle commits `blobDigest`, a given `bundle.said` pairs with exactly one blob, and **GC
is unambiguous**: never GC a bundle while its payload can still be served (`bundle ⊇ payload`);
delete it once that one payload is gone. **Fail-closed**: if the bundle is missing when serving,
refuse and delete the payload.

## Blob admission

A blob is admitted the way a SAD is: it must be committed by a **real, anchored document**. The
submitter supplies the committing document `D` (and anything gated that `blobsd` cannot fetch), and
admission checks two things — **`D` commits `S`** (cheap), and **`D` is anchored**, by the floor its
context supports:

- a **`file` SAD** → the owner's chain ([rooting](../../primitives/data/sad/rooting.md));
- an **off-federation inbox deposit** → the **envelope signature under `senderPin`**,
  full-IEL-verified — a real, witnessed identity stands behind the deposit; currency stays the
  recipient's on-open check, not the server's, so a harvested, since-rotated-out sender key can
  deposit spam that clears the floor and is rejected only on open — bounded by the per-identity
  rate, per-IP, and inbox caps ([`../../residuals.md`](../../residuals.md));
- a **message on a `chat-membership`-gated lane** → the **`chat-membership` per-requester check**
  the submitter must pass, plus the lane walk below;
- an **unrooted SAD** → the **submitter's own live signature** at this store's boundary — the
  unrooted class is off-federation, and the store's operator sets its own admission policy.

**`D` is a document set, not a document.** For a mail deposit `D = { message, envelope }` — the
envelope is `sad/field`-rooted by the message and co-present under `root ⊇ child`, so admission
assembles both to admit the deposit at all. Rules read fields off `D`; where a store removes an ESSR
deposit, it removes the set.

To check `D` is anchored, `blobsd` composes a **federation client** — configured with the set of
trusted federation prefixes — and queries the federation for the public parts as an end-verifying
consumer (the consumer pattern, never backend RPC: no server consumes another server's _answer_; it
fetches data it end-verifies itself — [`architecture.md`](architecture.md)). A depositor or
requester bound outside the trusted set is **unresolvable** — a distinct fail-closed refusal, never
"not Active". The anchor walk does not have to complete in one request: it resumes across requests
under a **token bundle**
([`log-server.md` §Capability tokens](../../compositions/log-server.md#capability-tokens-and-token-bundles)),
and the blob lands **last**, against a completed bundle whose recorded hash it must match.

**The payload must actually match the bundle.** Admission refuses unless the payload splits as
`bundle.said ‖ blob` with `bundle.said` recomputing from the submitted bundle bytes **and**
`hash(blob) == bundle.blobDigest`. This check is what makes the bundle-payload 1:1 true rather than
inferred, and both destructive rules depend on it — GC ("delete the bundle once **that one** payload
is gone") and fail-closed-on-missing-bundle ("refuse and delete the payload"). Without it a second
party submits `payload' = bundle.said ‖ blob'` under its own `D'`, and then either the owner's
expiry triggers a GC that cascades into deleting `payload'`, or `payload'` pins the bundle past the
owner's committed retention horizon.

**`access` is mandatory whenever `D` declares a read gate — a structural predicate, not a
judgment.** A blob is opaque bytes, so no boundary can tell ciphertext from plaintext; the predicate
reads off `D`, and every branch names a primitive or a feature construct — never an application —
which is both the honest scope and what keeps the branches computable:

- `D` carries an **ESSR envelope** → `access` **required**, `roster` = the envelope recipient;
- `D` carries **`custody.readers`** → `access` **required**, `membership` = those sets;
- `D` is a SAD whose **owning feature declares a serve-time membership gate** → `access`
  **required**, `membership` = the SEL that gate names (the branch is written on the feature's
  declaration — [`exchange.md` §The session mode](../../features/exchange.md#the-session-mode--chat)
  declares the one instance);
- `D` declares **no gate** → `access` **omitted**.

Every branch is checkable from the submitter-supplied `D`, so **the gate is never looser than `D`**
— a gated document cannot reach the store with an ungated payload.

**Chat validates against the submitter's own membership proof, and against the lane.** A chat
message SAD carries no `custody`, so there is nothing on `D` to match a claimed `access` against;
instead the submitter must **pass** the `chat-membership` check for the SEL it names — you can only
deposit a blob gated by a group you are currently in — **and** the message's lane must **root in
that group**: the store walks `previous` back to the lane root and checks the root's anchoring grant
act lands on that SEL, resumably under the token bundle, one hop in the steady state
([`exchange.md` §The session mode](../../features/exchange.md#the-session-mode--chat) — the walk,
the recorded lane → group binding, and its authorization-input status are stated there). Together
the two checks keep "the gate is never looser than `D`" true for chat with no exception.

**The bundle kind is validated against `D`'s kind.** A structurally sealed `D` — an ESSR envelope,
an epoch-sealed message — **must** carry the sealed bundle kind; a `file` SAD is ambiguous, so
**plaintext is the fail-secure default** and a client-side-encrypted drive opts down by deliberately
choosing the sealed kind. After admission it is just a kind gate; an unmappable kind is refused,
fail-closed.

**This is the abuse prevention.** Every stored blob costs a real anchored committing document —
exactly the SAD spam model — with one clarification for chat: the anchor is the **lane root's**
grant-chain act rather than a per-message one, so the per-message cost is a witnessed identity's
rate quota. No orphans.

**Rate-limiting rides an identity the admission check actually produced.** Each floor yields one,
and they are not the same party: a `file`'s **owner**; mail's **`senderPin` identity**; chat's
**member identity** the `chat-membership` check resolved; an unrooted SAD's **submitter** — the only
party the store can authenticate. Each is blinded the same way —
`rateTarget = hash('…/rate:{prefix}')`, a local counter, unsigned and operational. For the blob/mail
class rate-limiting is **load-bearing**: a blob's anchor is a **free signature** (an ESSR envelope,
a device signature), not a budgeted chain event, so the per-identity rate and per-IP caps are what
bound a real identity's flood.

**Admission is verification-coupled to the federation — and so is a cold read.** The anchor walk
runs at every deposit, so a partition — or a store eclipsed from the federation — blocks deposits;
the light serve-currency tier relaxes _freshness_, never the _walk_. A `membership` gate resolves
against the group's grant chain and a `roster` gate walks the recipient's IEL and its devices' KELs
— chains an off-federation store does not hold — so the **first** fetch against a gate the store has
never seen also needs the federation, and refuses under partition. What makes the light tier
meaningful is a **cached chain view** the store maintains for the gates it serves: the dependency is
write-side unconditionally, read-side on first contact with a gate's chain. The token bundle
amortizes the walk; it does not remove the dependency.

## The serve gate

`BlobStore` is a dumb key → value layer: given `S` it returns the payload `bundle.said ‖ blob`
**whole, verbatim** — the consumer recomputes `hash(payload) == S` and splits out `bundle.said` and
`blob` itself, self-verifying. The `BlobServer` logic peeks at the `bundle.said` prefix to find the
bundle, runs the availability call, and enforces the `access` gate — **dumb store, gating server**.
It serves verbatim for an ungated bundle and gates for a gated one.

**Ungated ≠ public.** An ungated bundle is still protected by **`S`-secrecy** — `S` is learned only
from the committing document — but `S`-secrecy is a **privacy layer, never the authorization**, so
anything whose `D` declares a read gate carries `access` and is gated here (§Blob admission).
Ungated means a bearer object by intent — a `once` link, published bytes — not "encrypted, so the
gate is optional."

**`access` gates the serve on a live-signed request**, dispatched on `access.check`: a `roster`
check admits a current member **device** of the named recipient IEL; a `membership` check admits a
current member of any named grant chain
([`membership.md`](../../primitives/protocols/membership.md)) — a drive/file's `readers` sets, or a
chat's `chat-membership`. The request carries a **nonce and a freshness window** (a replayed signed
request would be a bearer token). An unmappable check is **fail-closed** — refuse, never
default-serve. The gate is **operational, never the confidentiality boundary**
([`custody.md`](../../primitives/data/sad/custody.md)), and it authorizes **reads only**. It is
**one mechanism** with `SadServer`'s serve gate and the mail deposit gate — the same `membership`
resolution in all three places ([`blob-server.md`](../../compositions/blob-server.md),
[`sad-server.md`](../../compositions/sad-server.md)).

**Serve-currency matches the stakes, keyed on the bundle's kind.** The question is how current the
store's view of the grant chain must be before acting on the membership walk, and the answer turns
on what being wrong costs:

- **sealed bundle kind** → the **light** check: verify the request's live signature, its nonce, and
  that its timestamp sits in the clock band, then run the membership walk against the chain state
  the store already holds. Being wrong exposes ciphertext the requester cannot read — the seal or
  epoch key is the real boundary — so a partition never blocks a recipient from its own mail.
- **plaintext bundle kind** → the **strict multi-source freshness bar**
  ([`architecture.md`](architecture.md)) before trusting the chain view, because being wrong exposes
  the content itself, and an evicted party must be refused **fail-secure**; the propagation/eclipse
  window is the standing residual.
- **anything unrecoverable → always strict, regardless of kind — and that is BOTH a `once` bundle
  and any `delete(S)`.** Two triggers, not one. For `once`, the trigger is the **serve**: a mail
  bundle is structurally sealed, hence the light tier, whose justification is about _read_ exposure
  — a device cut from the recipient's roster issues an ordinary read of `S` before the cached chain
  view catches up, which the light tier deliberately permits, and `once` burns. For `delete(S)`,
  `acknowledge` **is** a `delete(S)` and mail deliberately does not use `once` — without the delete
  trigger a cut device drains and destroys an inbox under the light tier.

The kind is committed in `bundle.said`, hence in `S`, hence in `D`, and admission validated it
against `D`'s own kind — a structural dispatch, not a submitter's word taken on trust.

**`once`** is a destructive read — burns on the first serve, **gated or ungated**: an ungated `once`
is a **bearer one-time link**, first-reader-wins by `S`, for sharing to a party with no identity;
its only protection is `S`-secrecy (a leaked `S` gets it burned — an opt-in residual `blobsd`
needn't police). **`expiry`** GCs past its instant. The two compose
([`availability.md`](../../primitives/data/sad/availability.md)). Removal on request is the
deploying application's (below), so mail's recipient-drain is a predicate mail's own store carries,
not a bundle field.

## Deletion is the application's

`access` authorizes reads. **Nothing at this layer authorizes deletion**, and that is structural
rather than a scoping preference.

**The test.** If a wrong delete could make a verifier reach a wrong answer, deletion would have to
be a protocol rule. It cannot: the doctrine is that **absence proves nothing** — which is precisely
why removal is expressed as `kills[]`, `Trm`, and rescission rather than by expecting objects to be
missing. No verifier concludes anything from an object being gone. A bad delete costs availability
at one store, indistinguishable from that store going away, and store availability was never
promised.

**The stronger reason: the authorization question has no general answer.** Every derivable rule has
a hole, and the pattern is the same each time — the protocol reasoning about application semantics:

- a **bundle-declared** deleter is self-asserted — a mail sender names a prefix it controls and
  destroys the recipient's mail before it is read (a standalone SAD is its own `D`; nothing external
  validates the field);
- **deriving from `custody.owner` first** lets the same sender win by writing
  `custody { owner: self, pin }` on its own message — batchable across a whole send for one chain
  event;
- **an ESSR-first derivation misses the field entirely** — `recipient` sits on the **envelope**, and
  the message's canonical bytes carry `envelope` as a bare SAID, so a derivation reading the SAD's
  own bytes falls through to "not deletable" for every mail message the design sends.

Each is the protocol trying to decide something only the application knows. So there is **no
`deletes` field**, no derived-deleter chain, and no "a `readers` union never authorizes `delete`"
rule at this layer (the last exists as a structural bound on what a read gate can mean —
[`sad-server.md`](../../compositions/sad-server.md)). What the layers supply instead:

```
protocol supplies      delete(S) / delete(said)              a store capability
                       resolve(signed request) → identity    the live check access already runs

application supplies   mayDelete(object, requester) → bool
```

`BlobServer` and `SadServer` are libraries, so a deploying application compiles its own predicate
in. Mail's is one line — the requester equals the envelope's `recipient`, which the mail store read
at admission to build its deposits index ([`mail.md`](../../example-applications/mail.md) documents
it). The SAD layer states no law.

**`once` and `expiry` stay.** Unenforceable does not mean unexpressible: both are depositor
**declarations** with structural rules the protocol checks (`child.expiry ≤ root.expiry`; a root may
not be `once`), and `once` has a primitive-level use in per-device ESSR
([`availability.md`](../../primitives/data/sad/availability.md)). What the layer does not state is
the _authorization_ to remove on request, not the declarations.

**An application's own "delete" is inside its payload, where the protocol cannot see it.** A chat
message is an arbitrary encrypted blob with an application protocol riding inside — an unsend is an
**append naming its target**, the same shape as `kills[]`, authored in the application's own data.
There is no chat delete kind to specify.

**The federation is unaffected.** It never deletes, and it refuses `once` / `expiry` besides
([`availability.md`](../../primitives/data/sad/availability.md)).

## Durability rides the committing document

A blob re-verifies on a later fetch off **the committing document's** durability, never off anything
`blobsd` provides: a `file` SAD → its chain anchor; a mail message → sender-key-currency (the
sender's witnessed key-state); a message on a `chat-membership`-gated lane → the writing device's
signature under its KEL key-window, with the witnessed epoch bounding when
([`exchange.md`](../../features/exchange.md)); an unrooted SAD → the retained committing document
itself, on the off-federation store that admitted it. So `blobsd` needs no witness and no HSM — the
durable anchor is always the committing document's, and the blob rides it via `S`.

**`D ⊇ payload` — the covering rule.** Because the blob re-verifies off `D`, `D`'s availability must
cover the payload's: `D.expiry ≥ payload.expiry`, and **a `once` `D` roots nothing** — a message
read-and-gone can't anchor any payload
([`availability.md`](../../primitives/data/sad/availability.md)). `blobsd` checks this at admission,
where it holds the submitter-supplied `D`.

The **retention coupling** across the two **independent** stores — `D` on `sadd` staying available
while the payload on `blobsd` is still servable — is the **client's** (mail is client-side
composition; the client that acks or deletes one deletes the other). The delete-fan self-correction
covers the SAD half only: the client **discovers** a surviving SAD by polling, while a stray
**payload** whose SAD is already gone has no discovery path — nothing lists it to the client and no
reaper looks for it — so it sits until its `expiry` if it has one, and forever if it does not; a
bundle carrying `expiry` bounds the gap, an unexpiring one does not. Where a store GCs `D` early, a
later fetch of the orphaned payload **fails verification fail-secure** — no `D` to anchor `S` or run
sender-key-currency — an availability loss, never a forgery
([`../../residuals.md`](../../residuals.md)).

## Public-blob discovery

**Public content is the identity's, so it resolves from an identity-scoped lookup — never off
`receivers`** (the receive-key directory's field is **per device** and routes mail, not content —
[`receive-key-directory.md`](../../primitives/protocols/receive-key-directory.md)). A stranger
holding the owner's prefix and a public file's `S` derives `(owner prefix, the content-store topic)`
→ the owner's store identities
([`tags-and-topics.md`](../../primitives/data/event-logs/tags-and-topics.md)), resolves each named
service to its nodes through that service's own published **endpoint lookup**
([`receive-key-directory.md` §The endpoint lookup](../../primitives/protocols/receive-key-directory.md#the-endpoint-lookup--the-same-pattern-for-a-services-addresses)),
and fetches by `S`, which the public committing document names. The lookup is identity-scoped and
self-published — no third party asserts where the owner's content sits — and it stays stable when a
service moves a node.

**The price lands on an ordinary user, and nothing amortizes it.** A value-lookup SEL is
`{Icp, Gnt}` at **tier 2**, so standing one up takes the owner's rotation reserve at `t_authorize`,
co-signed across physically co-present devices (the co-signing transport has no asynchronous path).
So **publishing your first public file is a one-time tier-2 establishment**, and naming a second
content store stacks another `Gnt`. A service amortizes its endpoint lookup on the governance
cadence it already pays; a user publishing a file performs no other governance act. What keeps it a
**one-time** cost is that the value names a **service identity**, not an address, so it does not
churn — and an owner with no public content publishes nothing at all.

## Request bounds

Every request surface is bounded: the **size cap** — a maximum payload size at admission (config, ~1
MiB), refusing oversize, and since the whole payload is served, bounding the serve too — the
**per-identity rate** on the floor-produced identity (§Blob admission), and the **per-IP** cap. A
depositor or requester bound outside the configured trusted-federation set is refused
**unresolvable, fail-closed**. A deposit needs **no replay set**: the write is content-addressed and
idempotent — a replay re-stores identical bytes and changes nothing — so the per-identity rate and
the signed-fresh timestamp cover the space with one blinded key. Limiter and nonce tables are swept
by a periodic reaper, so attacker-generated keys cannot grow them without bound.

## Public face

The public dial is **authenticated against the node's KEL**: the node publishes a **transport-key
SAD** carrying a **validity window**, signed by a key that is **current** in its node KEL and
re-signed on a timer; the client verifies it against the node's KEL, then runs an ephemeral-KEM
handshake in which the transport key **signs** and is **never encapsulated to** (not the
receive-key-directory pattern — a receive key is a KEM key, and that reading breaks forward
secrecy). A fleet deployment is a member device of the service's IEL
([`architecture.md`](architecture.md)). There is **no enumeration on the public face**:
`enumerate(since)` is the replication listing over the object index — in-process or fleet-internal,
never public — and `blobsd` serves only by `S`, under the serve gate. A `bundle.said` fetch is
refused by default; the bundle is reachable only through the payload at `S`.

## Cross-references

- [`../../primitives/data/sad/sad.md` §Bulk opaque bytes](../../primitives/data/sad/sad.md#bulk-opaque-bytes--the-content-addressed-blob)
  — the payload / storage-key model.
- [`../../primitives/data/sad/shapes.md` §The blob bundle](../../primitives/data/sad/shapes.md#the-blob-bundle--access-and-availability-on-the-stored-object)
  — the bundle shape, the two kinds, the `access` descriptor.
- [`../../primitives/stores/blob-store.md`](../../primitives/stores/blob-store.md) /
  [`../../compositions/blob-server.md`](../../compositions/blob-server.md) — the store trait and the
  composition this daemon deploys.
- [`../../primitives/protocols/membership.md`](../../primitives/protocols/membership.md) — the
  membership resolution the serve gate dispatches on.
- [`../../features/exchange.md`](../../features/exchange.md) — chat's store authorization and the
  lane walk; [`../../example-applications/mail.md`](../../example-applications/mail.md) — mail's
  delete predicate.
- [`sadd.md`](sadd.md) — the sibling off-federation SAD store.
- [`architecture.md`](architecture.md) — the decomposition, the consumer pattern, the freshness bar.
- [`../../residuals.md`](../../residuals.md) — the priced residuals: the cross-store orphan, the
  stale-key deposit, the compromised-current-device drain, no-cross-submitter-dedup.
