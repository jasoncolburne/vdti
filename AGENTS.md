# VDTI — Verifiable Decentralized Trust Infrastructure

VDTI is a framework for building high-trust applications on decentralized, tamper-evident, authentic
data. System state lives in append-only chains of cryptographically-linked events that entities
throughout the network hold and verify independently — no central authority, no trust by fiat.

Status: **Phase 0** (design completion). Doctrine in `docs/design/` is the canonical source; code
lands in Phase 1+.

## Orientation

Read [`docs/design/system-thesis.md`](docs/design/system-thesis.md) **before doing substantive work
on vdti**. It captures the system thesis and the adversarial-first posture that all design decisions
are evaluated against.

Load-bearing principles to internalize:

- **Fail secure, not safe.** When the system can't determine an answer with confidence, refuse
  rather than guess.
- **Think like the attacker.** Assume adversarial input always. "Under valid input" / "happy path" /
  "this branch can't fire" are security smells — if the precondition is attacker-controlled, the
  branch can fire.
- **Compromise is permanent.** Authority belongs to current state only — past keys, past policies,
  past endorsers have zero structural ability to act once supplanted.
- **Correctness is the only metric.** The design is structurally interlocking; cheaper / easier /
  faster doesn't dominate "more likely correct." Wrong doctrine produces wrong code; wrong code
  collapses end-verifiability.

Detailed doctrine lives in `docs/design/` — primitive specs (KEL / IEL / SEL), federation
witnessing, federation bootstrap, kind-strict anchoring, divergence handling, irreconcilable-prefix
surface, custody, policy DSL, verification. AGENTS.md does not duplicate; consult the design docs
directly.

## Repo Layout

