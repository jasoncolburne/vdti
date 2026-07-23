---
name: create-application
description:
  Guide the design of a new application on VDTI — requirement gathering, adversarial
  pressure-testing, composition derivation from the design tree, and landing the app's design doc in
  its own directory beside this repo. Implementation and code templates are deferred until the VDTI
  implementation lands.
---

# Create a VDTI application

You are guiding a person from an application idea to a landed application design, composed from the
VDTI design surface. Work the phases in order; each ends with the user's explicit sign-off before
the next begins. Do not skip the pressure-test, and do not invent mechanisms — if the design tree
cannot express a requirement, that is a finding to surface, not a gap to fill with new machinery.

## Phase 0 — Orient

Read, in this order: `docs/design/AGENTS.md` (how to read the tree), `docs/design/TOC.md` (the
per-section map), `USES.md` at the repo root (the composition catalogue and core patterns), and skim
`docs/design/example-applications/` — seventeen worked designs, one per distinct feature/primitive
composition. They are the case book: every derivation below starts from the nearest of them.

## Phase 1 — Target

Establish, with the user:

- **The application's name** — short, single-word, an actor or artifact (`registrar`, `drive`).
- **The landing path** — the app lands in its **own directory, parallel to this repo**: default
  `../<app-name>` relative to the vdti repo root. Ask the user to confirm or override the path
  before creating anything. Offer to `git init` it. **Nothing lands inside the vdti repo** — the app
  is the user's; vdti is its substrate.

Everything this skill produces goes under that directory: `<target>/design/<app-name>.md` now; code
later, when the implementation phase unlocks.

## Phase 2 — Requirement gathering

Elicit and write down (in `<target>/design/requirements.md`, kept as the working record):

- What the application is, in one paragraph, and who its parties are — people, organizations,
  services, and which of them (if any) must run a server.
- For each piece of data: must it be **proven** (who wrote it, when, under what authority), **moved
  secretly**, **evolved collaboratively**, **looked up live**, or merely stored? Map each answer to
  the core patterns in `USES.md` §The core patterns.
- Authority questions: who vouches for whom, what gets revoked, who decides acceptance. Note every
  place an acceptance rule could be a committed policy SAD.
- What the application must NOT do (privacy lines, regulatory scope, explicit non-goals).

## Phase 3 — Pressure-test the requirements

An adversarial pass over the requirement list, before any design exists:

- For each requirement, name the attacker and the failure it causes if the requirement is met
  naively. Apply the reasoning-smell test from `docs/design/system-thesis.md` — "under valid input"
  and "no one would do X" are disqualified arguments.
- Sort each requirement into **structural** (the substrate can enforce it), **application-layer**
  (policy, arbitration, workflow — the app's own logic over proofs), or **out of scope for the
  substrate** (check `docs/design/residuals.md` and the **Limits** sections of the nearest example
  apps — recurring examples: secrecy from storage operators without client-side encryption, recall
  of already-published bytes, coercion-resistant secrecy, per-field write authority, physical-world
  binding).
- Rewrite the requirement list with each item tagged by that sort, out-of-scope items either dropped
  with the user's agreement or re-scoped to what the substrate honestly provides.
- **Sign-off gate**: the user approves the pressure-tested list before design begins.

## Phase 4 — Derive the design

- **Find the nearest compositions.** Match the requirement tags against the seventeen
  example-application docs and pick the closest one or two; the new design is a delta from them, not
  a blank page. State which apps it is nearest to and what differs.
- **Select the composition** — which features and primitives, and why each requirement lands on
  which mechanism. Every mechanism must resolve to a real section of the design tree (use `TOC.md`;
  cite the owning section, not a summary site).
- **Write `<target>/design/<app-name>.md`** in the established shape: intro (what it is, what it
  absorbs or resembles) → **Deployment** (a mermaid party-block diagram — who runs what, with the
  substrate strip, captioned with who runs a server) → **The composition** (the snap-together, every
  mechanism cited) → **Scenarios** (the load-bearing flows) → **What this validates** → **Limits**
  (honest, in the example-apps' voice). Because the app dir sits beside the vdti checkout, cite
  design docs as `../../vdti/docs/design/…` relative links (state that assumption in the doc) or as
  pinned GitHub URLs.
- Validate the diagram with `mmdc`. Re-check every citation resolves. Walk the finished design
  against the pressure-tested requirement list, item by item, and record the mapping.
- **Sign-off gate**: the user approves the design doc.

## Phase 5 — Implementation (deferred)

Code templates (`docs/design/templates/`) and the implementation walk land once the VDTI
implementation exists. Until then: stop after the design doc, and record in
`<target>/design/requirements.md` any implementation-relevant decisions already made (harness shape,
which fixture roles need an `issuer` instance, deployment topology) so the future phase starts warm.

## Done criteria

- The design doc and requirements record are landed at the confirmed parallel path; the vdti repo is
  untouched.
- Every cited mechanism resolves to a real section; the deployment diagram renders under `mmdc`.
- The user has signed off twice: on the pressure-tested requirements, and on the design.
