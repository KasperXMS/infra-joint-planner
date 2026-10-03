# Cost-guidance exploration v1: final 16-cell audit

2026-10-04. Execution freeze47fbe3b14196ea2b90c84597b75fa27f148b0b74;
analysis tools667c1ff. This is bounded exploratory evidence, not a paper evaluation
or a successful-method claim.16 designated runs/16 global reservations; no retry,
replacement or substantive rerun. The queue has recorded all_primary_cells_finished;
owned parent1365512 and final child1618059 no longer exist. No further cells launched.

## Exact setting and evidence

Remote root:`/home/super/xiaoming/cost-guidance-exploration-v1-47fbe3b`.
Each cell is under `evidence/<task>-<fast|slow>-<ledger|quote>`; its run ID is
`cost-guidance-exploration-v1-47fbe3b-<cell>`. Source bodies, private evaluation,
initial materialization, stored artifacts and full trace/results remain remotely
owned. Development receives only bounded metadata/hashes; no dataset distribution
through the PC. A small rendered research-paper page is unrelated to benchmark data.

Persistent OpenAI Agents SDK Manager, bounded Blind specialists-as-tools and the
existing Blind Verifier; finite operators, ActionGateway and B0 locality scheduler.
Cloud Manager/Verifier qwen3.8-max; physical Qwen35 27.3B Q4_K_M artifact under the
existing qwen3.8-27b alias,32K context/2048 reserved output,1200s service timeout.
20 Manager turns/64 physical calls/20 Verifier calls;8 specialist turns/4 created/
2 active. No prompt, benchmark/evaluator/representation, scheduler or model-pool tune.

4090 controller and Jetson A4/A5/A28; four fresh processes/stores per run. All22
successful physical model inferences select A28. GPU availability is not evidence
of an observed GPU/deployment preference reversal. Tools execute on A4/A5/A28.

Fast100Mbps/configured delay5ms; Slow3Mbps/configured delay50ms. Reused tc:
Jetson HTB without netem,4090 HTB plus netem; not a symmetric measured RTT claim.
Task order MH,Academic,Financial,Video; per-task Fast A,Fast C,Slow A,Slow C.
Fixed order,n=1,uncontrolled Ollama cache/load history; fresh stores are not cold models.

A is spent-only **Ledger**, not original Blind. C is Ledger plus anonymous,
parameter-specific **Quote-before-Commit**, no raw H/device identity. Both retain
BLIND profile visibility; costs only reach Manager, not specialists/Verifier.
C proposes/quotes/commits in additional cloud turns within the same20-turn horizon;
different semantic opportunity/control overhead is a disclosed protocol difference.

History freeze:`/home/super/xiaoming/cost-guidance-history-v0-00ff980/freeze-001`;
33 eligible runs,62 model/255 operator/245 transfer samples; minimum support3.
Descriptive p50/p90,not bounds; unsupported buckets/queue/cache/future outputs unknown.
History does not learn from this matrix's quality or costs during execution.

Protocol-file SHA:`f18bfff202a0314c29bdd673158ddcd875a08b084118df6a2b9df109bf1eec66`.
Canonical protocol-content SHA:`dcf01ea2927de3e5a547ab3d7f058160cbbe20f9ed26c700797d06accc09c7ea`.
Static capability SHA:`8d46d9b941a08380a00fdab1e7c151c25affd589ec4444864f3c5c925a2089a4`.
Final `matrix-admission-audit-001.json` SHA:
`32a12869dae88fd3025fc3beb2421305bcb089a6e11b9137512f27edfdf76a8b`.
All16 admissions checked,64 distinct empty store roots,zero findings: task/model/
harness/operator/history parity; actual recipient privacy; complete parent-linked
trace; quote visibility; retained shutdown and exact qdisc restoration receipts.
The first Fast Ledger gate stop is independently adjudicated recovered Agent schema
misuse, not a harness repair. Its original gate/trace/result and adjudication remain
unchanged. No wrong-answer sample is excluded. See [matrix audit](cost-guidance-matrix-admission-audit-v1.md).

## All runs

All rows:execution completed,terminal format valid,original evaluator invoked.
A=Ledger,C=Quote. Score is per-task evaluator quality, not execution validity.
Bytes/time below are **action transfers**, excluding initial placement; E2E includes
initial placement. Model/tool/control sums are work counters,not additive wall time.

