# lib/storage — planning stub

**Status:** planning. Not yet filed as a vdti sub-issue. Enhance as more design / integration details accumulate; file once scope is stable.

**Destination when filed:** Likely a Phase 1 sub-issue covering the absorbed `verifiable-storage-rs` and its integration surface with `lib/vdti`.

## Library overview

- `lib/storage` is the absorbed `verifiable-storage-rs` (sibling repo at `../verifiable-storage-rs/`). Provides the canonical storage primitive for verifiable types: SAID derivation, prefix derivation, chained-event repository, postgres backend.
- Public surface includes the `SelfAddressed` + `Chained` traits, the `#[derive(SelfAddressed)]` macro, the `Storable` trait, and the `#[storable]` attribute that generates postgres schema for tagged structs.
- Imported by `lib/vdti` for all SAID-bearing struct definitions (KEL events, IEL events, SEL events, SAD wrappers).

## KEL anchor-array storage notes

The KEL primitive doctrine (per vdti#10 Steering-3) commits to a flat `anchors: Vec<Digest256>` field on chain events that carry anchors. The doctrine specifies the per-kind anchor-list schema (Fcp/Rec/Dec empty; Icp/Fed exactly 1; Dip exactly 2; Ixn ≥1; Rot/Ror ≥0) and position-by-kind verifier dispatch (no in-data role labels).

**Storage shape.**

- Rust: `pub anchors: Vec<cesr::Digest256>` on event structs. Homogeneous element type; ordered by position.
- Postgres: `text[]` column (or `bytea[]` if SAIDs are stored as binary; current vdti convention is qualified-base64 text). The `#[storable]` derive in `lib/storage` should map `Vec<Digest256>` → `text[]` (or equivalent array column) without per-kind specialization.

**Why a flat array (not tagged objects):**

- **Privacy.** No in-data role labels (`"kind": "federation"`, `"kind": "delegator"`, etc.) — the SAIDs themselves are opaque; structural role is dispatched from the host event kind, which is already in the event. No new side-channel from anchor structure.
- **Storage compatibility.** Homogeneous-typed sequence maps cleanly to native postgres array storage (`text[]`); tagged objects would force jsonb columns or parallel arrays.
- **Schema simplicity.** One column per event row; ordered by position; indexed via GIN if reverse-lookup ("which KEL events anchor SAID X") is needed downstream.

**Per-kind schema validation** lives at `lib/vdti` (the chain-event structs and verifier), NOT at `lib/storage`. `lib/storage` provides the generic storage primitive; per-kind anchor-list rules (position dispatch, count constraints) are protocol-layer concerns enforced by the verifier walk.

## Other integration notes

- Forward-key commitments (`rotationHash`, `recoveryHash`): `Option<Digest256>` fields on establishment-kind structs.
- Two-hash inception derivation (prefix-then-said per `verifiable-storage-rs/lib/verifiable-storage-derive/src/lib.rs`): handled by the `#[derive(SelfAddressed)]` macro's `create()` generator. KEL inception structs declare both `#[said]` and `#[prefix]` fields.
- Chain-log schema generation: `#[storable(table = "kel_events")]` (or similar) on the KEL event struct generates the insert / select SQL; `anchors text[]` is one of the columns.

## Open / to-collect

- Concrete struct layout for KEL events (Fcp / Icp / Dip / Fed / Ixn / Rot / Ror / Rec / Dec) — likely a tagged-union via `serde(tag = "kind")` or per-kind structs with a shared trait. Affects which `#[storable]` rows go where.
- Postgres index strategy for `anchors` (when does reverse-lookup justify a GIN index?).
- Schema-evolution policy for the per-kind anchor-list shape (the doctrine doesn't anticipate adding structural roles; `lib/storage` doesn't need to support hot schema migration).
- Cross-primitive: IEL / SEL event structs land in subsequent sub-issues; their storage shape follows the same pattern as KEL.

## Forward-refs

- `lib/vdti` — protocol-layer event structs that derive `lib/storage` traits.
- `infrastructure/eventsd.md` (subsequent sub-issue) — the chain-log service; consumes `lib/storage` for postgres CRUD.

## Filing notes

When ready to file (likely Phase 1):

- Title: `Phase 1: lib/storage absorption + integration (vdti-storage)`.
- Label: `implementation`.
- Body: derive from this stub once scope is stable. Will include port-from-`verifiable-storage-rs` plan, integration with `lib/vdti` event structs, postgres schema generation for KEL / IEL / SEL chain logs, and SAD-object storage at the standalone-SAD layer.
