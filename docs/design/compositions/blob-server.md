# BlobServer — the blob composition

`BlobServer` is the logic layer over a [`BlobStore`](../primitives/stores/blob-store.md): blob
admission, the `access` serve gate, and the delete capability. With `BlobClient` and its `Source` /
`Sink`, it is the blob stack the off-federation [`blobsd`](../substrate/infrastructure/blobsd.md)
deploys — the blob model itself (the bundle, the payload, `access`, admission, serving) is stated
there.

- **Admission verifies before anything persists**: the committing document set commits the payload
  key, the payload matches its bundle, and the anchoring resolves — composing a federation client
  for the public parts, under the token-bundle discipline
  ([`log-server.md` §Capability tokens and token bundles](log-server.md#capability-tokens-and-token-bundles)).
- **The serve gate is the `access` dispatch** — `roster` or `membership`, live-signed — and it is
  **one mechanism** with [`SadServer`](sad-server.md)'s third gate: the same generic
  [`membership`](../primitives/protocols/membership.md) resolution, encoded once. Operational, never
  the confidentiality boundary.
- **`delete(S)` is the deploying application's predicate**, exactly as on the SAD side — the server
  supplies the capability and the live check; no protocol rule says who may delete.
- **A blob `Sink` re-verifies**: it pulls a list of keys, fetches, checks the bytes hash to the key,
  and stores — no sync protocol beyond that, because the objects are immutable and self-naming.

## Cross-references

- [`../primitives/stores/blob-store.md`](../primitives/stores/blob-store.md) — the dumb store.
- [`../substrate/infrastructure/blobsd.md`](../substrate/infrastructure/blobsd.md) — the blob model
  and the deployable.
- [`sad-server.md`](sad-server.md) — the sibling composition sharing the serve-gate mechanism.
