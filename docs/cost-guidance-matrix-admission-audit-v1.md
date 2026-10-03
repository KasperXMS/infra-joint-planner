# Cost-guidance matrix admission audit v1

2026-10-04. Offline, read-only audit tooling; final16-cell audit not executed yet.
The frozen queue remains live. This document records verification scope, not
an assertion that all pending experiments or the overall exploration are done.

`scripts/audit_cost_guidance_matrix_v1.py` refuses to run while any owned parent
or child controller handle is live. It never launches a process, restarts a cell,
changes shaping, fetches an artifact body or invokes a model/evaluator. CLI use
is restricted to4090-owned experimental roots; output is append-only metadata.

After queue exit it will inspect **every** scheduled task/condition, not only
correct/cheap trajectories:

- Exact original protocol-file hash, frozen Agent/method source and harness-file
  hashes; per-cell task bundle, source manifest, capability and placement parity.
- Equal semantic harness and EnvironmentSpec sources; unchanged models, budgets,
  scheduler,1200s timeout, no retry/replacement and specified Fast/Slow settings.
- Frozen numeric history file/manifest hashes; no fitting to new evaluator results.
- Four initially empty stores per cell, no cross-cell store-root reuse and exact
  owned namespace; retained cell-config hashes.
- Original operational gate, exact retained result/trace hashes for independent
  adjudications, method input/isolation/accounting gate, Worker shutdown and tc
  restoration receipts.
- Whole trace run identity, unique event IDs, serialized parent chain, timestamps,
  task start and run end; quote visibility, actual inference and artifact paths.

Quality0, recovered semantic errors or legitimate completion failure do not
become exclusion criteria. A completed run must still have a valid terminal
output and evaluator record. Missing evidence, changed hashes or a confounder is
reported, not silently admitted or automatically rerun. Artifact-persistence/
observer checks are covered by the original operational gate; raw source bodies
and private answers are not exported in the new metadata report.

Protocol **file** SHA256:
`f18bfff202a0314c29bdd673158ddcd875a08b084118df6a2b9df109bf1eec66`.
The separate canonical protocol **content** digest in that file is
`dcf01ea2927de3e5a547ab3d7f058160cbbe20f9ed26c700797d06accc09c7ea`.
These are different hash domains, not a protocol drift.

Five synthetic tests check exact adjudication hashes without overwriting the
original gate, feedback/network/history freeze parity, incomplete-cell refusal,
quality-independent admission and whole-chain reconstruction failures. Full555
pytest passed; Ruff passed; strict project Pyright0 errors/0 warnings and explicit
strict audit-script check passed; git diff check passed. Tests do not establish
the not-yet-run final audit, method benefit or novelty.

## Thirteenth completed cell:Video Fast Ledger

Video848-1/Fast/Ledger completes with original score0.0 and valid terminal format,
operational gates passing. E2E349.878s; initial placement160083738 bytes/13.894s;
action transfer986799 bytes/1.308s; tool work75.571s; physical model service227.249s;
Manager work23.053s; Verifier work8.620s. Work sums are non-additive to E2E.

Actual Manager trajectory:sample29 frames(every70s),three contact sheets with
10/10/9 inputs,one artifact-backed A28 inference consuming all three sheets.
Three Manager turns,zero specialists,one actual inference,7631 model input tokens,
no typed execution failures. Original video duration2037.781s. This interval/count
spans nearly the video timeline; do not call it uniform endpoint-preserving
sampling or assume a prefix-only failure. Contact sheets are real derived JPEG
representations; original video/task/evaluator remain frozen.

Fast Quote is still running at this checkpoint. Its real trace already shows
sample32 frames(every60s),followed by successive8-frame model-analysis proposals
and commits. Each quote exposes empirical model p50/p90 of274.468/291.314s with
support12; these are descriptive profiles, not bounds or quality guarantees.
The fourth model action is live. Do not label its whole elapsed time a single
timeout or count unfinished actions as successful inferences. Final quality and
cost comparison require terminal execution/evaluation and remaining Slow cells.
