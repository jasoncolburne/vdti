# pds — the personal data store

`pds` is your records, held and verified by you: the store a person's applications read and write
through, on hardware and hosts the person chooses. It is the composition case for **data with
custody plus logs**, and it absorbs the catalogue's same-composition variant, the **wallet backend**
— holding credentials and personal documents _is_ holding custodied SADs, no further machinery
required.

The drive showed custody alone building a hash-tree of owned data and hit one honest edge: a live
pointer to _evolving_ state is a log's job ([`drive.md`](drive.md)). The pds is that next step — the
same custodied records, now **indexed by the owner's own chains**, which is exactly the split the
catalogue's core patterns draw: store → custody; look up → a log.

## The composition

- **The root is the identity.** A person is an IEL over their devices — the unit everything below
  authenticates to. Records belong to the identity, not to any device, which is what makes every
  scenario below device-portable.
- **Records are custodied SADs.** Each document, note, backup, or held credential is a standalone
  SAD with the person as `owner` (anchored, backdate-proof) and `readers` as the person chooses —
  usually just their own read set, sometimes a clinician's or an accountant's
  ([`../primitives/data/sad/custody.md`](../primitives/data/sad/custody.md)). A held credential
  needs nothing extra: it is already a SAD, and holding it is storage, not issuance.
- **Indexes are content SELs.** Per domain — documents, health, finance, correspondence — the person
  runs a content SEL whose entries commit the domain's current records
  ([`../primitives/data/event-logs/sel/log.md`](../primitives/data/event-logs/sel/log.md)). The SEL
  tip is the **live pointer** the drive lacked: any device, walking the SEL, arrives at the current
  index with the chain vouching there is nothing newer being hidden — the freshness and divergence
  machinery of a witnessed chain, applied to "what is the current state of my stuff"
  ([`../primitives/data/event-logs/sel/log.md` §End-verifiability](../primitives/data/event-logs/sel/log.md#end-verifiability)).
- **Placement is the person's.** `availability.replicas` scopes records to chosen storage — a
  personal storage node is a store daemon with no witness beside it, first-class in the service
  architecture
  ([`../substrate/infrastructure/architecture.md` §The decomposition](../substrate/infrastructure/architecture.md#the-decomposition))
  — and the consumer-side **cascading store** composes the tiers: memory, then local disk, then the
  personal node, then a public node, one interface with the serve rules holding at whichever tier
  answers
  ([`../substrate/infrastructure/architecture.md` §The store traits](../substrate/infrastructure/architecture.md#the-store-traits--one-interface-composed-in-sequence)).

## Scenarios

- **A new device.** Joins the identity's roster, then rebuilds the entire store from nothing but the
  identity's chains: walk each index SEL to its tip, fetch every committed record by SAID, verify
  all of it locally. No backup file, no export format, no trust in the host it fetched from — the
  store _is_ its chains plus what they commit.
- **Moving hosts.** Re-point `replicas` and let replication carry the bytes; every record verifies
  identically from the new host. Source location is cost, not trust — exercised here as a practical
  migration story rather than a slogan
  ([`../system-thesis.md` §End-verifiability](../system-thesis.md#end-verifiability)).
- **An application acting for you.** A program operating the person's store reads and writes the
  same kinded SADs and chains everything else uses — one self-describing model it can generate,
  address, and verify locally
  ([`../system-thesis.md` §Uniform data](../system-thesis.md#uniform-data--a-program-can-operate-it-natively)).
  The pds is where that claim is most load-bearing: it is the surface personal agents operate.
- **Sharing one record.** Stamp the clinician's read set on that record — custody is per-object, so
  nothing else opens. The index SEL itself can stay private; sharing a record does not disclose the
  shelf it sits on.

## What this validates

- **The custody/log split is the right factoring.** Everything static is a custodied SAD; everything
  evolving is a chain; the two compose with no third mechanism. The drive's honest edge closes
  exactly where the catalogue said it would.
- **Identity decoupled from devices is a working recovery story.** The new-device scenario is the
  thesis's decoupling claim made operational: devices are replaceable; the identity and its data
  survive them.
- **Self-custody without self-verification is not asked of anyone.** The person's devices verify
  everything through the same core library the infrastructure runs — holding your own data does not
  mean auditing it by hand
  ([`../substrate/infrastructure/architecture.md` §The core is a library](../substrate/infrastructure/architecture.md#the-core-is-a-library-because-consumers-must-verify)).

## Limits

- **At-rest privacy from storage operators is client-side encryption**, an application pattern above
  the protocol — the same limit the drive states, unchanged by adding logs.
- **Delivering records secretly to another party is exchange's composition** — the pds shares by
  read-gating what it already holds; it does not seal or transport.
- **Losing the identity loses the store's authority.** Below-threshold device loss is the
  identity-recovery doctrine's domain, not the pds's; the store's records remain verifiable as
  written, but advancing them requires the identity. Run the roster with redundancy — the same
  advice the identity layer already gives
  ([`../system-thesis.md` §Defense against current-state compromise is layered](../system-thesis.md#defense-against-current-state-compromise-is-layered)).
