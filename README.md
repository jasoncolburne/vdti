# VDTI — Verifiable Decentralized Trust Infrastructure

VDTI lets users control their identity and data without relying on a central authority. Devices are
decoupled from the identity that operates them; identity and policy are first-class, composable
primitives. In contrast to solutions like KERI (a DKMI, Decentralized Key Management
Infrastructure), where system-wide state must be inferred via out-of-band watcher infrastructure,
VDTI lets any verifier determine system-wide state — including attack exposure — by inspecting data
from a single source.

It's a framework for building high-trust applications from the ground up.

## Status

**Phase 0: Design completion.** Doctrine is being ported and revised in
[`docs/design/`](docs/design/); code lands in Phase 1+.

See the [v1 roadmap](https://github.com/jasoncolburne/vdti/issues/1) for the full plan: mission,
audience, repo layout, 9-phase v1 sequencing, acceptance criteria.

## Audience

General-purpose. Any application requiring identity composes naturally on VDTI's primitives.

Three attestation modes drive most credential flows:

- **Property attestation** (you own X) — tickets, passes, goods-in-transit.
- **Identity attestation** (you are X) — age verification, travel, hiring.
- **Capability / certification attestation** (you've been verified to have X) — background checks,
  education, training, health records.

## Documentation

- [`docs/design/`](docs/design/) — protocol design and doctrine.
- [`docs/reference/`](docs/reference/) — primitive references, attestation modes, KERI comparison.
- [`docs/operations/`](docs/operations/) — deployment, backup, node retirement, shadow-node
  patterns.
- [`docs/analysis/`](docs/analysis/) — attack surfaces, scale, protocol analysis.

Start with [`docs/design/system-thesis.md`](docs/design/system-thesis.md) for orientation. See
[AGENTS.md](AGENTS.md) for contributor workflow conventions.

## Contributing

VDTI is in the design completion phase. If you're considering contributing, the v1 roadmap
([vdti#1](https://github.com/jasoncolburne/vdti/issues/1)) lays out the planned phases and where
work is happening. Use the issue templates (Doctrine, Implementation, Bug, Tracker) to file new
items.

## License

MIT. See [LICENSE](LICENSE).
