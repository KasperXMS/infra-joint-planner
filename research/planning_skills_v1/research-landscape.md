# Research landscape and the question retained for experiment

This is a targeted reading synthesis, not a systematic review or proof that no other relevant method exists. Versions, inspected methods/ablations, and abstract-only entries are enumerated in the [literature ledger](literature-novelty-ledger.md). Experimental conclusions belong in the final report, not in this prior-work map.

## What the proposed research cannot claim as new

Skill availability and presentation granularity are already evaluated under controlled knowledge conditions. A new abstract/procedure/atomic scale, without matched contents and a mechanism-specific contrast, would largely repeat the questions of [SkillsBench v4](https://arxiv.org/html/2602.12670v4) and [the controlled granularity study v1](https://arxiv.org/html/2605.31408v1).

Procedural anchoring, incompatible assumptions, invocation failures and excess verification already have empirical taxonomies. Our traces must provide independently checkable behavior, rather than merely renaming these categories. [Demystifying Agent Skills v1](https://arxiv.org/html/2608.14036v1) also studies transfer and lightweight procedural baselines. [Skills Can Be Harmful v1](https://arxiv.org/html/2608.11888v1) supplies a selected negative-case analysis; its selected cases do not estimate unconditional harm prevalence.

Compilation and selective materialization are also established. [SkVM v3](https://arxiv.org/html/2604.03088v3) profiles model–harness capability and moves work into compile/runtime passes. [SkillSmith v1](https://arxiv.org/html/2605.15215v1) exposes guarded executable interfaces. Consequently, neither a capacity-aware compiler nor a typed runtime interface is an original contribution merely because we implement one for 4B/9B.

State maintenance is an especially close predecessor. [StateMem v1](https://arxiv.org/html/2608.19652v1) explicitly represents current state, propagates recheck requirements and compares a structured answer wrapper with a matched control. [PACMI v1](https://arxiv.org/html/2610.05732v1) studies provenance and validity propagation. An observation-only ledger or invalidation cascade here is not itself a new mechanism.

## Assumptions that determine whether comparisons are informative

| Assumption / boundary | Why it matters | Treatment here |
| --- | --- | --- |
| Skill knowledge stays constant | Added examples or task hints can masquerade as a granularity effect | One generic bank remains unchanged; joins/unjoined tables have matched fact inventories |
| Prompt delivery is part of the intervention | Moving identical content changes role, position and salience together | Explicit same-bank role-placement contrast; no claim that role alone is isolated |
| State is already available | A representation gain should not come from otherwise hidden information | Runtime support reads actual tool observations and public policies only |
| A verifier may certify a weaker property than the task requires | Provenance/freshness completion need not imply a correct policy choice or answer | Separate completion, numeric success, conditional executed policy correctness and verifier work |
| An action probe is not an autonomous workflow | Specifying a target node removes scheduling and recovery decisions | Development probes are labeled separately from real workflow TSR |
| A supplied graph already externalizes decomposition | Layer names and topological order can make planning look easier | Primary scope is explicit; conditional transfer removes ordering/name hints |
| Greater model size does not identify a universal capacity law | Checkpoint, precision, thinking and serving also affect outcomes | Same within-model backend/contract; conclusions remain conditional on these checkpoints |
| Resource proxies are not prices | Batched waiting and prompt tokens do not determine exact GPU USD | Count batch wall once, retain local USD unknown, record whole-instance CNY rental |

## Narrow unresolved question pursued here

Given a strict tool contract, visible current values and an explicitly declared dependency graph, does placing current artifact values directly beside each action policy improve autonomous rebuilding and semantic re-decision beyond an equally informed, equally long unjoined rendering? Does that effect differ between these 4B and 9B checkpoints, or does a representation merely improve one-step decisions while whole-workflow failures persist?

This is deliberately narrower than claiming that state tracking, skill compilation or anchoring is unexplored. Exact operation correctness conditional on the model's actual intermediate values distinguishes policy errors from upstream arithmetic errors; paired policy-stable/flip source updates distinguish rebuilding from semantic re-decision. Those controls make the question testable. They do not by themselves establish algorithmic novelty or external-domain generalization.

## Evidence required before a recommendation

The primary held-out study must retain all failures and compare joined/unjoined support, ordinary state bookkeeping, static prompting, local delivery and role placement. A useful current-fact effect then requires independent structural transfer with unchanged mechanisms. Remaining errors must be located in actual scheduling, dependency use, branch choice or terminal control. Positive aggregate TSR alone is insufficient to recommend a new research direction, and a negative result can still support a bounded characterization.

## Where the completed evidence leaves this landscape

The necessary primary, independent structural transfer and post-hoc decision diagnosis are complete. They support the narrower evaluation problem: a state representation can improve legal completion and reduce repeated work while leaving semantic operation choices wrong; numeric answer equality may even hide those wrong choices. Transfer has 19 numeric successes but only seven policy-compliant final ancestries. This is conditional synthetic evidence, not a demonstrated assumption failure for all open-ended agents.

The final report retains one nine-field characterization/measurement direction. It explicitly compares StateMem, SkillSmith and SkVM, preserves the current mechanism's overlap with prior work, and calls for new-domain, cost-matched semantic-controller comparisons only as future requirements. It makes no claim that a new name, a small checkpoint, or a negative example alone establishes novelty. No broad skill-granularity or capacity scaling law follows from two checkpoints and the selected graph clusters.
