# Resident checkpoint120 — valid completion, limited interface use

Source-aware snapshot033 at2026-10-06T05:51:07Z binds120/168effective cells,
124attempts/123settled+pending121, with three preserved confounded originals.
Closed42predecessor results remain unpooled. No pruning or PhaseIIlaunch.
All five newly audited cells use unchanged execution003canonical SHA
`09f0a5e978623c145b1c075ecb575ed6ea54eec20110c0b7059e1db2b5b905e6`.

| Cell /task /Planner /network /method | Completion /format /score | E2E s | Manager /specialist /Verifier | Prepared tool /model; returned inference | Fixed initial bytes /s | Complete action bytes /s | Complete tool work s | Returned model service s | Physical input /output tokens | API list USD |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | --- | ---: |
|116 /602-2 /P1 /Fast /A|yes /valid /1|102.494|3 /0 /3|1 /1;1|213,739,837 /18.615|0 /0|15.760|31.316|5,612 /2|0.111752729|
|117 /131-3 /P1 /Fast /B|yes /valid /1|75.920|4 /0 /4|1 /1;1|7,037,220 /0.689|0 /0|1.557|31.371|5,608 /2|0.080596153|
|118 /131-3 /P2 /Slow /C|yes /valid /1|115.247|12 /5 /4|4 /2;2|7,037,220 /19.710|unknown /unknown|unknown|11.428|1,413 /44|0.182817498|
|119 /131-3 /P1 /Slow /D|yes /valid /1|131.701|13 /0 /4|3 /1;1|7,037,220 /19.719|unknown /unknown|unknown|30.822|5,514 /2|0.116921130|
|120 /131-3 /P2 /Fast /E|yes /valid /1|106.699|5 /0 /5|1 /2;1|7,037,220 /0.654|0 /0|1.639|44.288|7,801 /2|0.148384957|

P1=DeepSeekV4Pro, P2=Qwen3.8-Max; Verifier remains fixed Qwen3.8-Max.
USD uses frozen regional list prices, not invoices. Work sums are not an E2E
decomposition. Original result operator latency includes model-action execution;
the table separates pure tool work and backend service without double-counting.
All returned inference finish reasons are`stop`.

The failed oversized`read_artifact` on118/119 makes complete action transfer and
tool work unknown. Successful transfer receipt subtotal is0; successful tool-work
subtotals are1.231s/0.435s respectively. Do not promote those lower bounds to
complete totals or claim measured zero movement on those two cells.

## Actual trajectories and adoption

-116: sample_frames -> artifact-backed visual inference; one phase-restricted
  contact-sheet request was rejected without additional physical execution.
-117: recovered from argument/phase errors, then sampled15frames and passed five
  explicit frame artifacts to the terminal visual model. B's optional estimates
  were exposed in all four actual Manager requests; query attempts/cards were0.
  Observed eligible ready root decisions=2. This is non-adoption, not query benefit.
-118: oversized read rejected; extract_clip -> specialist sample_frames ->
  contact_sheet -> materialized visual note -> root terminal model. Four quotes,
  three consumed, one pending; four quote argument rejects. Two actual inferences
  consumed one artifact each. Two owners but no actual parallel overlap.
-119: oversized read rejected; extract_clip -> sample_frames -> visual model
  consuming five frame artifacts. Five quotes, four consumed, one pending; four
  quote argument/phase rejects. D made **no candidate comparison calls**, so this
  is not evidence that multi-candidate optimization was exercised.
-120: sample15frames ->15-image model action rejected during selection for context
  ->future seven-image action succeeds. The first model proposal did not infer;
  the second did. E rules were visible in five root inputs; internal rule use is
  unobservable. Correct recovery alone does not establish E caused it or preserved
  all semantic evidence; the eventual original evaluator score is1.

All actual physical selections were local to A4/residentVL4B. This is scheduler
realization, not evidence that all five resident models were invoked. Each returned
model actually consumed artifacts; no prompt-only inference is inferred here.
Finite tool/schema errors and context recovery are ordinary valid trajectories,
not reasons to tune prompts or repeat a cell.

| Cell | Nodes /information edges /snapshots | Logical owners | Max actual concurrency /overlap | Actual API contexts scanned |
| --- | --- | ---: | --- | ---: |
|116|2 /5 /7|1|1 /0s|6|
|117|2 /5 /7|1|1 /0s|8|
|118|6 /18 /19|2|1 /0s|21|
|119|4 /6 /13|1|1 /0s|17|
|120|3 /22 /10|1|1 /0s|10|

All four Workers exited after each cell; resident validation passed and startup
subtraction=false. Fresh stores are not cold inference cache. No methods are
pruned and no aggregate correctness/causal optimization claim is made before
all168private semantic/failure/recipient/adoption audits.

## Immutable remote proof

Root:`/home/super/xiaoming/large-scale-cost-guidance-resident-v1`.

-Snapshot033SHA:`0fb9a77072fe59f622e8a8e9b96a98054c4049b1a60727a4be3eadb7128ba91f`.
-Bound journal SHA:`e810ad9c0ee146156740a336096dfd368dfcb11da6980de0bc314e26a77d0202`.
-`analysis/resident-cells116-120-completed-002.json` SHA:
  `107ebf59a485d7a85678301ceec13e0ca14cb4f1eac4fd27ba5da8be5ead049b`.

Projection002binds original result/trace/admission/Worker-shutdown files. An
audit-only001query looked for shutdown in`private/` instead of the attempt root;
its false absence flags are retained but superseded, not experimental failures.
002uses the real file, proves all exits and supplies source-aware cost receipts.
No original evidence or runtime was changed and no rerun follows from that query.

Queue011controller4047590was verified live. At05:52:26Z, cell121settled valid;
its outcome is not yet included in this source-bound checkpoint. The queue keeps
only never-started scheduled cells; exact subsequent coverage requires a fresh
source-aware snapshot, not inference from a console or stale process handle.
