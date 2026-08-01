# BlobStore — the dumb blob store

`BlobStore` is the persistence trait for content-addressed blobs — the bulk bytes a bundle commits,
keyed by `S = hash(payload)`
([`sad.md` §Bulk opaque bytes](../data/sad/sad.md#bulk-opaque-bytes--the-content-addressed-blob)).
It is **dumb**: bytes in, bytes out, by key, paginated — admission, the serve gate, and deletes live
one layer up, in the [`BlobServer`](../../compositions/blob-server.md).

## The trait

| Operation     | Returns                                                                |
| ------------- | ---------------------------------------------------------------------- |
| `page(since)` | the update-ordered listing of held keys, over the store's object index |
| `get`         | the bytes by key                                                       |
| `put`         | store bytes by key                                                     |
| `delete(S)`   | remove the bytes by key — a **capability** the composing server grants |

`page(since)` exists because a replicated deployment's blobs need a sync path: without an
enumeration over the object index, the blob half of every replicated deposit would have no way to
ride anti-entropy. A blob `Sink` pulls a list of keys, fetches, checks `hash(payload) == S`, and
stores — no sync protocol beyond that, because the objects are immutable and self-naming.

## Capabilities

The same grants as [`SadStore`](sad-store.md)'s, for the same reasons: **`delete` is a capability
the composing server gates** (the deploying application supplies the predicate —
[`blob-server.md`](../../compositions/blob-server.md)); **`page` is `in-process | mesh`, never
`public`** (a public enumeration of payload keys defeats digest-secrecy outright). And, as there,
**there is no existence probe**: a refused fetch is the uniform "not present", and a probe would be
a cheaper way to ask the same question — cheap is what makes an oracle worth running.

## What the store never does

It never verifies a bundle, never resolves an anchor, never evaluates `access`. A blob is opaque
bytes — no `kind`, no `custody`, no `availability` of its own; everything that governs it rides its
committing bundle, evaluated by the [`BlobServer`](../../compositions/blob-server.md) and by
consumers.

## Cross-references

- [`../../compositions/blob-server.md`](../../compositions/blob-server.md) — blob admission, the
  `access` serve gate, deletes.
- [`log-store.md`](log-store.md) / [`sad-store.md`](sad-store.md) — the sibling traits.
- [`../data/sad/sad.md`](../data/sad/sad.md) — the content-addressed blob and what commits it.
