# Decision after Harness v2 requalification

**Stage 3 held-out validation: No-Go.** The preregistered rule requires an
existing method to show a repeatable logical workflow change, lower measured
cost, preserved evidence and acceptable task quality in both trials. Stage 2
has nine task/network/method combinations with L2 structural changes in both
trials, but zero preserve score 1 for Blind and the candidate method in both.
Therefore no method qualifies, and the 48-cell held-out matrix was not run.
The six held-out task selection rule remains frozen but unused; there is no
post-hoc favorable task selection.

The H1 resource-blind baseline is operational but not reliably successful:
local Qwen3.8-27B scored 6/12 on the six frozen Stage 1 tasks over two
trials, and the cloud reference scored 3/6. Harness v2 carried all completed
outputs into the original evaluator and recorded failures without silent
acceptance or context truncation. The previous terminal/state-management
defect is not the dominant observed limit in this sample. The fixed cloud
Verifier's invalid original function calls, and one semantic-invalid verdict,
are instead prominent: Stage 1 had seven Verifier raw-schema interruptions
plus one semantic interruption; Stage 2 had 11 plus one. These are observed
model/contract failures under the frozen roles, not retroactively repaired
cells or infrastructure-awareness effects.

The KEEP-only H2 check found no natural pending suffix in either of two
scenarios. The Manager dispatched each proposed action immediately, leaving
no dependency-rich frontier to seal and patch. A future logical adapter
cannot honestly claim to optimize the pending workflow on this evidence; it
would first need an explicit, provenance-preserving plan representation and
an actual pre-execution decision point. This study did not create either.

Raw Aware changed logical operations or information flow in 10/12 matched
pairs, and Cost Ledger in 11/12, so physical placement alone is not the whole
story. Yet neither simple method improved TSR: across both networks, Blind
scored 3/12, Aware 2/12 and Ledger 1/12. Their aggregate E2E and known cloud
USD were lower mainly amid shorter, failed or wrong-answer trajectories.
Slow Video trial 2 Aware was a single quality-preserving lower-cost pair;
its companion trial lost correctness. The Fast Video answer reversal across
trials also defeats a reliable infrastructure-state preference claim. The
measured improvements cannot be assigned to the Physical Scheduler alone:
that scheduler was constant, while logical structure and stochastic Planner
behavior both varied. No same-task, two-trial quality-preserving cost
mechanism was established.

Accordingly, **do not treat Raw Aware or Cost Ledger as a competitive
quality-preserving baseline, and do not implement a full Infra-aware Logical
Workflow Adapter from the current H2 interface yet.** The research problem
is still live: a future mechanism should expose a real pending workflow,
track artifact provenance, and optimize data reduction or model placement
only while protecting necessary evidence and evaluator quality. That is a
design hypothesis, not a demonstrated need for a particular Adapter.
Separately, reliable Verifier function-call validity is necessary for cleaner
future comparisons. No additional experiment or code change is launched by
this decision.

The evidence is exploratory: three studied anchors, two trials each, one
frozen serving configuration. It supports a No-Go under this protocol, not a
statistical claim that either method can never work. Local GPU monetary cost
is unknown. Source, model and task hashes, individual redacted cell results,
workflow signatures, cost receipts, network restoration and Worker cleanup
are retained in the branch; sensitive raw traces remain only on the
experiment controller.