See [vdti#1](https://github.com/jasoncolburne/vdti/issues/1) (the v1 roadmap) for the full layout
and Phase 0–9 sequencing. Quick orientation:

- `lib/encoding/`, `lib/storage/`, `lib/cache/` - reusable libs.
- `lib/vdti/` — protocol core: KEL / IEL / SEL primitives, the verifier / merge / transfer engine,
  the SAD store + custody, gossip (Cargo feature flag); linked by both `vdtid` and consumers
  (end-verifiability). Policy is the **document layer**, not a primitive.
- `lib/mail/`, `lib/exchange/`, `lib/creds/` — application shims; depend on `vdti/`.
- `lib/derive/` — KEL signed-events repo derive macros. KEL only — IEL and SEL events anchor in KEL
  events, not directly signed.
- `lib/ffi/` — Rust → C bindings.
- `services/vdtid/` — main service daemon. Consolidates KEL submission, SAD storage, and IEL / SEL
  hosting.
- `services/witnessd/` — witness / gossip service daemon. Imports the HSM consumer lib from
  `infrastructure/mock-hsm/` for signing keys.
- `cli/vdti/` — CLI binary.
- `infrastructure/{objects,database,kvstore,mock-hsm}/` — deploy configs + HSM service. `mock-hsm/`
  builds a consumer lib that services import; production swaps the HSM behind the lib without
  service changes.
- `examples/messaging/` — iOS / Android demo (ports the kels iOS surface + adds messaging).
- `docs/{design,reference,operations,analysis}/` — design completion (Phase 0).
- `tests/` — e2e scenario suite (port of `kels/clients/test/`); benchmarks under `tests/bench/`.

## Build & Verify

- `make` verifies changes (lint-terminology, lint-docs, fmt, deny, clippy, test, build). Never use
  naked cargo commands.
- The doc linters work from day one — `lint-terminology` and `lint-docs` (doc cross-references);
  `make all` runs them alongside `fmt-md-check`, and CI runs each as its own job. The code targets
  (fmt, deny, clippy, test, build) become meaningful as the Cargo workspace lands in Phase 1.
- When landing a rename, add retired tokens to `.terminology-forbidden` so `make lint-terminology`
  catches future regressions.
- `TEST_ARGS` on `make test` forwards flags to `cargo test` for iterating on one suite or one
  package. Still run the full `make` before calling a change done.
- **`make` is slow (minutes). Run it ONCE and tee output to a file**, then grep/tail the file
  repeatedly instead of re-running: `make 2>&1 | tee /tmp/make.log`. Do not run `make | tail -N`
  then `make | grep foo` then `make | head -N` — you just burned 3× the time for one build.
- Garden orchestrates infra + services for e2e tests.
- After substantial changes: deploy → federation → witnessing → gossip → adversarial tests.

## Code Style

**Imports**: three groups (std, external, local), nested, blank-line separated. `rustfmt` handles
sorting within groups. Fix grouping when touching a file.

```rust
use std::{collections::HashMap, sync::Arc};

use anyhow::Result;
use vdti_storage::{SelfAddressed, StorageError};

use crate::{handlers::AppState, repository::CoreRepository};
```

**Rules:**

- Fail **secure**, not safe.
- Greenfield — no transition language. Edit migrations and design in place; don't preserve
  "previously X" / "and not v\_{tip-1}" helper phrases.
- Never hardcode event / record kind strings — use enum methods.
- Never `.unwrap()`. Use `.expect("reason")` with `#[allow(clippy::expect_used)]`.
- Use `vdti-encoding` types for all cryptographic material. Parse at boundaries, pass typed values.
- `create()` not `new()` for `SelfAddressed` types (`new()` leaves SAID as placeholder).
- Sign the SAID's QB64 bytes, never serialized payloads.
- All HTTP endpoints: POST with JSON bodies. No identifiers in URL paths or query params.

## Doc Style

**Diagram annotations.** In ASCII diagrams (chain shapes, scenario walkthroughs, state transitions),
keep in-diagram text terse — short pointer labels like `(tip)`, `(adversary)`, `→ divergent`,
`(terminal)`. Multi-sentence explanations of _why_ a step does what it does go in prose above or
below the diagram, not inside it. The reader's eye can't track both an ASCII layout and
paragraph-length annotations at the same time; separating the two lets the diagram carry shape and
the prose carry argument.

**Cross-repo issue refs.** Bare `#NNN` autolinks to the current repo. When referencing kels issues
from vdti docs, code, or issue bodies, write `kels#NNN` (or `jasoncolburne/kels#NNN`). Search
`(post-|per |under )#[0-9]+` before submitting cross-repo prose.

**Bullets over prose** for dense information (lists, scope rails, deliverables, decisions). Prose
only for narrative.

## Event Transfer

All multi-page event transfers use the `transfer_*_events` infrastructure in `lib/vdti/`. Never use
single-page `fetch_*_events` in loops — manual pagination bypasses tamper-evident protection.

Key functions:

- `forward_*_events` — server-side fan-out.
- `verify_*_events` / `completed_verification` — consume; returns a `Verification` token.
- `collect_*_events` / `resolve_*_events` — client-only; accumulates the chain into memory.

See `docs/design/` for the full event-transfer doctrine (tamper-evident protection at page
boundaries, verifier tokens, divergent-chain sub-batch partitioning).

## Verification Invariant

The DB cannot be trusted. **The verifier is the trust boundary** — every chain-validity invariant
lives in the verifier walk / completion. Trust only the data; not services, DB, or peers.

Three categories of operation:

1. **Serving** — no verification; receiver verifies.
2. **Consuming** — requires `Verification` token from the verifier's `into_verification()`.
3. **Resolving** — wrong answers trigger unnecessary syncs, not security holes.

End-verifiability means a verifier with **data from any source** plus the trusted federation
prefixes can determine system-wide state — including attack exposure. Source location matters for
cost, not trust.

## Working Conventions

- **`.working/`** is gitignored. Durable in-progress docs (issue / PR bodies, design drafts, audit
  outputs, agent briefs) live there per the `kels/` precedent. Filenames follow `vdti-{N}-{slug}.md`
  once an issue number is assigned, or `vdti-{slug}.md` pre-submit.
- **Design canon (`docs/canon/`).** The `vdti-area-*.md` area canon, `vdti-invariants.md`, and
  `vdti-implementation-notes.md` are tracked under `docs/canon/` (line-per-concept, prettier-exempt
  — stable `file:line` review refs). Unlike `docs/design/`, the canon tracks history
  (greenfield-exempt).
- **`.working/` surface.** Organized around `00-INDEX.md` (the read-order map), `design-resume.md`
  (live state — read first to resume), the review briefs / findings, and the roadmap (synced to
  [vdti#1](https://github.com/jasoncolburne/vdti/issues/1)). Keep the index, resume, and roadmap
  **current**; **archive aggressively** — the day a doc is superseded move it to `archived/`
  (recoverable), don't leave drift.
- **Design process.** Design notes go in `.working/` area docs → dual-pass review → iterate until
  **sound**; then encode into `docs/design/` **one concept per PR** → dual-pass review each PR until
  **polished** → Jason reviews each PR before it lands.
- **Issue / PR body workflow.** Long bodies go in `.working/` and are submitted via
  `gh issue create --body-file` / `gh issue edit N --body-file`. Don't inline heredoc long bodies.
- **Commit posture.** Don't commit unless explicitly asked. When asked, "commit this" is scoped to
  the named change only.
- **Multi-agent audit reviews.** Outputs land in `.working/` (durable, gitignored). The 5-axis audit
  (security, correctness, completeness, readability, accessibility) gates Phase 0 closure.
- **When in doubt, read.** vdti protocol semantics live in `docs/design/`. Reconstructing from
  priors is unreliable — read; don't reason.
- **When corrected, ask — don't reconstruct.** A negative signal alone doesn't pin the right answer.
