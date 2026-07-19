# ⚠️ Design in progress ⚠️

# VDTI — Verifiable Decentralized Trust Infrastructure

**Build apps where the data proves itself — and skip the trusted backend.**

Most apps ship on a backend everyone has to trust: an auth server, a database, an API. VDTI turns
that middle into composable, verifiable primitives. Every record carries its own tamper-evident
proof of who created it, when, and under what authority — so any client can verify everything
itself, from any source, with no service to trust. You write the app; you don't build, secure, or
run the trusted middle.

## Compose, don't build

Underneath, you get the things every backend gives you — as verifiable primitives you snap together:

- **Data with custody** — content that carries a provable writer and a controlled read-set. Storage,
  provenance, and access control in one primitive.
- **Logs** — single-owner, append-only, tamper-evident. Audit trails and event sourcing, free.
- **Identity** — a person or organization as a threshold of their own devices: the unit you
  authenticate and issue to, independent of any single device.

Then three **features** escalate for the genuinely hard problems — and they compose:

- **Shared documents** — collaborative, branch-and-merge, membership-governed. It is essentially
  git: a signed, attributed DAG, indexed for lookup.
- **Exchange** — secure delivery and key distribution. One-to-one and ratcheting group messaging.
- **Credentials** — delegated, revocable authority. One identity vouches for another, verifiably.

Most of what you would build is just data with custody. Reach for a feature only for the hard thing
it owns; combine features for the rich apps — a group chat is exchange + shared documents, a
supply-chain recall is credentials.

**→ See [`USES.md`](USES.md) for the full catalogue — dozens of applications and exactly how each
one composes.**

## What you get for free

Every app you compose inherits, by construction:

- **Tamper-evidence** — a changed record breaks its own proof.
- **Provenance** — who did what, when, and under what authority travels _with_ the data.
- **End-to-end verification, no trusted server** — the client checks its own work against the data,
  from any source; there is no service to believe. (Authenticity verifies with no network;
  confirming a credential is _not revoked_ needs a fresh read — see below.)
- **Revocation** — an issuer can revoke; a verifier confirms not-revoked from a fresh read of the
  issuer's chain (any source) and **fails secure** by default (an application may opt into
  fail-open).
- **Incident response by design** — a compromised or lost key is a **rotation**; a bad device is a
  **roster cut**. What forces a truck roll or a fleet re-provision elsewhere is a single in-band
  chain event here.

Whole classes of bug stop being possible: "trust the server" auth bypasses, silent tampering, murky
provenance, and "who had access when" forensic gaps.

In contrast to systems like KERI (a Decentralized Key Management Infrastructure), where system-wide
state must be inferred through out-of-band watcher infrastructure, VDTI lets any verifier determine
system-wide state — including whether an identity has **diverged or been compromised** — from the
data itself, with no watcher infrastructure.

## Who runs it

No central operator. The organizations that issue and rely on trust run the witnessing
infrastructure — and in doing so support the whole network. Federations partition the network; a
verifier can trust several by configuration, and an identity moves between them freely. Trust comes
from cooperation, not from a single party you have to believe.

## Built to last

VDTI uses post-quantum cryptography, with the root of trust in device hardware. It is built for the
next fifty years, not the last ten — for the people and institutions whose secrets and identities
have to outlive every key they ever use.

## Status

**Phase 0: Design completion.** Doctrine is being ported and revised in
[`docs/design/`](docs/design/); code lands in Phase 1+. See the
[v1 roadmap](https://github.com/jasoncolburne/vdti/issues/1) for the full plan: mission, audience,
repo layout, 9-phase v1 sequencing, and acceptance criteria.

## Documentation

- [`USES.md`](USES.md) — what you can build, and how each application composes.
- [`MODEL.md`](MODEL.md) — a plain-English description of VDTI and its rules.
- [`docs/design/`](docs/design/) — protocol design and doctrine (start with its
  [`README.md`](docs/design/README.md) for the full reading order, beginning with
  [`system-thesis.md`](docs/design/system-thesis.md) for orientation).
- [`docs/reference/`](docs/reference/) _(forthcoming)_ — primitive references, attestation modes,
  KERI comparison.
- [`docs/operations/`](docs/operations/) _(forthcoming)_ — deployment, backup, node retirement,
  shadow-node patterns.
- [`docs/analysis/`](docs/analysis/) _(forthcoming)_ — attack surfaces, scale, protocol analysis.

## Contributing

VDTI is in the design-completion phase; the canon is nearly complete. If you are considering
contributing, the v1 roadmap ([vdti#1](https://github.com/jasoncolburne/vdti/issues/1)) lays out the
planned phases and where work is happening. Use the issue templates (Doctrine, Implementation, Bug,
Tracker) to file new items.

To work on VDTI with an LLM, point it at [`docs/canon`](docs/canon) — VDTI's design notes. The
workflow flows one way: the canon is propagated into **doctrine** (the design docs under
[`docs/design`](docs/design/)), which is then translated into implementation. Design docs follow
three rules: no jargon, greenfield voice, and human-readable slug refs.

## License

MIT. See [LICENSE](LICENSE).
