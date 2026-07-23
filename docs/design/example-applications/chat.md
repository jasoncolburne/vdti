# chat — the ratcheting group conversation

`chat` is the long-lived conversation: a group whose membership churns over years, whose messages
stay confidential against both outsiders and ex-members, on any member's devices. It is a UI over
the **exchange** feature's session mode — the composition case for exchange with the group-key
ratchet underneath — and a 1:1 conversation is the degenerate group of two, deliberately not a
separate construction
([`../features/exchange.md` §The session mode](../features/exchange.md#the-session-mode--chat)).

## The composition

Everything is the session mode as specified; the app adds rendering:

- **Keying is the group-key epoch ratchet.** A membership change turns the epoch; a removed member
  holds keys for the past it legitimately read and nothing after — forward secrecy as a structural
  consequence of removal, not a re-encryption project.
- **Messages are per-writer lanes.** Each writing device's messages chain in its own single-parent
  lane rooted at a grant-anchored marker; the lane is the writer (no sender field to forge), the
  signature attributes to the owning identity, and a second child of any message is an undeniable
  self-signed equivocation. Ordering rides `(epoch, timestamp)`, non-decreasing per lane, so
  backdating forks visibly instead of landing quietly.
- **The store checks membership per requester.** The `chat-membership` instance gates deposit and
  fetch — resolved one self-identifying requester at a time, never a materialized roster, so a
  non-member neither writes nor drains and no downloader enumerates the group. Removal records a
  per-lane `bound` the **verifier** enforces — a removed member's forward-append, below-bound fork,
  and fresh unanchored lane all fall outside the honored interval by a local check against durable
  data.
- **Catch-up is the union of your membership periods.** An intermittent member walks the epoch log
  and unwraps exactly the epochs it was in; blobs are retained across the catch-up window (the one
  place chat's retention deliberately differs from mail's ack-and-delete).

## Scenarios

- **Years-long group.** Members join, leave, rejoin; each stint is a disjoint anchored lane bracket;
  the current epoch always seals to exactly the current members. Nothing re-encrypts history, and no
  server ever holds a group key.
- **Remove a member.** One rescission: the epoch turns, their lanes close at their bounds, the store
  refuses their requests — three consequences from one recorded act, each independently verifiable.
- **A member equivocates.** Two signed successors to one lane point converge at any honest member as
  a provable same-writer fork; the group's policy — not the structure — decides the social
  consequence, with the structure holding the evidence.
- **New device.** The identity adds it; it derives the lanes' subkeys for the epochs its identity
  holds and reads the same history — membership is per identity, writing per device, exactly the
  split the mode draws.

## What this validates

- **Group confidentiality under churn from data alone.** The hardest ongoing-secrecy shape in the
  catalogue runs with no key server, no admin console, and every security-relevant transition —
  join, removal, epoch turn, lane bound — a witnessed, walkable fact.
- **Two authorization structures compose without drifting.** The member-held wrap roster (keys) and
  the store-checked membership set (service) are different structures with different readers, and
  the design's coupling rule — the wrap set derives from both, removal reads from either — holds up
  under the app that stresses it hardest.
- **Equivocation evidence beats equivocation prevention.** Chat accepts that a writer can fork its
  own lane and makes the fork undeniable and confined — the system-wide detection posture, exercised
  at message granularity.

## Limits

- **One device's signature, not a quorum.** A chat message authenticates a single writing device — a
  deliberately lower bar than mail's `t_use` quorum, priced for volume; one compromised member
  device authors in its identity's name within its windows, bounded by its lane and epochs.
- **The group's home nodes see the writer set and volume-timing** — the stated residual; the
  membership graph itself stays participant-blind.
- **The open epoch's future-dating gap** — accepted, self-harming, and closable by deployments that
  want mail's future-side clock bound; a dormant member's late history into epochs it held reads as
  legitimate, the chat instance of the backdate-within-a-held-window class. Both stated by the
  feature, inherited without decoration
  ([`../features/exchange.md` §The session mode](../features/exchange.md#the-session-mode--chat)).
