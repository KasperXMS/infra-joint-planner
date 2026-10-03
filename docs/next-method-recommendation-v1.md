# Next-method recommendation v1

2026-10-04. Decision after the audited16-cell A/C exploration: **do not promote
mandatory Quote-before-Commit as the primary method**. Retain Ledger as the lean
comparison baseline. The next design hypothesis is an optional,amortized B-style
action-consequence interface,not an empirically validated winner. No new experiment
or tuning is launched by this recommendation. [Full results](cost-guidance-final-results-v1.md).

## Recommended primary research direction

Study **uncertainty-aware, low-overhead consequences for Agent-proposed ready
semantic actions**, with the existing separate physical scheduler. The consequence
vector should distinguish actual information movement,context envelope,model/tool
service support and control overhead. It cannot infer answer correctness or choose
semantic evidence for the Agent. Unknown is a first-class value,not a cheap zero.

This direction keeps task decomposition/representation/retrieval/synthesis open-
ended,without a topology pool,whole-DAG search or executable tool invention. It
differs from C's mandatory approval round trip:make pricing optional/amortizable,
and expose the accounting of the pricing protocol itself. This is a **generic
design refinement motivated by failures**,not a task recipe or demonstrated gain.
Keep the current A/C implementation/evidence frozen;new interface implies a new
variant/protocol. Do not conceal the quality risk of choosing fewer evidence inputs.

No claim that B will fix MH or Video:MH retrieved the right documents then selected
the wrong subset;Video expanded despite quotes;both may require a better decision
policy rather than a better cost representation. Explicitly test that alternative.

## Ranked routes

Ranks are **next-investment priority**,not a tested-performance leaderboard.

| Rank / route | Evidence and disposition | Failure mode | Literature overlap / novelty risk | Complexity | Expected paper value |
| --- | --- | --- | --- | --- | --- |
|1 B:optional Action Cost Card|Shared estimator is implemented,standalone B not tested;recommended next hypothesis,not promoted method|Incorrect estimates,evidence abandonment,optional card ignored|Abacus/AQP/CostBench overlap;interface alone weak novelty|Low-medium;must avoid extra compulsory cloud turn|Potentially isolates actionable consequences from protocol overhead;benefit unproven|
|2 A:spent-only Ledger|8 runs complete;MH/Academic score1 in both H;recommended lean baseline,not proof Ledger improves original Blind|Past cost cannot choose future evidence;Financial/Video wrong;Slow MH full aggregation|Budget Tracker-inspired,not BATS reproduction;high overlap/low originality|Low|Strong audit/control baseline,not sufficient standalone novelty|
|3 D:up to3 ready candidate consequences|Untested;defer until B's estimator/overhead evidence is sound|Candidate omissions,extra cloud turns;cost Pareto does not preserve semantic adequacy|EnumGRPO enumeration and Abacus Pareto collision;must remain online/ready/local|Medium|Useful representation-vs-policy diagnostic,not justified live expansion now|
|4 C:mandatory Quote-before-Commit v0|8 runs complete;49 actual-visible quotes;do not promote current protocol|MH quality regression,Academic Fast overhead,Video Fast expansion,prompt-only shortcuts|AQP/cost-aware tool-use/operator pricing;novelty in bounded distributed protocol only if useful|Medium;ownership/readiness/TTL/metering/testing|Valuable falsifiable negative result and reusable audit interface;weak positive method case|
|5 E:trace-distilled heuristics|Untested;offline design only,not injected|Task memorization,evaluator hindsight,unverified quality surrogate|Strong direct EnumGRPO collision;clearly attribute any contrastive distillation|Medium-high|Limited as primary novelty;could be attributed baseline after held-out evaluation|

No forced winner,no claim all five routes failed,no claims of universal cost-
optimality. A's correct executions do not establish cost-guidance effectiveness;
historical Blind/Raw-Aware are not contemporaneous randomized controls.

## Q1-Q10

