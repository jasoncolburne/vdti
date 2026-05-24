# KEL Reconciliation — Multi-Node Correctness Matrix

This doc is the **load-bearing correctness proof** for the KEL primitive. It exhaustively enumerates every combination of (per-node chain state) × (submitted batch shape) × (cross-node gossip state), and demonstrates that each case terminates correctly under the merge-layer routing rules and that all nodes converge on the same effective SAID across the federation. Without this matrix, the merge engine, the gossip layer, and the federation-witnessing layer are not proven sound — they are designed against this enumeration. Cross-node convergence as a doctrinal property is stated upstream at [§Federation Convergence](../../../../protocol-doctrine.md#federation-convergence); this doc is the per-primitive proof.

For lifecycle prose (states, locked-portion bound, page model), see [`log.md`](log.md). For per-kind reference (event kinds, fields, three-tier capability model), [`events.md`](events.md). For the merge-layer routing rules being proved sound, [`merge.md`](merge.md). For recovery doctrine (Rec parent shapes, dual-signature defense), [`recovery.md`](recovery.md). For the verifier walk, [`verification.md`](verification.md).

## Proof structure

The proof composes three matrices:

1. **Local submissions matrix** — what every submission to every chain state produces on a single node. Demonstrates that the merge-layer routing rules are exhaustive and terminate correctly.
2. **Source → sink transfer matrix** — what gossip propagation between two nodes produces, for every combination of source and sink chain states. Demonstrates that gossip-driven sync converges per-node states under the merge rules.
3. **Race matrix** — what concurrent privileged-event races produce across federation peers. Demonstrates that the seal-cap and locked-portion bound are sound under adversarial concurrency, and that the federation-witnessing layer carries the cross-node disagreement signal.

All three matrices depend on the same protocol-enforced invariants, stated next.

## Invariants

The cases below depend on these protocol-enforced invariants. They are stated structurally — the protocol's safety claims hold *by construction*, not by observation.

1. **Seal-advance cap compliance.** Every KEL has a seal-advancing event (`Rec` / `Ror` / `Rot` / `Fed`) at least every `MINIMUM_PAGE_SIZE − 2 = 62` non-seal-advancing events. Surfaced by the verifier and enforced by the merge handler. See [`events.md` §Seal-advance cap](events.md#seal-advance-cap).
2. **Bounded divergence.** An adversary can only fork after the last seal-advancing event (forking before triggers `ParentLocked` per the locked-portion bound). Combined with invariant 1, divergence spans at most 62 events from the fork point. An adversary holding less than the rotation-key preimage can only submit `Ixn` events, so the seal-advance cap limits them to at most 62 events before they need a seal-advancing primitive — which requires tier-2 or tier-3 capability per [`recovery.md` §Three-tier compromise model](recovery.md#three-tier-compromise-model).
3. **Bounded operations.** Recovery batch (`[Rec, ?Rot]` plus the surviving-branch context) is at most 64 events; the archival window is at most 62 events. Both fit in one `MINIMUM_PAGE_SIZE`-bounded page.
4. **Privileged divergence is terminal at merge.** Privileged events (`Rot` / `Ror` / `Fed` / `Dec`) that would create or join a divergent set are rejected at the merge layer per [§Privileged Divergence is Terminal](../../../../protocol-doctrine.md#privileged-divergence-is-terminal). Divergent sets contain only non-privileged events by construction.
5. **Locked-portion bound is unconditional.** Every event class is subject to the seal-cap: `event.parent.serial >= seal_serial`. Stale-authority revival is structurally impossible.

These invariants make synchronous archival, single-page discriminator walks, and atomic batched submissions feasible. The page-plus-resume-verify discriminator pattern relies on invariants 1–3. The proof matrices below rely on invariants 4–5.

Recovery-preimage rotation cadence (how often `Ror` should land to refresh the recovery commitment) is **operator guidance**, not a protocol-enforced invariant — see [`events.md` §Seal-advance cap](events.md#seal-advance-cap). Reconciliation correctness does not depend on a cap on `Rec` / `Ror` / `Dec` frequency.

## KEL chain states (proof states)

The state enumeration covers every per-node shape that can arise under the merge rules.

| State | Description |
|---|---|
| **Empty** | No events for this prefix on this node. |
| **Active** | Linear chain; the current tip extends cleanly via `previous`. |
| **Active, sealed** | Sub-state of Active where a submitter's view lands at-or-before `lastSealAdvancingEvent`. Any extension whose parent sits in the locked portion returns `ParentLocked`. |
| **Divergent** | Fork detected; two non-privileged events at the same serial. Privileged events extending `v_{d-1}` are rejected at merge per invariant 4. |
| **Divergent (sealed)** | Sub-state of Divergent where the seal has advanced past the divergence point — typically via a `Rec` / `Ror` / `Rot` / `Fed` that landed in a branch extension before resolution. The locked-portion bound rejects competing `Rec` against `v_{d-1}`. |
| **Recovered** | Clean chain after synchronous archival in the merge transaction. Equivalent to Active in subsequent rules — the discriminator-losing branch is removed from live storage. |
| **Decommissioned** | Exactly one `Dec`, ending a clean linear chain. Fully terminal: all submissions rejected by the seal-cap. |

## Matrix 1: Local submissions

What happens when a client submits events to the merge engine on a single node. Each cell names the outcome (per [`merge.md` §Merge outcomes](merge.md#merge-outcomes)) and the structural reason.

| Chain state | `Ixn` | `Rot` | `Ror` / `Fed` | `Rec` (with optional `Rot`) | `Dec` |
|---|---|---|---|---|---|
| **Empty** | Reject (no KEL) | Reject | Reject | Reject | Reject |
| **Active** | Append ✓ | Append ✓ (linear extension; `ParentLocked` if extending `v_{d-1}` while an event exists at `v_d` per invariant 4) | Append ✓ (linear extension; `ParentLocked` on divergent-set-creating parent shape) | Append ✓ (gossip-sync of recovered chains lands cleanly) | Append ✓ → Decommissioned (linear); `ParentLocked` on divergent-set-creating parent shape |
| **Active, sealed** (parent at-or-before `lastSealAdvancingEvent`) | `ParentLocked` (seal-cap) | `ParentLocked` (seal-cap) | `ParentLocked` (seal-cap) | `ParentLocked` (locked-portion bound condition 2b) | `ParentLocked` (seal-cap) |
| **Divergent** | `RecoverRequired` | `ParentLocked` (invariant 4 — privileged event extending `v_{d-1}`) | `ParentLocked` (invariant 4) | **Recovered** ✓ (discriminator runs; `RecoveryRecord` created) | `ParentLocked` (invariant 4) |
| **Divergent (sealed)** | `ParentLocked` | `ParentLocked` (seal-cap) | `ParentLocked` (seal-cap) | `ParentLocked` (locked-portion bound) | `ParentLocked` (seal-cap) |
| **Recovered** | Same as Active | Same as Active | Same as Active | Same as Active | Same as Active |
| **Decommissioned** | `ParentLocked` | `ParentLocked` | `ParentLocked` | `ParentLocked` | `ParentLocked` |

### Notes on cell routing

- **Privileged event extending `v_{d-1}` (any chain state).** A privileged event (`Rot`, `Ror`, `Fed`, or `Dec`) with `previous = v_{d-1}.said` whose landing would create or join a divergent set is rejected at the merge layer per invariant 4. The merge engine returns `ParentLocked`. When the rejected submission originated from another federation peer's locally-landed privileged event (a cross-node priv-vs-priv race), the chain does not structurally converge with that peer; federation-level convergence runs at the federation-witnessing layer — see [§Matrix 3: Race matrix](#matrix-3-race-matrix).
- **Active, sealed and Divergent (sealed).** The seal-cap (`parent_serial >= seal_serial`) rejects every submission whose parent sits in the locked portion. All extensions of `v_{seal-1}` / `v_{d-1}` return `ParentLocked`. The pre-seal verifiability guarantee (per [`recovery.md` §Pre-seal verifiability](recovery.md#pre-seal-verifiability)) is what makes this rejection sound: the chain segment at-or-below the seal stays structurally trustworthy regardless of subsequent above-seal disruption.
- **Decommissioned.** Fully terminal. All submissions are rejected with `ParentLocked` — the seal-cap treats a Decommissioned chain as sealed at its `Dec` (see [`merge.md` §Routing order](merge.md#2-seal-cap)). Federation races between concurrent competing privileged submissions resolve at the federation-witnessing layer (see [§Matrix 3](#matrix-3-race-matrix)).

### Batch submissions

The merge engine handles batches atomically:

- **`[events ..., Rec, ?Rot]`** — the surviving-branch context plus the recovery primitive. At most 64 events (bounded by the seal-advance cap). Processed as a single overlap or divergent submission; the discriminator archives the non-surviving events synchronously.
- **`[Rot, Ixn]` or `[Ror, Ixn]`** — auto-inserted by the builder when an `Ixn` would exceed the seal-advance cap interval. `Rot` is the cheaper choice; `Ror` is selected when the operator's recovery-preimage rotation cadence guidance calls for it.
- **`[Fcp, Fed]` plus federation Fcp and receipts** — the founder bootstrap atomic batch. The KEL events land alongside the federation IEL `Fcp` and the cross-attestation receipts in a single transaction. See [`../../../../federation/bootstrap.md`](../../../../federation/bootstrap.md) (subsequent sub-issue) for the bootstrap protocol.

## Matrix 2: Source → sink transfer (gossip sync)

When node A propagates a KEL to node B, the transfer reads from A's local chain state and submits to B's merge engine. Each cell describes the outcome at B for the named source / sink state pair.

"Active (surviving)" means B has the eventual surviving branch's non-divergent chain. "Active (alternate)" means B has the eventual non-surviving branch's non-divergent chain (submitted to that node before divergence was detected elsewhere). The protocol cannot distinguish the two from chain data alone — "surviving" is the branch the `Rec` (whoever holds the recovery key) ultimately extends.

| Source | Sink: Empty | Sink: Active (surviving) | Sink: Active (alternate) | Sink: Divergent | Sink: Decommissioned |
|---|---|---|---|---|---|
| **Active** | Full chain appended ✓ | Duplicates; no-op ✓ | Overlap → Divergence | `RecoverRequired` | `ParentLocked` |
| **Recovered** | Full clean chain ✓ | `Rec` + optional `Rot` append ✓ | Overlap → `Rec` in batch → Recovery ✓ | `RecoverRequired` (sink awaiting recovery) | `ParentLocked` |
| **Divergent (unrecovered)** | Reordered: longer chain plus fork event ✓ | Fork event creates overlap → Divergence | Fork event creates overlap → Divergence | Effective SAIDs match (`hash_effective_said("divergent:{prefix}")`) ✓ | `ParentLocked` |
| **Decommissioned** | Full chain plus `Dec` ✓ | `Dec` appends ✓ | Overlap; `Dec` in chain ✓ | `RecoverRequired` | Effective SAIDs match (`Dec.said`) ✓ |

### Notes on cell routing

- **Sink terminal state** (Decommissioned). Gossip ignored once the sink is terminal; the cell shows the error the sink returns. Federation-level convergence between a Decommissioned sink and an Active source (or any other state where the source has not retired) resolves at the federation-witnessing layer.
- **Send-side partitioning** (Source: Divergent). The source partitions the chain into sub-batches the sink will accept under its routing rules. The structural requirement is on the sender: receive-side ordering can sort what arrived, but cannot fix composition problems where the sink's merge handler will reject a particular batch composition. See [`merge.md` §Gossip send-side partitioning](merge.md#gossip-send-side-partitioning) and [§Transfer ordering](#transfer-ordering) below.
- **Divergent → Divergent sink.** Effective SAIDs match by construction (both compute the synthetic `hash_effective_said("divergent:{prefix}")`). Full anti-entropy may reconcile any missing branch events even when SAIDs already match.
- **Cross-node priv-vs-priv races.** When the source and sink hold different competing privileged events at the same serial, the seal-cap rejects each peer's gossip-arriving event. Federation-level convergence resolves at the federation-witnessing layer via divergent witness receipts — see [§Matrix 3](#matrix-3-race-matrix).

### Transfer ordering

For divergent source chains, the sender reorders events to ensure the chain reconstructs the same way at the sink. With synchronous archival, a recovered source chain is always a clean linear chain — the archived-branch events are removed in the merge transaction. In normal operation, only unrecovered divergent cases reach the partitioning path.

- **Divergent with `Rec`** — rejected with error. This state cannot exist through normal merge paths: synchronous archival means a `Rec` immediately archives the other-branch events, leaving a clean chain. A divergent chain with `Rec` in the live tables indicates possible DB tampering. The partitioner refuses to propagate it.
- **Unrecovered (`Ixn`-`Ixn` divergent set)** — longer chain first as non-divergent appends; only the fork event from the shorter chain is sent. Receiver routes the fork event through the overlap path → Divergent state.

### Effective-SAID convergence

All nodes must eventually agree on the effective SAID for each prefix. The effective SAID is the chain's canonical wire-format identifier; nodes exchange it during anti-entropy.

| State | Effective SAID computation | Converges? |
|---|---|---|
| **Active** | Tip event SAID | ✓ (identical chains after gossip) |
| **Divergent** | `hash_effective_said("divergent:{prefix}")` — deterministic synthetic | ✓ (same value regardless of which fork events each node holds; avoids wasted anti-entropy sync) |
| **Recovered** | Tip event SAID | ✓ (identical clean chains after gossip) |
| **Decommissioned** | `Dec` event SAID | ✓ (identical chains across all nodes where `Dec` landed without a competing privileged submission). When a competing privileged event extending `Dec`'s parent has been submitted to a different node, the federation does NOT structurally converge — each node's seal-cap rejects the other's submission; convergence runs at the federation-witnessing layer (see [§Matrix 3](#matrix-3-race-matrix)). |
| **Federation-irreconcilable** | `hash_effective_said("irreconcilable:{prefix}")` — deterministic synthetic, federation-witnessing-layer-sourced | ✓ (deterministic; same value across all nodes when the federation surfaces the prefix as in-dispute via divergent witness receipts; returned by chain-query responses regardless of per-node tip state). |

The synthetics depend only on `(state, prefix)` — no chain history, no fork point, no serial. Any node can compute either synthetic without holding chain state. See [§Effective-SAID synthetic comparison](../../../../protocol-doctrine.md#effective-said-synthetic-comparison) for the cross-primitive framing.

## Matrix 3: Race matrix

Concurrent priv-vs-priv races between federation peers — both submitting privileged events extending the same parent `v_{d-1}` to different nodes — uniformly resolve via the same structural shape: each event lands as a clean linear-chain extension on its submitting node and advances the local seal; gossip then delivers each event to the other node, where the seal-cap rejects it (`parent_serial < seal_serial`). The chain does not structurally converge at the protocol layer; federation-level convergence runs at the federation-witnessing layer via divergent witness receipts.

The race participants — any pairing across `{Rec, Ror, Rot, Fed, Dec}` — produce identical structural outcomes per-node:

- Each node keeps its locally-landed first-receive.
- The gossip-arriving competing event is rejected by the seal-cap with `ParentLocked`. On the Dec'd side the rejection is identical — a Decommissioned chain is sealed at its `Dec`, so the seal-cap rejects per [§Forks are Seal-Bounded](../../../../protocol-doctrine.md#forks-are-seal-bounded).
- Federation-level convergence runs at the federation-witnessing layer.

### Worked race: `Dec` versus `Ror` / `Dec` at `v_d`

Two parties submit concurrent privileged events extending `v_{d-1}` at the same serial `d` to different nodes: party 1 submits `Dec` (clean retirement); party 2 submits another privileged event (e.g., `Ror` or `Dec`) extending the same parent.

```
Pre-state (linear at v_{d-1}):

  Both nodes:  ... → v_{d-1}    (tip)

Concurrent submissions:

  Party 1 → Node A:    dec.previous     = v_{d-1}.said, dec.serial     = d
  Party 2 → Node B:    ror_alt.previous = v_{d-1}.said, ror_alt.serial = d

Each event lands as a linear-chain extension on its submitting node.

Gossip propagates:

  Node A (Decommissioned at v_d via dec) receives ror_alt:
    ror_alt.parent_serial = d-1 < seal_serial = d
    → rejected by seal-cap with ParentLocked (chain sealed at its dec).
    Node A state unchanged: Decommissioned.

  Node B (Active at v_d via ror_alt) receives dec:
    dec.parent_serial = d-1 < seal_serial = d
    → rejected by seal-cap with ParentLocked.
    Node B state unchanged: Active with ror_alt as tip.

  Effective SAIDs:
    effective_said(A) = dec.said
    effective_said(B) = ror_alt.said
    A ≠ B → federation does not converge at the protocol layer.
```

Federation-level convergence in this scenario is provided by **divergent witness receipts** at the federation-witnessing layer. Federation members witness every structurally-valid event they observe (always-witness); adjacent receipts at the same chain position carrying different `witnessedSaid` values are the structural evidence that the federation cannot agree at that position. The prefix surfaces as federation-irreconcilable at-and-beyond the divergent serial. See [§Limit of the doctrine — concurrent privileged event races](../../../../protocol-doctrine.md#concurrent-privileged-event-races) and [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md).

The seal-cap stays unconditional. Relaxing it to admit competing events at a sealed serial would re-open the stale-authority killswitch surface that the locked-portion bound was designed to close.

### Race classes (tier-2 versus tier-3)

The race surface partitions by adversary tier (per [`recovery.md` §Three-tier compromise model](recovery.md#three-tier-compromise-model)):

- **Tier-2 path.** An adversary holding the rotation-key preimage can force federation-level non-convergence by racing `Rot_adversary` against an honest concurrent `Rot_operator` or `Ror_operator` on different federation nodes. The forging bar is tier-2 (one preimage), strictly easier than the tier-3 bar required to forge `Ror` / `Rec` / `Fed` / `Dec`.
- **Tier-3 path.** An adversary holding both preimages can force non-convergence by racing any recovery-revealing event (`Ror` / `Rec` / `Fed` / `Dec`) against operator submissions. Once an adversary's tier-3 event has landed on any federation node, no in-band protocol recourse exists.

Both paths produce identical per-node structural outcomes (matrix above). See [§Rotation-tier adversary federation-non-convergence path](../../../../protocol-doctrine.md#rotation-tier-adversary-federation-non-convergence-path) for the structural framing.

## Archival bounds

Archival happens synchronously within the merge transaction that accepts the `Rec` (or `[Rec, Rot]`) batch. No background task, no async processing.

| Metric | Bound | Source |
|---|---|---|
| Non-surviving events to archive | ≤ 62 | Seal-advance cap limits fork distance (invariant 1). |
| Archival scope | Single transaction | Synchronous in merge; bounded by `MINIMUM_PAGE_SIZE` (invariant 3). |
| Surviving-branch events never archived | ✓ | Surviving branch identified by walkback from `Rec.previous` per the discriminator (see [`merge.md` §Discriminator algorithm](merge.md#discriminator-algorithm)). |

## Edge cases

### 1. Rec landing as normal append (no divergence)

A submitter with the recovery key submits `Rec` to a non-divergent chain (normal append, no divergence). This reveals the recovery key. Any future divergence at or after this `Rec` is unrecoverable per-node: the recovery key is spent, non-privileged events that form divergent sets cannot be archived, and privileged events that would create or join the divergent set are rejected at merge per invariant 4. Operator recourse is abandon-and-reincept under a new prefix.

```
Pre-state (linear chain through v_N):
  v_0 → v_1 → ... → v_N   (tip at v_N; seal at last recovery-revealing event ≤ N)

A recovery-key holder submits rec with previous = v_N.said (dual-sig satisfied):
  v_0 → ... → v_N → rec_x  (v_{N+1}; seal advances to N+1)

Effect: chain stays linear; seal advances to N+1; recovery key now spent for this chain. A privileged event extending v_N.said arriving via gossip is rejected at merge per invariant 4 — its acceptance would create a divergent set containing a privileged event. Cross-node priv-vs-priv races resolve at the federation-witnessing layer. Competing Rec against v_N is rejected by the locked-portion bound; non-privileged extensions submitted at serial ≤ N+1 are rejected with ParentLocked (seal-cap).
```

### 2. Multiple competing non-privileged events injected across nodes

Different `Ixn` events at the same serial are submitted to different nodes (federation race or threshold compromise — chain-indistinguishable). When gossip syncs, divergence is created. Only one extra event is written per overlap (the fork event). Recovery resolves it. All nodes converge after recovery propagates via gossip.

```
Pre-state (linear at v_{d-1}, replicated to nodes A and B):

  Node A:  v_0 → ... → v_{d-1}    (tip)
  Node B:  v_0 → ... → v_{d-1}    (tip)

Different events submitted at v_d on each node:

  Node A receives ixn_a:  v_0 → ... → v_{d-1} → ixn_a @ v_d
  Node B receives ixn_b:  v_0 → ... → v_{d-1} → ixn_b @ v_d

Gossip propagates ixn_a → B, ixn_b → A. Each node's merge engine observes overlap at v_d and writes the second event as the fork event (one extra event per overlap; dedup-rejection on subsequent submissions at the same serial):

  Both nodes:  v_0 → ... → v_{d-1} ─┬─ ixn_a @ v_d   (Divergent)
                                    └─ ixn_b @ v_d

A recovery-key holder submits Rec to any single node → discriminator archives the non-extended branch → recovery propagates via gossip → all nodes converge on the post-Rec linear state.
```

### 3. Local events archived by a competing `Rec`

If one recovery-key holder submits `Rec` archiving another party's events synchronously, that other party's local store detects missing events when it next attempts to flush. Detection works by loading the last page of locally-held events, then walking backward checking each SAID against the server until finding the boundary — everything after that boundary was archived. The party then resubmits those missing events (plus any continuation work) as an atomic batch.

```
Pre-state (divergent at v_d; local store holds branch A):

  Server:  v_0 → ... → v_{d-1} ─┬─ branch_A @ v_d → branch_A' @ v_{d+1}
                                └─ branch_B @ v_d

  Local:   v_0 → ... → v_{d-1} → branch_A → branch_A'   (local view)

A second recovery-key holder submits Rec extending branch_B (branch-tip-extending shape):

  Discriminator archives branch_A, branch_A'; rec_B lands at v_{d+1}.

  Server (post-archival):  v_0 → ... → v_{d-1} → branch_B → rec_B

Local party detects via existence-check on the server that branch_A, branch_A' no longer exist server-side. They bundle [branch_A, branch_A', Dec] as an atomic batch and submit. The missing events are verified server-side and re-established under the batch's atomic transaction. Post-batch, Dec with previous = branch_A.said (v_d) would land at v_{d+1} as a sibling of branch_A' — creating a divergent set containing a privileged event. The merge layer rejects the Dec per invariant 4; the chain stays at its prior server-side state (tip = rec_B at v_{d+1}). Recourse is to re-fetch the server state and submit Dec extending the current tip cleanly, or to accept the server-side state without decommissioning.
```

### 4. Post-recovery events synced to a node holding the archived branch

After recovery on node A, new events (e.g., `Ixn`) are appended. When synced to node B (which still has the now-archived branch), the overlap handler creates a `RecoveryRecord` and archives the non-surviving events synchronously in the merge transaction.

```
Pre-sync state (post-recovery on A; archived branch still on B):

  Node A:  v_0 → ... → v_{d-1} → branch_A @ v_d → rec → ixn_new
           (clean linear chain after Rec archived branch_B)

  Node B:  v_0 → ... → v_{d-1} → branch_B @ v_d
           (still has the alternate branch; Rec hasn't propagated)

Gossip propagates Node A's chain (including Rec) to Node B. Node B's merge engine observes overlap at v_d (its branch_B vs incoming branch_A), sees Rec in the batch, runs the discriminator (Rec walkback identifies branch_A as the surviving branch), and archives branch_B synchronously.

  Node B (post-sync):  v_0 → ... → v_{d-1} → branch_A → rec → ixn_new
                       (matches Node A; branch_B in the archive store)

All nodes converge on the same effective SAID (tip event SAID).
```

### 5. Concurrent privileged race at `v_d` — federation-witnessing-layer convergence

See [§Matrix 3](#matrix-3-race-matrix). Per-node, each chain stays linear with its own first-receive as tip. Federation-level convergence runs at the federation-witnessing layer via divergent witness receipts. The seal-cap stays unconditional.

## Cross-references

- [`log.md`](log.md) — chain primitive: states, locked-portion bound, page model.
- [`events.md`](events.md) — per-kind reference: kinds, fields, three-tier capability model, seal-advance cap.
- [`merge.md`](merge.md) — merge engine routing being proved sound.
- [`recovery.md`](recovery.md) — recovery doctrine: Rec parent shapes, three-tier compromise model, pre-seal verifiability.
- [`verification.md`](verification.md) — verifier walk.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#federation-convergence) — federation convergence (cross-primitive doctrine).
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#privileged-divergence-is-terminal) — privileged-divergence-is-terminal rule.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#forks-are-seal-bounded) — seal-cap and locked-portion bound.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#concurrent-privileged-event-races) — limit of the doctrine; concurrent privileged event races.
- [`../../../../protocol-doctrine.md`](../../../../protocol-doctrine.md#effective-said-synthetic-comparison) — effective-SAID synthetic comparison.
- [`../../../../federation/witnessing.md`](../../../../federation/witnessing.md) — federation witnessing (subsequent sub-issue): always-witness, threshold-two-events, divergent witness receipts.
