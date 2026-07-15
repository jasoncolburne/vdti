# Gossip topics — the federation mesh channels

Every event reaches the nodes that need it over **gossip**, the federation witness mesh's
propagation layer. A **gossip topic** is a mesh channel — a pub-sub subject naming _what_ rides the
mesh. This doc catalogues the topics and states the transport they run on; the guarantees that rest
on propagation — first-seen, the witnessing floor, query-scoping — are
[`witnessing.md`](witnessing.md).

The mesh **is** the federation roster, and it carries only what stays within the federation: all
inter-node traffic is encrypted (ML-KEM-1024 + AES-256-GCM) — receipts and the events they carry
alike — so mesh contents never leave the roster. The channel underneath — how two nodes
authenticate, agree a key, and encrypt each frame — is
[`../infrastructure/mesh-transport.md`](../infrastructure/mesh-transport.md).

## Two meshes

Gossip runs at two scopes:

- **Roster-wide (push-gossip).** Once an event is **witnessed in full** it is pushed to every node —
  submission-time fan-out plus continuous anti-entropy — so a node ordinarily sees a completed
  quorum before any later sibling arrives. The propagation window is bounded, but the bound is
  **operational**: the doctrine asserts only the eventual property (every node eventually holds
  every accepted event).
- **Selected witnesses (sub-gossip).** A **not-yet-witnessed** event lives among the witnesses
  selected for its position while it gathers receipts; they sub-gossip it among themselves, so the
  first-seen sibling reaches threshold once it reaches any one honest selected witness. A
  sub-threshold event is returned by a query **only to a selected witness** for that position — to
  every other node it is withheld, which is what keeps a non-witness holding only witnessed-in-full
  events ([`witnessing.md`](witnessing.md)).

## The topics

Pub-sub channels on the `vdti/gossip/v1/*` convention
([the shared naming convention](../../primitives/data/sad/kinds.md#the-naming-convention)). A topic
names _what_ rides the mesh, never _how_:

| Topic                            | Carries           |
| -------------------------------- | ----------------- |
| `vdti/gossip/v1/witness/receipt` | a witness receipt |
| `vdti/gossip/v1/kel/event`       | a KEL event       |
| `vdti/gossip/v1/iel/event`       | an IEL event      |
| `vdti/gossip/v1/sel/event`       | a SEL event       |

The list grows as the system adds propagated payloads. A gossip topic is **not** a SAD and **not** a
derivation input — it is a routing label, distinct from a SAD's `kind`
([`kinds.md`](../../primitives/data/sad/kinds.md)) and from a derivation tag or SEL topic
([`tags-and-topics.md`](../../primitives/data/event-logs/tags-and-topics.md)).

## Cross-references

- [`witnessing.md`](witnessing.md) — the mesh mechanics: first-seen, the witnessing floor,
  query-scoping, the propagation premise.
- [`bootstrap.md`](bootstrap.md) — genesis: the mesh forms once nodes set their federation prefix;
  before that, arrangement is point-to-point.
- [`../infrastructure/mesh-transport.md`](../infrastructure/mesh-transport.md) — the authenticated,
  encrypted channel the mesh runs over.
- [`../../protocol-doctrine.md`](../../protocol-doctrine.md) — how the primitives consume
  propagation (federation convergence).
- [`../../primitives/data/sad/kinds.md`](../../primitives/data/sad/kinds.md) — SAD kinds.
- [`../../primitives/data/event-logs/tags-and-topics.md`](../../primitives/data/event-logs/tags-and-topics.md)
  — derivation tags and SEL topics.
