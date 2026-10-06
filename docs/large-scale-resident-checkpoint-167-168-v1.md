# Resident PhaseI cells167–168: execution closed, audit not complete

2026-10-07, Asia/Hong_Kong. Last two original scheduled cells, attempt1 each:
LongBench2 `1458aa227ea0348b`. Both completed, terminal format valid, original
evaluator score0. No retry/replacement/tuning. Execution APP004, resident diverse
pool, scheduler, tools, prompts, budgets and evaluators remain unchanged.

| Metric |167 DeepSeek / Slow / B1|168 Qwen / Fast / A|
| --- | --- | --- |
| Manager / specialist / Verifier turns |8 /0 /8|11 /8 /11|
| Physical calls / actual model inference |12 /1|16 /1|
| Context preflight rejections |2|4|
| Operators prepared |9BM25,3model|9BM25,5model,2aggregate|
| Created specialists / peak |0 /0|1 /1|
| E2E including fixed initial setup |114.405513s|143.994668s|
| Fixed initial bytes |2,119,778|2,119,778|
| Fixed initial transfer work |5.986054s|0.390685s|
| Complete Agent movement bytes / work |0 /0s|0 /0s|
| Tool work |5.000276s|2.154200s|
| Model backend service work |10.768445s|15.099141s|
| Model input / output tokens |3,803 /2|5,335 /2|
| Manager / specialist / Verifier work |63.612795s /0s /26.478222s|52.051331s /29.930932s /41.342740s|
| API calls / known list-price USD |16 /0.158687156353|30 /0.317700059794|
| Nodes / information-flow edges / snapshots |12 /9 /37|16 /15 /49|

Both actual inferences select A4/Qwen3-VL4B. Context rejections are not inference.
167 also has four phase-restricted observations.168 has one phase-restricted and
one semantic-validation observation. Actual specialist result/handoff is retained;
8specialist turns alone is not proof of failure. Work sums are non-additive and
USD estimates are not invoices. Complete zero Agent movement is receipt-backed,
not a missing-value default. Fixed materialization is reported separately.

## Exact interface visibility and integrity

167's eight actual root API requests each contain exactly one fresh anonymous
profile equal to the corresponding trace profile. All eight actual Verifier
requests contain no profile. This proves visibility, not optimization adoption.
168 records11spent-ledger predecisions, no optional query/quote/comparison;
ledger presence is not proof that it causally changed reasoning.

Both original admissions are independently reconstructed and match immutable
settlements with valid disposition and no implementation/operational problems.
Four initially empty stores, actual SDK recipient/privacy contexts, verified
Worker exits, tc cleanup and resident identity checks pass. Runner identities
match166→167→168before/after states; no reload or guessed warm-up subtraction.
Actual child execution-only imports/revision0ff0e9b were verified live for both.
No benchmark/private/API body is exported by these metadata audits.

Remote append-only proof paths are under
`/home/super/xiaoming/large-scale-cost-guidance-resident-v1/analysis`:

| Proof | SHA256 |
| --- | --- |
|167live start|`a96e537f05fc3842027eb859a1223a8fcc355e2ec003d2aa807ad8730be1625f`|
|167settlement|`d75629056aed3a97eb2bb8fb008f3ae28c1aca7e45c4c461ccf3b4fd37bedec3`|
|167actual profile delivery|`8a3cef876e267b77c73e4fbb5ebfcf6618358e45952afc4c4086e60e0393d3d9`|
|168live start|`405b79eb29afab804eb7146cfcf272f048e5c493fa22402a7ec2a0094244ba6e`|
|168settlement|`890988da2355835773b9dc452b4ec6803d1a15c53caa6607dc8feb4b7f183128`|

Queue025 PID1394661 exited normally, returncode0 at17:35:51.654824Z.
At17:36:26Z both queue and final atomic action are independently inactive;
journal411records,14additional settlements after snapshot051's154 =168nominal
cells. A fresh full source-bound projection and owner-local private evidence
audit are now running, after inactivity guards. Old snapshot052/old42/attempts
are not overwritten or pooled. Wrong-answer semantic causes await full review.

**Execution completion is not comprehensive audit completion or goal completion.**
No quality aggregation, pruning, PhaseII authorization/launch or method winner is
claimed here. All168semantic/failure/recipient/adoption reviews, actual held-out
PhaseII and finalQ1–Q10remain required.
