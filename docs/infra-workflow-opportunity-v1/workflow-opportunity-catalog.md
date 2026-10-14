# Workflow opportunity catalog

The candidates below use named existing operators and retain the original
benchmark evaluator. Only the Video-MME 795-3 pair is executed in this
package; the other rows are design leads whose artifact schemas, retrieval
recall and end-to-end executability are not yet established. Quality
acceptability requires measured original task success and is never inferred
from structural validity.

| Task / candidate | Logical operations and information flow | Physical distinction | Risk / status |
| --- | --- | --- | --- |
| Video-MME 795-3, individual frames | `sample_frames(video, 8 at 5 s)` on source A4 → eight JPEG artifacts → `invoke_model` on existing image-capable pool → canonical choice | Eight image payloads move to selected physical model; scheduler unchanged | Prefix-only sampling misses later evidence; executable fixed workflow under test |
| Same task, contact sheet | Identical sampling → `make_contact_sheet(4×2, 640×360)` on A4 → one JPEG composite → same `invoke_model` requirement and prompt → canonical choice | One composite replaces eight individual payloads | Resizing can erase fine detail; executable fixed workflow under test |
| Video-MME 795-2, full-timeline sheets | `sample_frames` at wide cadence → multiple sheets → synthesis | More local decode and several reduced image transfers | Historical fast Blind correct, other conditions not; expensive and not selected post hoc |
| LongBench multidoc, per-document retrieval then synthesis | `bm25_retrieve` on compatible structured document records → reduced text artifacts → model synthesis | Source-local retrieval may reduce inter-agent traffic | Original text artifact schema may require a valid record conversion; recall and executability unverified |
| LongBench multidoc, full source/model | Original documents → `invoke_model` with complete context if preflight permits | Large model payload; may be context-limited | Capability-dependent; no controlled run in this package |
| MultiHop 609-document corpus, complete shards vs shard retrieval | Three information-equivalent source shards → full transfer or local BM25 candidates → synthesis | Distributed corpus traffic versus retrieval compute | Candidate recall is unverified; prior formal bridge has no live pending-suffix rewrite |

The primary tested pair differs in a real semantic operation (`make_contact_sheet`)
and the representation consumed by the model. It does **not** force placement:
the unchanged locality-aware scheduler selects feasible Workers. Both use the
same original video, task, eight sampled moments, prompt, output contract,
physical model requirement and evaluator. The sheet loses spatial resolution,
so it is a *candidate*, not a guaranteed semantically equivalent workflow.

The proposed "centralized raw video" topology is not a valid third condition
here: the resident physical model accepts text and image, not an intact MP4,
and the current action contract provides no video-model deployment. Moving
the same `sample_frames` action from A4 to A28 would change only physical
placement. Likewise, A4 has no equivalent resident visual model for a
source-local final inference. The sheet path is the executable local reduction
plus strong-model reasoning alternative. No synthetic operator or hidden
benchmark-specific video selector was added to force a three-way matrix.

Moving the exact same `sample_frames` and `invoke_model` actions to different
Workers is a physical placement alternative. So are the older heterogeneous
fixed-DAG results. Changing only action order when the information dependencies
are identical, or shortening a run through failure, offers no legitimate
logical optimization. A task-aware retrieval or visual reduction could be a
stronger alternative, but the present registry has no task-aware video
selection operator; inventing one in this experiment would change the action
space and confound comparison.