**Q1. Closest literature?** For semantic cost-aware interleaving,
[EnumGRPO](https://arxiv.org/abs/2606.03152);for semantic cost/quality estimation,
[Abacus](https://arxiv.org/abs/2505.14661);for cross-layer serving,
[Murakkab](https://www.usenix.org/conference/osdi26/presentation/chaudhry).
[INFRAMIND](https://arxiv.org/abs/2606.11440),
[DynTaskMAS](https://ojs.aaai.org/index.php/ICAPS/article/view/36130),
[AQP](https://www.cs.umd.edu/~amol/papers/fnt-aqp.pdf) bound the infrastructure/
dynamic-graph/runtime-feedback story. [Literature map](method-literature-map-v1.md)
contains all21 original-body comparisons,authors/venues/URLs and reading caveats.

**Q2. Biggest novelty collision?** EnumGRPO for stepwise semantic cost optimization
and trace heuristics;Murakkab/INFRAMIND for broad infra-aware MAS/cross-layer claims.
Published Murakkab adds a dynamic coding pipeline and request-specific compositions:
it cannot be dismissed as only a fixed-DAG placer. Retire "first cost-aware workflow",
"first dynamic graph" and "first logical/physical separation" claims. The narrow
distributed locality/consequence conjunction is a hypothesis requiring evidence,
not proof of novelty by combining established components.

**Q3. Direction preserving our differences?** Online ready-action consequences for
open-ended semantic choices over distributed artifacts,with anonymous feedback and
a separate unchanged scheduler. Demonstrate semantic changes beyond device routing,
under genuinely different infrastructure consequences,with quality/overhead audits.
Current model selections are all A28;dynamic load/device heterogeneity claims remain
unproved. Do not expand the setting merely to make a broad story sound complete.

**Q4. Why raw profiles insufficient?** Profiles describe H,not the consequences of
specific artifact sets/representation/granularity choices. Existing Raw-Aware
references are mixed. The new data also shows the deeper limitation:correctly exposed
prices alone do not guarantee useful choices. Quote offers consequences yet MH drops
already retrieved evidence and Video performs expensive expansion. Information,
semantic adequacy,decision policy and control cost are separate issues.

**Q5. Is Ledger enough?** Enough as a reusable low-complexity accounting/control
baseline;not enough evidence as a cost-rational adaptation method. A correct MH Slow
run moves5.20MB through full aggregation. Financial/Video stay wrong. A changes across
H despite no prospective-H input,so stochastic/recovery differences must not be called
cost-conditioned optimization. Its improvement over old Blind is unmeasured here.

**Q6. Are action consequences clearly more useful than raw profiles?** Not established
for quality-preserving system gains. C gives auditable feasible-request feedback:
13 infeasible cards,12 uncommitted;exact byte prediction,49 actual-visible cards.
But omission of evidence/prompt-only escape is not successful semantic reduction.
No matched Raw control isolates consequences,and mandatory two-step overhead
confounds representation versus policy. Accurate exposure is an intermediate result.

**Q7. Is Quote-before-Commit the primary method?** No for current v0. Academic Fast
adds71s and model prices do not stop Fast Video's7-call expansion;MH loses quality
in both H. Quotes cost little deterministic work but consume cloud reasoning horizon
and context. Root-only quoting also leaves Blind specialist expansion outside control.
Retain non-executing quote/readiness/audit components;do not present mandatory C as
a robust quality-preserving optimizer.

**Q8. Multi-candidate/Pareto?** Conditional diagnostic,not the next live priority.
Alternative descriptions might expose local-versus-aggregate or raw-versus-sheet
trade-offs,but candidate generation adds cloud work. Pareto-pruning system cost alone
cannot establish semantic equivalence. First isolate B's presentation/overhead and
estimator support;later compare at most3 Agent-proposed ready actions without a
predefined topology pool or gold-aware selection. No D cells run in this phase.

**Q9. Trace-distilled heuristics?** Useful offline failure taxonomy with support,
counterexamples,scope and overfit risk;not ready for runtime injection. For example,
"reduce before reasoning" fits some efficient trajectories but MH's reduced inputs
omit both supporting documents;"use sheets" reduces Video service but still wrong.
Do not convert private audit annotations into future Agent rules. Any tested E
must be separately versioned,attributed to EnumGRPO lineage,and evaluated held-out.

**Q10. RL warranted?** No.16 exploratory n=1 runs do not show all non-RL interfaces
failed;B/D/E untested,control-overhead effects unresolved and no safe quality reward
or simulator validated. RL would add cost/credit-assignment/novelty issues instead
of diagnosing them. Keep RL a future option,not implementation/training now.

## Next formal experiment: conditional proposal, not a launched sweep

Before formalizing:freeze a standalone optional B contract and pre-register stop/
quality criteria;verify actual recipient exposure,unknown propagation,no executable
primitive change and no mandatory quote turn. Keep one shared scheduler/harness.
Separate static-feasibility cards from genuinely dynamic cost cards. Do not promise
quality from a cost estimator or tune thresholds to this matrix's answers.

Suggested small diagnostic before any paper-scale study:existing MH/Academic/Video
tasks × Fast/Slow × A/B/C (18 cells,n=1),with prospectively balanced order and frozen
profiles. This is **next-stage advice only**;not part of current16/36 reservations.
Use C as a negative-control protocol to separate representation from approval cost;
retain original Blind/Raw-Aware as references or add matched controls only when
explicitly justified. If findings justify formal evaluation,then increase held-out
task coverage/repetitions and predefine sample size,not result-driven repeat selection.

Report quality/completion independently;successful reduction must preserve useful
evidence,not merely score once via prompt-only inference. Include initial/action
movement,model/tool/Manager/specialist/Verifier work,actual E2E,profile support/error,
graph changes and measured overlap. Match profiles/bytes exactly;do not invent
critical paths/counterfactual quality. Require explainable infrastructure-dependent
revisions on more than one workload without systematic quality loss or dominant
control overhead. Reject B if it repeats C's evidence discard/expansion failure.

Broader dynamic-H/load/heterogeneous-model evaluation is a later required claim
test,not established by the current static bandwidth intervention. Independent
quality-preserving semantic planning is not solved by the shared physical scheduler.

## Current stop and deliverables

Stop the current unattended exploration after16 primary cells and full audits.
This is useful negative evidence for **tested A/C**,not "all simple methods failed".
Reasons not to spend the remaining20 slots:mandatory C misses promotion criteria
through clear multi-workload quality/overhead failures;D adds the same costly decision
protocol before isolating it;E has high novelty/overfit risk. No prompt rescue/new
tasks/estimator hindsight/RL/whole-workflow search is authorized by this conclusion.

Final deliverables:literature map,collision audit,protocol/results,prototype audit,
failure paths and this Q1-Q10/ranking/next-experiment recommendation. Benchmark data
and full evidence remain remote;branch is pushed without merging main. The closest
published-paper version check is recorded;other unverified version differences
remain qualified rather than treated as absence claims.