| Task | H | Method | Score | E2E s | Action bytes | Transfer s | Model service s | Inferences | Manager/specialist turns | Action nodes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | --- | ---: |
| MultiHop multi-source |Fast|A|1|250.012|57445|0.636|157.319|1|9/8|16|
| MultiHop multi-source |Fast|C|0|203.999|27774|0.066|127.532|1|18/0|7|
| MultiHop multi-source |Slow|A|1|201.631|5204596|14.941|136.496|1|4/0|4|
| MultiHop multi-source |Slow|C|0|228.329|27774|0.180|125.679|1|19/0|7|
| LongBench Academic |Fast|A|1|114.371|233303|0.166|72.809|1|7/0|5|
| LongBench Academic |Fast|C|1|185.066|233323|0.454|71.302|1|18/0|5|
| LongBench Academic |Slow|A|1|162.897|28303|0.667|60.336|1|12/8|16|
| LongBench Academic |Slow|C|1|61.482|0|0|6.391|1|14/0|3|
| LongBench Financial |Fast|A|0|243.291|495883|2.168|121.075|1|14/0|20|
| LongBench Financial |Fast|C|0|97.570|470494|0.281|8.370|1|16/0|2|
| LongBench Financial |Slow|A|0|191.421|19116|0.909|111.225|1|8/0|15|
| LongBench Financial |Slow|C|0|83.587|470494|1.632|15.334|1|10/0|2|
| Video-MME848-1 |Fast|A|0|349.878|986799|1.308|227.249|1|3/0|5|
| Video-MME848-1 |Fast|C|0|1467.875|2646929|1.813|1116.263|7|18/8|15|
| Video-MME848-1 |Slow|A|0|785.337|682425|3.048|189.335|1|6/0|3|
| Video-MME848-1 |Slow|C|0|556.145|231020|0.825|30.335|1|7/0|3|

Initial bytes:MH7696522;Academic514789;Financial1081150;Video160083738.
Video initial transfer:Fast A/C13.894/13.905s;Slow A/C446.958/446.972s.
This fixed initial component is not a saving the Manager can reverse after placement.

## Workflow/action-level effects and failure classification

| Task/H | Ledger actual path | Quote actual path | Primary result/failure |
| --- | --- | --- | --- |
| MH/Fast | Cross-shard retrieve,context refusals,aggregate/retrieve/read recovery,specialist,terminal evidence model | Six BM25 outputs;infeasible six-input model quote left pending;terminal takes only shard-1 pair | C composition/evidence selection,then wrong synthesis;A recovers |
| MH/Slow | Full aggregate,two BM25,terminal evidence model | Same six-BM25/two-input structure as Fast C | Same C evidence omission;no H-dependent structural change |
| Academic/Fast | Aggregate,BM25,model context refusal,smaller BM25,model | Same prepared operator sequence;one known-infeasible quote committed/refused | Both correct;C overhead,not useful structural adaptation |
| Academic/Slow | Iterative retrieval/context recovery,aggregate,specialist,model with two artifacts | Two BM25;two infeasible model proposals discarded;prompt-only model | C scored correct but grounding/reduction benefit unproven |
| Financial/Fast | Aggregate,three rounds of four retrievals/reaggregation/context recovery,model | Aggregate;four infeasible quotes discarded;prompt-only model | A reasoning/task failure after evidence processing;C evidence abandonment/synthesis |
| Financial/Slow | Three groups of four BM25,two context refusals,model | Aggregate;two infeasible quotes left pending;prompt-only model | Both wrong;C moves more bytes despite lower E2E |
| Video/Fast |29 frames every70s,three contact sheets,one model |32 every60s,four8-image analyses;Blind specialist resampling/sheets/model/clip;read;two more models | Both wrong;C over-expansion,7 inferences,4.20x E2E,2.68x bytes |
| Video/Slow |31 every64s;31-image refusal;model with eight spaced frames |16 every64s,one320x180-cell contact sheet,one model | Both wrong;C cheaper representation/prefix-limited coverage,not demonstrated semantic preservation |

Typed context/phase/schema refusals are observed recoverable events,not inference
successes or run retries. All runs finish before hard budgets; no cloud billing,
OOM,900/1200s backend timeout or store-collision terminal failure is identified here.
No independent semantic critic or hidden finalizer is added. Financial A consumes
retrieved evidence yet fails; no proof it had all task-required evidence is inferred
from artifact existence. Video wrong-answer causes cannot be uniquely identified
from sampling metadata alone. Final choices are not repaired post hoc.

### Private MultiHop evidence audit

After all owned queue handles exit, original supports are mapped to corpus document
IDs; each artifact body is checked/scanned on its owning node,with bytes/SHA and
namespace confinement. No annotation enters Agent/cost inputs. Both support documents
and literal fact cues appear in the shard-3 retrieval outputs of both C runs.
Neither support document appears in either of their terminal shard-1 inputs; neither
literal fact cue appears in the terminal prompt. Both A terminal inputs retain both
documents/fact cues and score1. This localizes C's failure to selecting/composing
already retrieved evidence. It does not make a correctness oracle or prove what an
unexecuted six-input model would answer/fit. Literal absence alone is not semantic absence.

Private `support-coverage-audit-001.json` SHA,Fast A/C then Slow A/C:

