# Controlled fixed-workflow experiment

The preregistered task is original Video-MME `video_mme:795`, question `795-3`,
with the intact 282,442,048-byte MP4 and unchanged private choice evaluator.
The controller checks the original source SHA-256 before any cell. It runs a
single deterministic fixed Manager policy through the unchanged control-plane
runner and physical scheduler. There are no cloud Manager, Specialist or
Verifier calls in this fixed-workflow condition; their costs cannot be
silently compared with an adaptive Agent run. The real A28 physical visual
model, media operators, Workers and evaluator remain active.
The remote frozen source/Worker manifest has 11 component hashes, all of
which match this branch's `ee5c044` base files. The A28 resident Ollama tag
digest and 32K runner context were checked read-only during the matrix and
are recorded in the model manifest.

The two logical strategies are frozen in
[`infra-workflow-fixed-v1.json`](../../configs/experiments/infra-workflow-fixed-v1.json):
both sample the first eight video frames at a five-second cadence. `frames`
sends the eight separate JPEGs into one visual model call; `sheet` first
executes the existing `make_contact_sheet` operator on A4, then sends the
resulting 4×2 composite to the same model requirement. The task prompt,
choice set and terminal contract are identical. Sampling and sheet actions
declare their artifact outputs and explicit dependencies. Different image
representation is the only intended logical factor; both representations
may lose original video information, and the sheet may lose detail further.

The sampled-frame digest and physical-model prompt digest are identical in
all four cells; the contact-sheet digest is also identical across network
states. The direct-frame pair reports exactly 7,512 input tokens in both
states, and the sheet pair reports 1,943 in both states. Thus the slow runs
did not use different task content or evidence. Model-service time nevertheless
changes sharply across execution order; the cost report treats serving
cache/warm state as an uncontrolled limitation.

The infrastructure factor is fast 100 Mbps/configured 5 ms versus slow
3 Mbps/configured 50 ms. Each of the four fixed cells uses a fresh Worker
process and artifact store in the independent
`/home/super/xiaoming/infra-workflow-opportunity-v1` namespace. A separate
`tc` wrapper records original, applied and restored queue disciplines. The
batch order was frozen as fast-frames, fast-sheet, slow-frames, slow-sheet;
one actual execution per cell completed. The original source, output
contract, evaluator, physical scheduler, model pool and serving settings are
unchanged. The `tc` setup and Worker startup happen before task E2E timing;
mandatory source materialization happens inside it.

An initial orchestration attempt failed **before Worker startup or model
execution** because the existing `tc` wrapper read the master JSON instead
of the generated cell YAML (`KeyError: network`). Its empty attempt directory
and queue event are preserved. The transport-only correction passes the cell
YAML to the existing wrapper and retains the master freeze separately under
condition `transport-fix-1`. No sampled answer or model result was available
to influence the correction; no executed cell is rerun.

The final matrix is 4/4 completed, 4/4 valid outputs and **4/4 original
task successes**. Times are seconds; task E2E includes original video staging.

| Condition | Original score | E2E | Source staging | Action transfer bytes / time | Model service | Model input/output tokens |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Fast, individual frames | 1 | 240.690 | 24.584 | 1,230,240 / 0.904 | 210.982 | 7,512 / 2 |
| Fast, contact sheet | 1 | 83.136 | 24.633 | 452,899 / 0.264 | 54.513 | 1,943 / 2 |
| Slow, individual frames | 1 | 801.393 | 788.944 | 1,230,240 / 4.815 | 3.416 | 7,512 / 2 |
| Slow, contact sheet | 1 | 797.929 | 788.584 | 452,899 / 1.411 | 3.274 | 1,943 / 2 |

All four runs used A4 for media operations and A28 for one physical model
inference. The sheet workflow adds one local `make_contact_sheet` call. The
fixed Manager made three or four deterministic decisions; Specialist and
Verifier calls were zero by policy. No cloud API was called in these four
cells. Worker cleanup and exact `tc` restoration passed in every cell; the
batch process exited zero and no own Worker ports remained listening. The
complete sequence took about **62.2 minutes wall time**, including repeated
network configuration and Worker startup; the sum of measured task E2E was
32.05 minutes. These setup costs are outside the task timing boundary.

Per-action metrics, SHA-256 trace indexes and scores are in the
[sanitized result](../../results/infra-workflow-opportunity-v1/controlled-public.json).
Sensitive original traces remain on the controller. The initial pre-Worker
configuration failure and all four effective attempts are separately retained
there; no model result was selectively retried.
