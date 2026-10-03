# Method literature map v1

Status: **21 requested original bodies read**, 2026-10-04. Comparative review v1.
Representative visual checks are recorded, not claimed for every figure.
Published-version differences and remaining figure checks stay explicit;
absence of a feature in the read version is not proof of global novelty.

## Reading coverage

| # | Requested original work | Reading status |
| --- | --- | --- |
| 1 | Cost-Aware Optimization for Agentic Query Execution / EnumGRPO | Main text and references read; figure inspection pending |
| 2 | Abacus | Main text and references read; PDF figure inspection pending |
| 3 | CostBench | Main text/appendices/references and published prompt pages read; prompt pages visually inspected |
| 4 | Budget-Aware Tool-Use Enables Effective Agent Scaling | Main text/appendices/references and embedded prompts/cases read; prompt/case pages visually inspected |
| 5 | INFRAMIND | Original HTML through appendix/references read; figures pending |
| 6 | Murakkab | Full v2 preprint and published OSDI PDF read; Figure5/Table1 visually checked; version caveat updated below |
| 7 | Latency-Aware Orchestration for Multi-Agent LLM Workflows on Heterogeneous GPUs | Original HTML through references read; figures pending |
| 8 | From Intent to Infrastructure | Original HTML through references read; figures pending |
| 9 | LLMCompiler | Main text/appendices/references and published prompt pages read; remaining figures pending |
| 10 | Flow | Main text and complete PDF appendices/references read; workflow-update figure visually inspected |
| 11 | AFlow | Main text/appendices/references and PDF-embedded code/prompts read; optimizer prompt visually inspected |
| 12 | DynTaskMAS | Complete published nine-page PDF read; architecture visually inspected |
| 13 | GPTSwarm | Complete published PDF read; graph representation visually inspected |
| 14 | MasRouter | Complete published PDF, profiles/cases/algorithm read; framework visually inspected |
| 15 | Automated Design of Agentic Systems | Complete ICLR-marked v2 PDF read, including code/prompts; search architecture visually inspected |
| 16 | Palimpzest | Complete v2 PDF read, including plan examples/references; optimizer architecture visually inspected |
| 17 | DocETL | Complete 22-page v3 original read; optimization graph visually inspected; published-version comparison pending |
| 18 | Optimizing Agentic Workflows using Meta-tools | Complete 17-page v2 original read; framework and appendix result tables visually inspected |
| 19 | RouteLLM | Complete 16-page ICLR-marked v4 original read; evaluation curves visually inspected |
| 20 | FrugalGPT | Complete specified 13-page 2023 original read; strategy figure visually inspected; later TMLR revision not compared |
| 21 | Adaptive Query Processing | Complete author-hosted original: all 70 physical / 140 printed pages read; Figure 3.3 and Table 8.1 visually inspected |

## 1. Cost-Aware Optimization for Agentic Query Execution