- `2b9237013031fdb3993765913b08ea3b80401f9c4a6ef3978d6fba8be9703274`
- `fd39c2e8dcb6759a417a6547d8f2a7a35f3a74e6b68b2745f7d8fa181ec0a47b`
- `3b0e48327b17b5860c226764521faa8b4d53d990d0aa64bed793a10297ad8d15`
- `537782f74046a2abb5d5863ce5d145e6d4cb31dc67c329eef61ce5a1833af491`

### Quoted feedback, real execution and uncertainty

49 cards are **exactly** present in actual post-filter Manager SDK inputs before
commit/discard,or while pending.37 consumed,8 discarded,4 pending;36 executions
succeed and one known-infeasible model is committed then preflight-refused.
13 infeasible cards:8 discarded,4 pending,1 committed. Pending is not discarded;
this corrects the earlier checkpoint's10-discarded/2-pending statement. Neither
input visibility nor a revision is evidence of a private causal reasoning process.

13 successful quoted model calls:9 supported service predictions,4 unknown. All13
context-envelope/preflight classifications agree. This agreement is with frozen
conservative UTF8-byte/image preflight,not true tokenizer capacity or OOM prediction.
All36 successful quoted byte estimates match actual movement receipts. Most local
zero transfers are deterministic locality facts,not learned latency validation.
Unsupported nonlocal transfer profiles remain unknown; configured serialization
is not an empirical prediction. No unrealized proposal has observed counterfactual cost.

| Quoted model | Support | Actual s | Actual-minus-p50 s | Actual-minus-p90 s |
| --- | ---: | ---: | ---: | ---: |
| MH Fast |10|127.532|-50.285|-192.608|
| MH Slow |10|125.679|-52.137|-194.460|
| Academic Fast |15|71.302|-28.002|-56.348|
| Financial Slow |6|15.334|4.356|-0.194|
| Video Fast raw8 #1 |12|229.037|-45.431|-62.277|
| Video Fast raw8 #2 |12|190.822|-83.646|-100.492|
| Video Fast raw8 #3 |12|260.077|-14.391|-31.237|
| Video Fast raw8 #4 |12|190.976|-83.492|-100.338|
| Video Fast final |6|16.810|5.832|1.282|

Unknown service:Academic Slow6.391s,Financial Fast8.370s,Video Fast additional
108.439s,Video Slow30.335s. They are not backfilled. Short transfer estimates are
not precise:Video Slow predicts0.511/0.694s,observes0.825s;MH Fast predicts0.123/
0.898s,observes0.066s. p50/p90 work sums are not joint quantiles/critical-path time.

Academic Fast C Manager work96.515s versus A21.251s,18 versus7 turns,without
less traffic; quote mechanism work1.380s excludes this cloud overhead. MH C uses
18/19 Manager turns and246545/263201 input tokens;A uses9/4 turns and109106/36804
tokens (Fast A also8 specialist turns). Video Fast four raw8-image inferences alone
cost870.912s despite visible per-call p50 quotes274.468s. Model/service cost and
workflow expansion dominate,not the1.813s action-transfer work. Specialists are
intentionally unquoted;root-only C is not all-action economic control.

Measured overlap exists only in A:MH Fast max5/actions overlap0.696s;Financial
Fast/Slow max4,2.030/1.515s;Video Fast max3,0.989s. C trajectories are serial.
The protocol supports parallel commit;these trajectories choose serial actions.
No critical-path number is invented from service-work sums; full intervals/graphs
are retained. Model caching and cloud turn latency can change n=1 ordering.

## What is established, and what is not

Established:cost consequence cards reach the real Agent;static feasibility feedback
can prevent actions;open-ended trajectories change;cheaper paths can lose evidence;
model/Manager/expansion/initial placement can dominate bytes. C is not a robust
quality-preserving improvement over A in this cohort. No empirical route is promoted.

Not established:causal improvement versus original Blind/Raw-Aware,universal failure
of all cost guidance,stable crossover,statistical significance,within-run dynamic-H
adaptation,GPU preference reversal,or evidence-preserving reduction in prompt-only
Academic Slow. First actions can differ before any quote;A also varies across H
without future-profile input. H!=G alone does not establish consequence-guided causality.

Inherited caveat:the frozen generic choice-format helper also prefixes some root
intermediate text/plain model actions. Four Fast Video C calls are affected outside
synthesis. No JSON/schema failure proves an invalid cell;not shown to cause wrong
answers. Do not tune it away or attribute every semantic failure solely to cost
feedback. [Presentation audit](cost-guidance-matrix-admission-audit-v1.md) retains
the original evidence. No experiment is replaced for ordinary Agent behavior.

Stop after the completed primary matrix and audits:the tested cheap formulations
have useful negative evidence;mandatory C fails its promotion criteria. B/D/E are
untested. Further method variants are recommendations,not launched cells. See
[final ranking and next experiment](next-method-recommendation-v1.md).