Authors: Lunyiu Nie, Yilin Xia, Yiren Liu, Christopher Jermaine, Swarat Chaudhuri.
2026 arXiv preprint; an accepted venue is **not verified**.
[Canonical](https://arxiv.org/abs/2606.03152),
[original HTML v1](https://arxiv.org/html/2606.03152v1),
[PDF](https://arxiv.org/pdf/2606.03152),
[code](https://github.com/Flitternie/EnumGRPO).

| Field | Original-text finding / comparison |
| --- | --- |
| Problem / representation | Cost-aware agentic queries; evolving relational workspace |
| State / actions | Query, schemas, samples, statistics, trace; SQL/LLM/auxiliary operations |
| Dynamic infra / locality | Distributed runtime network/locality optimization not demonstrated |
| Semantic change / full plan | Stepwise observation-conditioned actions; no upfront fixed full plan required |
| Cost / quality | Operator tokens/dollars; reference-based tuple/cell quality during training |
| Method / timing | Offline axis enumeration and contrastive in-context heuristic learning; online execution without enumeration |
| Workloads / baselines | SWAN, four SQLite databases; AgenticText2SQL, AgenticBlendSQL, base agent |
| Assumptions | Training references; cloud models; reported single CPU/cloud testbed |
| Overlap / collision | Cost-aware evolving semantics and logical/physical distinction already present |
| Difference | Dynamic distributed artifact movement and separate device scheduler are not established here |
| Reusable mechanism | Contrastive distillation with scope/counterexamples; separately versioned if used |
| Baseline role | Close semantic cost-aware comparator, not direct hardware-placement baseline |

Reading locators: HTML sections 2-5 and conclusion/references. Its operator
placement axis concerns semantic pre/post-aggregation ordering, not GPU placement.

## 2. Abacus: A Cost-Based Optimizer for Semantic Operator Systems

Authors: Matthew Russo, Chunwei Liu, Sivaprasad Sudhir, Gerardo Vitagliano,
Michael Cafarella, Tim Kraska, Samuel Madden.
PVLDB 19(5), 1060-1073, 2026; DOI 10.14778/3796195.3796215.
[Canonical](https://arxiv.org/abs/2505.14661),
[original HTML v3](https://arxiv.org/html/2505.14661v3),
[PDF](https://arxiv.org/pdf/2505.14661v3),
[code](https://github.com/mitdbg/palimpzest).

| Field | Original-text finding / comparison |
| --- | --- |
| Problem / representation | Constrained semantic-operator optimization; developer logical pipelines |
| State / actions | Sampled quality/cost/latency, priors; implementation and rewrite rules |
| Dynamic infra / locality | Runtime distributed locality/network adaptation not demonstrated |
| Semantic change / full plan | Reordering/reduced-context implementations; optimize before primary execution |
| Cost / quality | Dollars/latency; labels or model judge, per-operator estimates |
| Method / timing | Pareto-Cascades plus bandit sampling during optimization |
| Workloads / baselines | BioDEX, CUAD, MMQA; LOTUS, DocETL, no-context model |
| Assumptions | Approximate operator independence; product quality, additive costs, max-path latency |
| Overlap / collision | Profile-guided quality-cost workflow optimization is not new |
| Difference | Not an open-ended online Manager operating on changing distributed infrastructure |
| Reusable mechanism | Uncertainty/support-aware operator estimates; no private quality oracle for our estimator |
| Baseline role | Declarative optimizer comparator, not drop-in unrestricted online Agent |

Reading locators: HTML sections 2-4, algorithms 1-5. Optimization samples execute
operators; they are not no-execution quotes. MMQA corpus filtering uses ground
truth related-item coverage, unsuitable to copy into our faithful adapter.
Abstract and section 4.3 numerical summaries differ; no headline speedup is
adopted here pending PDF verification.

## 3. CostBench: Evaluating Multi-Turn Cost-Optimal Planning and Adaptation in Dynamic Environments for LLM Tool-Use Agents

Authors: Jiayu Liu, Cheng Qian, Zhaochen Su, Qing Zong, Shijue Huang,
Bingxiang He, Yi R. (May) Fung. ACL 2026, pp. 12826-12858.
[Canonical](https://aclanthology.org/2026.acl-long.584/),
[published PDF](https://aclanthology.org/2026.acl-long.584.pdf),
[HTML v3](https://arxiv.org/html/2511.02734v3),
[code](https://github.com/JiayuJeff/CostBench).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Dynamic cost-sensitive tool planning; ordered typed pipelines |
| State / actions | Query, costs, history, blocking events; atomic/composite tools |
| Dynamic infra / locality | Synthetic tool-cost changes; no measured network/locality |
| Semantic change / full plan | Iterative path changes; fixed equivalent paths |
| Cost / quality | Synthetic expenses, coverage and completion |
| Method / timing | Online LLM decisions; Dijkstra oracle and greedy comparator |
| Workloads / baselines | Six synthetic domains, ten models; static/dynamic scenarios |
| Assumptions | Composite tools, guaranteed reachable goals, enumerated equivalent paths |
| Overlap / collision | Cost visibility does not guarantee rational adaptation |
| Difference | No real distributed consequence estimation or uncertain semantic equivalence |
| Reuse / baseline | Motivation; not a new workload in this exploration |

Reading: HTML main/appendices; published PDF pp. 28-33, prompt pages 32-33
visually inspected. Cost/path metrics condition on goal completion; invalid calls
are not charged. Our accounting must retain failures and their real work.

## 4. Budget-Aware Tool-Use Enables Effective Agent Scaling

Authors: Tengxiao Liu, Zifeng Wang, Jin Miao, I-Hung Hsu, Jun Yan, Jiefeng Chen,
Rujun Han, Fangyuan Xu, Yanfei Chen, Ke Jiang, Samira Daruki, Yi Liang,
William Yang Wang, Tomas Pfister, Chen-Yu Lee. COLM 2026 (arXiv v2 comments).
[Canonical](https://arxiv.org/abs/2511.17006),
[HTML v2](https://arxiv.org/html/2511.17006v2),
[PDF](https://arxiv.org/pdf/2511.17006v2),
[code](https://github.com/google-research/budget-aware-agent).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Budget-conditioned tool scaling; ReAct trajectories or BATS tree/checklist |
| State / actions | Used/remaining tool budgets, history; search/browse and domain tools |
| Dynamic infra / locality | No distributed network/artifact locality model demonstrated |
| Semantic change / upfront plan | Iterative decisions; BATS updates plans and pivots |
| Cost / quality | Calls and token/API expenses; benchmark correctness |
| Method / timing | Online Budget Tracker; BATS verification, restarts, summary and answer selection |
| Workloads / baselines | BrowseComp, Chinese variant, HLE Search; ReAct, SLIM, parallel scaling; appendix coding/retail |
| Assumptions | Budget guidance and context management; tool-call budget is not complete system cost |
| Overlap / difference | Ledger motivation already established; our ledger adds measured distributed execution work |
| Collision / reuse | Not novel to expose remaining budget; reuse only spent-budget accounting |
| Baseline role | Simple attributed Ledger; do not import BATS retries/summaries/new verifier |

Reading: embedded Budget Tracker/BATS prompts and cases now read in PDF;
pp. 24-28 and 30 visually inspected. Tracker includes budget-tier strategy
guidance, not just balances. Our spent-only Ledger intentionally omits it.
HTML table/reference gaps closed; this was an earlier reading checkpoint.
Current overall coverage is recorded in the table at the start of this document.

## 5. INFRAMIND: Infrastructure-Aware Multi-Agent Orchestration

Authors: Ahasan Kabir, Jiaqi Xue, Mengxin Zheng, Qian Lou. 2026 preprint;
accepted venue and code URL unverified.
[Canonical](https://arxiv.org/abs/2606.11440),
[HTML](https://arxiv.org/html/2606.11440v1),
[PDF](https://arxiv.org/pdf/2606.11440).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Latency/quality-constrained MAS; arrival-time topology/role assignment |
| State / actions | Queues, cache, time remaining; five models times three reasoning strategies |
| Dynamic infra / locality | Shared serving load; distributed artifact locality not demonstrated |
| Semantic change / upfront plan | Initial topology committed; runtime topology revision explicitly future work |
| Cost / quality | Latency; task reward with quality constraint |
| Method / timing | Hierarchical CMDP; planner REINFORCE, executor PPO, shared multiplier; online EDF |
| Workloads / baselines | Math/code/MMLU-Pro; MoA, GPTSwarm, MasRouter; two B200 GPUs |
| Assumptions | Fixed serving pool, trained policies, selected inference strategies |
| Overlap / collision | Infrastructure-aware MAS and structure conditioned on initial load already exist |
| Difference | No demonstrated online evidence-conditioned retrieval/reduction graph evolution |
| Reuse / baseline | Separate initial structural choice from runtime execution routing; conceptual infra-aware comparator |

Original-text locator: sections 3-6 and appendices. Do not describe its entire
planner action space as finite solely from the executor's fifteen choices.

## 6. Murakkab: Resource-Efficient Agentic Workflow Orchestration in Cloud Platforms

Authors: Gohar Irfan Chaudhry, Esha Choukse, Haoran Qiu, Inigo Goiri,
Rodrigo Fonseca, Adam Belay, Ricardo Bianchini. OSDI 2026, pp. 567-587.
[Canonical](https://www.usenix.org/conference/osdi26/presentation/chaudhry),
[published PDF](https://www.usenix.org/system/files/osdi26-chaudhry.pdf),
[preprint HTML v2](https://arxiv.org/html/2508.18298v2).
Code URL unverified.

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Declarative task dependencies, reusable workflow components/configuration knobs |
| State / actions | Demand, resource availability, profiles; workflow knobs, models, hardware, instances |
| Dynamic infra / locality | Adaptive demand/resources; distributed artifact-link costing not demonstrated |
| Semantic change / upfront plan | Configuration can alter enabled tasks/frames/debate; query composition supported |
| Cost / quality | Cost, latency, energy, quality/SLO; offline ground-truth workload profiles |
| Method / timing | Offline profiles, periodic MILP optimization, online dispatch/autoscaling |
| Workloads / baselines | Video QA, code debate, math reflection; manually configured runtime and ablations |
| Assumptions | Registered components/configurations and reusable hardware/service profiles |
| Overlap / collision | Strong cross-layer/profile-guided heterogeneous orchestration overlap |
| Difference | Not demonstrated continuous evidence-driven Manager decisions with per-action no-execution quotes |
| Reuse / baseline | Separate workload-quality profiles from hardware service profiles; systems comparator |

This entry describes the fully read v2 preprint. Published PDF differences remain
unverified. **Not** accurately characterized as physical-only or immutable-DAG.

## 7. Latency-Aware Orchestration for Multi-Agent LLM Workflows on Heterogeneous GPUs

Authors: Jinghao Wang, Yifeng Zhang, Xiao Zhou, Yao Lu, Yihui Zhang, Xiaoyang
Sun, Tianyu Wo, Xu Wang, Chunming Hu, Renyu Yang. September 2026 preprint;
venue/code release unverified.
[Canonical](https://arxiv.org/abs/2609.03335),
[HTML](https://arxiv.org/html/2609.03335v1),
[PDF](https://arxiv.org/pdf/2609.03335).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Incrementally exposed logical graph; physical execution graph/window |
| State / actions | Device/residency/memory/load; placement, fusion, lease, prefetch, reclamation |
| Dynamic infra / locality | Heterogeneous GPU lifecycle and concurrent demand; artifact-link modeling not demonstrated |
| Semantic change / upfront plan | Preserves logical semantics/model assignments; logical graph may emerge incrementally |
| Cost / quality | Completion latency/memory; semantics preservation rather than quality optimization |
| Method / timing | Offline device-aware GNN predictor; online ready-window heuristic and lifecycle decisions |
| Workloads / baselines | GSM8K ensemble, MBPP repair, QMSum; Parrot, Kairos, predictor ablations |
| Assumptions | Operator/model profiles; resolved ready/future demands; V100/A100 serving pool |
| Overlap / collision | Logical/physical separation and incremental graph scheduling already exist |
| Difference | Physical rewrites, not evidence-dependent semantic workflow revisions |
| Reuse / baseline | Validate decision ordering, not just estimator error; strong physical-optimization comparator |

## 8. From Intent to Infrastructure: LLM-Driven Agent Compilers for ISAC Networks

Authors: Lijie Zheng, Xudong Zhong, Baoquan Ren, Xiangwu Gong, Xinghui Zhu,
Ji He. July 2026 preprint; venue/code URL unverified.
[Canonical](https://arxiv.org/abs/2607.16269),
[HTML](https://arxiv.org/html/2607.16269v1),
[PDF](https://arxiv.org/pdf/2607.16269).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Intent compilation into ISAC policy graph with constraints/feedback edges |
| State / actions | Capabilities/channel/environment; task decomposition, mapping, parameter/recompilation decisions |
| Dynamic infra / locality | Network/environment changes; artifact-locality costing not demonstrated |
| Semantic change / upfront plan | Compiled graph; fast parameter, partial and full recompilation tiers |
| Cost / quality | Mission utility, control latency, energy; simulated detection/communication outcomes |
| Method / timing | Slow LLM compiler plus deterministic fast solvers; runtime tiered adaptation |
| Workloads / baselines | UAV rescue simulation; Fixed Rule, MADDPG, Direct LLM |
| Assumptions | ISAC library/capability database and simulation models |
| Overlap / collision | Cross-layer compilation and infrastructure-conditioned graph revision already exist |
| Difference | Not measured data-intensive Agent tool/model action-consequence feedback |
| Reuse / baseline | Separate adaptation timescales; conceptual lineage, not drop-in benchmark baseline |

## 9. An LLM Compiler for Parallel Function Calling

Authors: Sehoon Kim, Suhong Moon, Ryan Tabrizi, Nicholas Lee,
Michael W. Mahoney, Kurt Keutzer, Amir Gholami. ICML 2024,
PMLR 235, pp. 24370-24391.
[Canonical](https://proceedings.mlr.press/v235/kim24y.html),
[published PDF](https://raw.githubusercontent.com/mlresearch/v235/main/assets/kim24y/kim24y.pdf),
[HTML v3](https://arxiv.org/html/2312.04511v3),
[code](https://github.com/SqueezeAILab/LLMCompiler).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Parallel function calls; dependency DAG and placeholders |
| State / actions | Tools, history, executor observations; calls and finish/replan |
| Dynamic infra / locality | Network, device locality and load not modeled |
| Semantic change / full plan | Supports iterative replanning, not solely one-shot compilation |
| Cost / quality | Tokens/dollars, latency, benchmark correctness |
| Method / timing | Online streamed planning, readiness dispatch, result-conditioned replanning |
| Workloads / baselines | QA, MovieRec, ParallelQA, Game24, WebShop; ReAct, parallel calling, TPTU |
| Assumptions | Declared tools; curated tool access; benchmark-specific demonstrations |
| Overlap / collision | Parallel dynamic logical graphs already exist |
| Difference | No infrastructure-conditioned semantic consequence feedback |
| Reuse / baseline | Readiness dispatch; resource-oblivious conceptual comparator |

Reading: HTML main/appendices, published PDF references and pp. 19-22 prompts;
p. 20 visually inspected. Section 3.4 explicitly replans from observations.
Streaming analysis assumes timing relationships; it is not a general critical-path
formula for heterogeneous stragglers.

## 10. Flow: Modularized Agentic Workflow Automation

Authors: Boye Niu, Yiliao Song, Kai Lian, Yifan Shen, Yu Yao,
Kun Zhang, Tongliang Liu. ICLR 2025.
[Canonical](https://proceedings.iclr.cc/paper_files/paper/2025/hash/ba84da6921f3040b74ee163aa7451f53-Abstract-Conference.html),
[PDF](https://arxiv.org/pdf/2501.07834v2),
[HTML](https://arxiv.org/html/2501.07834v2),
[code](https://github.com/tmllab/2025_ICLR_FLOW).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Modular collaboration; activity-on-vertex DAG |
| State / actions | Status/results/global requirements; add/delete/edit/rerun/reassign tasks |
| Dynamic infra / locality | No measured deployment/network/locality optimization |
| Semantic change / full plan | Initial graph, then execution-result-driven revisions |
| Cost / quality | Execution time; task success and human ratings |
| Method / timing | LLM candidate graphs ranked by parallelism then degree dispersion |
| Workloads / baselines | Website, Gobang, slides; AutoGen, CAMEL, MetaGPT |
| Assumptions | Global inspection; generated roles; cloning parallel agents |
| Overlap / collision | Dynamic semantic graph refinement already established |
| Difference | Structural modularity, not physical action-consequence optimization |
| Reuse / baseline | Account for revision overhead; conceptual dynamic Blind comparator |

Reading: HTML main; PDF pp. 12-36, including all appendix algorithms/prompts and
proof; Figure 3 visually inspected. Evaluations wait for running tasks before
updates. Revision adds overhead; parallelism metrics are not measured speedup.

## 11. AFlow: Automating Agentic Workflow Generation

Authors: Jiayi Zhang, Jinyu Xiang, Zhaoyang Yu, Fengwei Teng, Xiong-Hui Chen,
Jiaqi Chen, Mingchen Zhuge, Xin Cheng, Sirui Hong, Jinlin Wang,
Bingnan Zheng, Bang Liu, Yuyu Luo, Chenglin Wu. ICLR 2025.
[Canonical](https://proceedings.iclr.cc/paper_files/paper/2025/hash/5492ecbce4439401798dcd2c90be94cd-Abstract-Conference.html),
[PDF](https://arxiv.org/pdf/2410.10762v3),
[HTML](https://arxiv.org/html/2410.10762v3),
[code](https://github.com/geekan/MetaGPT).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Automated workflows; code edges, LLM nodes, reusable operators |
| State / actions | Validation results and experience; code/prompt edits |
| Dynamic infra / locality | No runtime distributed resource/locality adaptation |
| Semantic change / full plan | Whole workflow searched offline; code can contain loops/conditionals |
| Cost / quality | Token dollars and benchmark scores; reported Pareto frontier |
| Method / timing | MCTS variant, LLM expansion, repeated validation and backpropagation |
| Workloads / baselines | Six QA/math/code benchmarks; manual approaches and ADAS |
| Assumptions | Validation evaluator; model/temperature/format fixed in primary search |
| Overlap / collision | Open code topology and semantic optimization already exist |
| Difference | Not online execution-grown resource-conditioned action quoting |
| Reuse / baseline | Explicit optimization overhead; conceptual offline-search comparator |

Reading: HTML plus PDF pp. 7-38; embedded optimizer prompt/code read, p. 15
visually inspected. Cost frontier is execution expense, not total search cost.
Open-ended-task appendix uses judges; not permission to expose our evaluator.

## 12. DynTaskMAS: A Dynamic Task Graph-driven Framework for Asynchronous and Parallel LLM-based Multi-Agent Systems

Authors: Junwei Yu, Yepeng Ding, Hiroyuki Sato. ICAPS 2025, 35(1), pp. 288-296;
DOI 10.1609/icaps.v35i1.36130.
[Canonical](https://ojs.aaai.org/index.php/ICAPS/article/view/36130),
[published PDF](https://ojs.aaai.org/index.php/ICAPS/article/download/36130/38284).
Code URL unverified.

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Adaptive collaboration; weighted dynamic task DAG |
| State / actions | Task progress, context, latency/utilization; graph changes and resource allocation |
| Dynamic infra / locality | Load-aware; distributed context and transfer weights, not explicit artifact-route estimates |
| Semantic change / full plan | Recursive initial decomposition and ongoing graph updates |
| Cost / quality | Computation/context-transfer estimates; performance, no benchmark-quality objective shown |
| Method / timing | Online priority scheduling, candidate configuration evaluation, greedy allocation |
| Workloads / baselines | Complexity/scaling tests and travel; serial comparator, four RTX3090 GPUs |
| Assumptions | Complexity/transfer estimators and candidate generator not fully specified |
| Overlap / collision | Dynamic graphs plus resource/context-transfer feedback already claimed |
| Difference | No demonstrated anonymous no-execution action quote to semantic Manager |
| Reuse / baseline | Computation/communication distinction; conceptual close systems comparator |

Reading: complete published PDF, Figure 1 visually inspected. Do not call it
resource-blind. A measured heterogeneous-link semantic-adaptation experiment
is not established by its aggregate throughput tables.

## 13. GPTSwarm: Language Agents as Optimizable Graphs

Authors: Mingchen Zhuge, Wenyi Wang, Louis Kirsch, Francesco Faccio,
Dmitrii Khizbullin, Jürgen Schmidhuber. ICML 2024, PMLR 235, pp. 62743-62767.
[Canonical](https://proceedings.mlr.press/v235/zhuge24a.html),
[published PDF](https://raw.githubusercontent.com/mlresearch/v235/main/assets/zhuge24a/zhuge24a.pdf),
[code](https://github.com/metauto-ai/GPTSwarm).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Modular agents/compositions as operation DAGs |
| State / actions | Task, evaluation utility; node prompts and inter-agent edges |
| Dynamic infra / locality | No deployment/link/artifact-locality feedback demonstrated |
| Semantic change / full plan | Optimizable graphs; predefined operations and candidate inter-agent edges |
| Cost / quality | Tokens/time; task reward and benchmark correctness |
| Method / timing | Edge REINFORCE; prompt demonstration optimization/UCB; online improvement claimed |
| Workloads / baselines | MMLU, crosswords, HumanEval, GAIA; IO, random/full graphs, debate, DyLAN |
| Assumptions | Evaluated rewards; fixed candidate nodes/edges, cycles rejected |
| Overlap / collision | Graph composition and online graph improvement already exist |
| Difference | No infrastructure-conditioned, no-execution action consequence feedback |
| Reuse / baseline | Separate optimization from inference cost; conceptual graph-optimization comparator |

Reading: all 25 published pages, including appendices; Figure 1 inspected.
GAIA demonstrates composition without node/edge optimization. Crosswords include
equal-density random comparisons. Do not portray the paper as purely offline,
or assume all reported improvements include search/training expense.

## 14. MasRouter: Learning to Route LLMs for Multi-Agent Systems

Authors: Yanwei Yue, Guibin Zhang, Boyang Liu, Guancheng Wan, Kun Wang,
Dawei Cheng, Yiyan Qi. ACL 2025, pp. 15549-15572.
[Canonical](https://aclanthology.org/2025.acl-long.757/),
[published PDF](https://aclanthology.org/2025.acl-long.757.pdf),
[code](https://github.com/yanweiyue/masrouter).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Query-conditioned MAS configuration; mode/role/model pools |
| State / actions | Query and semantic profiles; collaboration mode, agent count, roles, model routing |
| Dynamic infra / locality | No current deployment/queue/network/artifact-locality state demonstrated |
| Semantic change / full plan | Per-query configuration, not evidence-driven execution-grown revision |
| Cost / quality | API/token dollars; task correctness minus weighted cost |
| Method / timing | Cascaded variational controller and policy-gradient training; query-time routing |
| Workloads / baselines | MMLU, GSM8K, MATH, HumanEval, MBPP; GPTSwarm, AFlow, pruning, single-model routers |
| Assumptions | Finite profiles/modes; evaluated training tasks; agent-count ceiling |
| Overlap / collision | Joint collaboration/role/model quality-cost selection already exists |
| Difference | No action-level dynamic distributed consequence estimator |
| Reuse / baseline | Explicit training/inference accounting; conceptual finite-routing comparator |

Reading: all 24 published pages, including routing algorithm, task graphs,
cost tables and embedded profiles; Figure 2 inspected. Profiles include model
prices/benchmark capabilities, not measured current system state. More agents
can add substantial expense for marginal quality; not a new observation of ours.

## 15. Automated Design of Agentic Systems

Authors: Shengran Hu, Cong Lu, Jeff Clune. ICLR 2025.
[Canonical](https://proceedings.iclr.cc/paper_files/paper/2025/hash/36b7acf6f6010652b3f2a433774a66fe-Abstract-Conference.html),
[read PDF v2](https://arxiv.org/pdf/2408.08435v2),
[published PDF](https://proceedings.iclr.cc/paper_files/paper/2025/file/36b7acf6f6010652b3f2a433774a66fe-Paper-Conference.pdf),
[code](https://github.com/ShengranHu/ADAS).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Automated system design; Python forward functions |
| State / actions | Archive, validation scores/errors; code/prompt/workflow generation and refinement |
| Dynamic infra / locality | No measured current network/device/artifact-locality feedback |
| Semantic change / full plan | Whole agent program searched before deployment; programs may loop/decompose |
| Cost / quality | Main objective task performance; search expense reported separately |
| Method / timing | Offline meta-agent proposal, reflection, validation and archive updates |
| Workloads / baselines | ARC, DROP, MGSM, MMLU, GPQA; CoT, consistency, refinement, debate, OPRO |
| Assumptions | Validation evaluation; code execution; domain/model transfer tests |
| Overlap / collision | Open code-space agent/workflow design already exists |
| Difference | No online distributed action-consequence mechanism demonstrated |
| Reuse / baseline | Scope/counterexample-aware archive analysis; conceptual offline design comparator |

Reading: all 34 v2 pages, marked ICLR; Figure 1 inspected. Multi-objective and
online continual design are future work. Reported search/evaluation costs about
$300-$500 are not free optimization. Do not import its generated primitives,
runtime retries or validation access into our finite-tool online experiment.

## 16. A Declarative System for Optimizing AI Workloads / Palimpzest

Authors: Chunwei Liu, Matthew Russo, Michael Cafarella, Lei Cao, Peter Baille
Chen, Zui Chen, Michael Franklin, Tim Kraska, Samuel Madden, Gerardo Vitagliano.
2024 preprint; this entry concerns the specified early system, not Abacus.
[Canonical](https://arxiv.org/abs/2405.14696),
[read PDF v2](https://arxiv.org/pdf/2405.14696v2),
[code](https://github.com/mitdbg/palimpzest).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Semantic analytics; typed relational programs with convert |
| State / actions | Samples/statistics/preferences; reorder, model selection, synthesis, prompt packing, token reduction |
| Dynamic infra / locality | Dataset names initially local; current distributed link/locality adaptation not demonstrated |
| Semantic change / full plan | User logical program; equivalent logical/physical candidates before main execution |
| Cost / quality | Time/dollars; champion-model quality estimates, final labeled evaluation |
| Method / timing | Executed sentinel samples, candidate scoring, Pareto selection |
| Workloads / baselines | Legal discovery, real estate, medical schema matching; naive GPT-4/3.5/Mixtral |
| Assumptions | Declared dependencies; sample extrapolation and champion proxy |
| Overlap / collision | Logical/physical separation and quality-cost rewrites already exist |
| Difference | No no-execution quote to persistent semantic Manager |
| Reuse / baseline | Provenance/uncertainty; conceptual declarative optimizer comparator |

Reading: all 29 pages; Figure 1 inspected. Sentinel sampling executes work and
costs money. Reported parallel speedups compare against single-threaded baselines;
not pure optimizer gains. Failed conversions are dropped in this prototype,
unsuitable for our fail-closed contract.

## 17. DocETL: Agentic Query Rewriting and Evaluation for Complex Document Processing

Authors: Shreya Shankar, Tristan Chambers, Tarak Shah,
Aditya G. Parameswaran, Eugene Wu. PVLDB 18(9), pp. 3035-3048, 2025;
DOI 10.14778/3746405.3746426. Findings below concern the fully read v3 preprint.
[Canonical](https://arxiv.org/abs/2410.12189),
[read PDF v3](https://arxiv.org/pdf/2410.12189v3),
[published PDF](https://www.vldb.org/pvldb/vol18/p3035-shankar.pdf),
[code](https://github.com/ucbepic/docetl).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Complex document quality; YAML operator pipelines |
| State / actions | Prompts, samples/results; 13 directives synthesizing decomposition/aggregation/representation |
| Dynamic infra / locality | No measured network/device/artifact-locality adaptation demonstrated |
| Semantic change / full plan | Recursively rewritten full pipeline before primary execution |
| Cost / quality | Primarily accuracy; synthesized validators, sampled ratings/pairwise comparisons |
| Method / timing | Top-down opportunistic generation/validation; context-size heuristics |
| Workloads / baselines | CUAD, game reviews, declassified articles, Biodex, police case; LOTUS, Palimpzest, Aryn, NLP |
| Assumptions | LLM-judge reliability; dependent operator quality; samples may miss full-data limits |
| Overlap / collision | Semantic decomposition and representation are optimization objects already |
| Difference | No pre-execution system-cost quote to an online Manager |
| Reuse / baseline | Expose expansion/validation expense; conceptual quality-first rewrite comparator |

Reading: all 22 v3 pages, algorithms and embedded prompts; Figure 1 inspected.
Shared generation/validation bias is acknowledged. Truncation/retries occur in
this system, not allowed in ours. More accurate plans can cost more; optimization
expense must not disappear. Published-version changes remain unverified.

## 18. Optimizing Agentic Workflows using Meta-tools

Authors: Sami Abuzakuk, Anne-Marie Kermarrec, Rishi Sharma,
Rasmus Moorits Veski, Martijn de Vos. 2026 preprint; venue unverified.
[Canonical](https://arxiv.org/abs/2601.22037),
[read PDF v2](https://arxiv.org/pdf/2601.22037v2).
Code URL withheld in this original for double-blind review; unavailable here.

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Redundant reasoning; weighted trajectory-state graphs |
| State / actions | Historical tool sequences; merge equivalent states, extract deterministic composites |
| Dynamic infra / locality | No current device/link/artifact-locality conditioning demonstrated |
| Semantic change / full plan | Expanded tool set; agent still composes workflows online |
| Cost / quality | Calls/tokens/dollars/latency; benchmark success, not guaranteed equivalence |
| Method / timing | Offline expert-guided horizontal merging and greedy chain compression |
| Workloads / baselines | AppWorld, VisualWebArena; original ReAct tools; GPT-5.1, Claude, GPT-OSS |
| Assumptions | Representative traces; domain-specific equivalence and implementable composites |
| Overlap / collision | Trace-guided orchestration-overhead reduction already exists |
| Difference | Changes executable vocabulary, not anonymous consequence feedback |
| Reuse / baseline | Separate control overhead; conceptual tool-fusion comparator, not current variant |

Reading: all 17 pages; Figure 4 and appendix tables inspected.
Fewer calls need not reduce latency; GPT-OSS becomes less efficient.
Automated merge-rule verification remains unresolved. Main/appendix Claude call
counts differ. Do not import benchmark-specific merging or new primitives.

## 19. RouteLLM: Learning to Route LLMs with Preference Data

Authors: Isaac Ong, Amjad Almahairi, Vincent Wu, Wei-Lin Chiang, Tianhao Wu,
Joseph E. Gonzalez, M Waleed Kadous, Ion Stoica. ICLR 2025.
Proceedings use "from Preference Data" in the title.
[Canonical](https://proceedings.iclr.cc/paper_files/paper/2025/hash/5503a7c69d48a2f86fc00b3dc09de686-Abstract-Conference.html),
[read PDF v4](https://arxiv.org/pdf/2406.18665v4),
[published PDF](https://proceedings.iclr.cc/paper_files/paper/2025/file/5503a7c69d48a2f86fc00b3dc09de686-Paper-Conference.pdf),
[code](https://github.com/lm-sys/RouteLLM).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Quality-cost routing; independent query, binary strong/weak choice |
| State / actions | Query/preferences; predicted win probability and cost threshold select one model |
| Dynamic infra / locality | No current load/link/locality conditioning demonstrated |
| Semantic change / full plan | No tool graph; one selected generator per query |
| Cost / quality | Strong-call fraction/dollars; preference or benchmark quality; router overhead separate |
| Method / timing | Offline classifiers/factorization; similarity-weighted ranking solves online |
| Workloads / baselines | MT Bench, MMLU, GSM8K; random routing, commercial routers |
| Assumptions | Preference distribution coverage; strong/weak classes; short single-turn price assumptions |
| Overlap / collision | Quality-cost model routing is established |
| Difference | No execution-grown semantic changes or distributed action consequences |
| Reuse / baseline | Account control overhead; conceptual model-routing comparator |

Reading: all 16 pages; appendix curves inspected. Arena-only routers approach
random on MMLU/GSM8K; augmentation matters. Gold/judge training does not justify
a quality oracle in our estimator. Router throughput is not full-workflow latency.

## 20. FrugalGPT: How to Use Large Language Models While Reducing Cost and Improving Performance

Authors: Lingjiao Chen, Matei Zaharia, James Zou. Specified 2023 preprint;
official code identifies a later TMLR 2024 publication, not read as this version.
[Canonical requested original](https://arxiv.org/abs/2305.05176),
[read PDF v1](https://arxiv.org/pdf/2305.05176v1),
[later publication PDF](https://openreview.net/pdf?id=cSimKw5p6R),
[code](https://github.com/stanford-futuredata/FrugalGPT).

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Budget-constrained API use; learned model cascade |
| State / actions | Query and generated-answer reliability; accept or invoke next API |
| Dynamic infra / locality | Static API pricing; current links/load/locality not modeled |
| Semantic change / full plan | Offline cascade selected; conditional invocation online, not tool-workflow evolution |
| Cost / quality | Input/output/fixed request fees; supervised correctness-scoring regression |
| Method / timing | Budget-constrained chain/threshold optimization; pruning/interpolation; length three evaluated |
| Workloads / baselines | Headlines, Overruling, adapted CoQA; twelve APIs and best individual model |
| Assumptions | Labeled representative training data; amortized learning; scorer reliability |
| Overlap / collision | Quality-cost cascades and response-dependent selection established |
| Difference | No runtime distributed consequence interface; latency optimization future work |
| Reuse / baseline | Expose learning/inference expense; conceptual cascade comparator |

Reading: all 13 pages; Figure 2 inspected. Prompt adaptation/approximation are
broader proposed strategies, not all evaluated mechanisms. Reliability errors
can invoke every model unnecessarily. Do not import model substitution or a
correctness predictor. Later OpenReview access returned browser verification;
updated findings are not substituted for the specified original.

## 21. Adaptive Query Processing

Authors: Amol Deshpande, Zachary Ives, Vijayshankar Raman.
Foundations and Trends in Databases 1(1), pp. 1-140, 2007;
DOI 10.1561/1900000001.
[Canonical requested page](https://research.ibm.com/publications/adaptive-query-processing),
[author publication page](https://www.cs.umd.edu/~amol/pubs-qp.html),
[author-hosted original PDF](https://www.cs.umd.edu/~amol/papers/fnt-aqp.pdf).
This is the author's two-pages-per-sheet version: 70 physical PDF pages,
140 printed pages. Not the similarly titled two-page VLDB tutorial.
No single code repository verified for this survey.

| Field | Finding / comparison |
| --- | --- |
| Problem / representation | Uncertain query execution; relational plans, tuple routing, intermediate state |
| State / actions | Cardinalities, costs, memory/network, remote delays; reorder, reoptimize, bind, migrate state |
| Dynamic infra / locality | Remote-source delays and distributed routing explicitly considered |
| Semantic change / upfront plan | Runtime plan changes; not exclusively upfront optimization |
| Cost / quality | Response time, work, monitoring/planning/actuation overhead; relational correctness |
| Method / timing | Survey of online adaptive mechanisms and policies; not one learned optimizer |
| Workloads / baselines | Compares research systems; no single benchmark campaign |
| Assumptions | Valid routing/equivalence and controlled state reuse, varying by technique |
| Overlap / collision | Feedback loops, resource-sensitive adaptation and state reuse are established |
| Difference | No LLM answer-quality guarantee or semantic-agent consequence interface |
| Reuse / baseline | Account adaptation overhead/uncertainty; conceptual systems lineage |

Reading: all pages, including references. Figure 3.3 (printed36) and Table8.1
(119) inspected. Chapters6-8 distinguish routing history, intermediate reuse,
checkpoints and delay-triggered operator synthesis. Reoptimization can regress;
monitoring and switching are not free. Relational equivalence does not guarantee
quality after LLM evidence reduction. No competitive/optimality theorem is
transferred to our Agent.

## Original PDF provenance

Read-only research sources are downloaded/rendered on the 4090, not benchmark
data transferred through the development PC. Only selected small page images
are copied for visual inspection. Remote scratch:
`/home/super/xiaoming/cost-guidance-literature-gnhlgaeb`.

| Source | SHA-256 of downloaded original |
| --- | --- |
| CostBench, published ACL PDF | f226078662745d4c450fdb3fd1b5dd6f32326da7b99bff52752b96d232dbdf3f |
| Budget-Aware, arXiv v2 | 33de6a06ad58c90e5b3c526af1b750c1fae16a38b9dd2fc3cc4f23bbdb340333 |
| LLMCompiler, published PMLR PDF | 36dde899ed8abe0df728215e054aab21d1699add719afeb0ddadbb4e4eb23263 |
| Flow, arXiv v2 | 6c729ba58bc8beafb951adb8b27d247c1945804b1419b58f256053ddce6d75f7 |
| AFlow, arXiv v3 / ICLR-marked PDF | 8d18d9ce80b78ef6dd8e9e3974020a9f45f41a8ba2e3e95be7e3a66053c60bb1 |
| DynTaskMAS, published ICAPS PDF | 193d914347827c04f73ca7f3004f4ac23f82b1585d1dda445a7bacb738575482 |
| GPTSwarm, published PMLR PDF | 63aab69835f124fd1bee714a21433a696c4d8d36da9f7883e0b5b01b836fd6ed |
| MasRouter, published ACL PDF | 1bf45eaa68515ae2a6d3de2e2240ac321fef37a46ba831718aacee52bb12f457 |
| ADAS, arXiv v2 / ICLR-marked PDF | 32eb1c1a6888e35fae0f618e33c58698b54d9c49bc063fef91ee591719fca376 |
| Palimpzest, arXiv v2 | f853718e273a6330aa4fde3ce79fbe23bf457d90c18d4d1f009de2adaca5deaf |
| DocETL, arXiv v3 | dda098a6be8b61b4cad5096f05d1de43fcd01b0a81da03d8c33ec80cc3810601 |
| Meta-tools, arXiv v2 | 97f856b6c45a66870a9323359f260d8df8b8f66785b0ae96837b8672ccd140ff |
| RouteLLM, arXiv v4 / ICLR-marked PDF | c9bc9c8171cab95bb3832cde8767c6b5e0925cd62930e51ddbd60d7cb2616741 |
| FrugalGPT, specified arXiv v1 | 035ae8b90333dad8b7817fc8f55e7c4cbca435368c5c1a4dbf7bba9e5db87473 |
| Adaptive Query Processing, author-hosted two-up original | 9307f20bd31e92583f63279b32ae560f899fc080554551134785d9b0785ed48e |

Budget-Aware Poppler metadata-string warnings did not prevent inspected pages
from rendering; source warnings are not treated as failed experimental actions.

## Coverage limitations and next audit

All21 comparison entries now cover the requested fields. Code unavailable or
unverified is explicitly distinguished from a verified repository. Reading
coverage does not establish exhaustive related-work coverage. DocETL's published
version and FrugalGPT's later TMLR revision have not
been compared against the read originals; do not claim version equivalence.
Remaining visual checks are listed above. The novelty audit must use these
qualified findings, not infer missing functionality from a title or abstract.

## Murakkab published-version check,2026-10-04

The [OSDI PDF](https://www.usenix.org/system/files/osdi26-chaudhry.pdf),all22
physical pages including references/appendix,was read;Figure5/Table1 rendered.
SHA:`9c9aa888b675c7849467d5b594e640996fee57f32b79fc9cf443fb549587c0e0`.
Sections2.2/4.4 add dynamic coding with optional review and test-driven iterations;
Table1 distinguishes per-query graph construction,epoch optimization and runtime
dispatch. It is not fixed-DAG-only. Section3.3 profiles quality and solves MILP;
no equivalence to our per-ready-action non-executing distributed quote is established.
The earlier preprint-only limitation is closed,not a claim of version identity.
