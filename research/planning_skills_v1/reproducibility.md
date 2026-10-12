# Reproducing the selected studies and their evidence

Use a new namespace. Historical pilot results stay preserved and the historical v2 remains paused. This research uses supplied synthetic dependency graphs and real local inference with deterministic tools; its verifier is a provenance/freshness tool, not the historical LLM Verifier or Physical Executor.

## Environment and model bytes

Observed target: Ubuntu 22.04.5, Python 3.12.3, PyTorch **2.8.0+cu128**, torchvision 0.23.0+cu128, Transformers 5.19.0, two RTX 5090 GPUs with driver 595.71.05. The container allocation is 180 GiB RAM / 50 CPU cores. Other PyTorch/CUDA combinations have not been validated by this study.

[Observed constraints](constraints-observed.txt) record all 176 distribution versions; [selected requirements](requirements-inference.txt) pin 14 runtime/analysis packages. Constraints do not install unused notebook/Conda packages. The [active-environment receipt](evidence/runtime-environment-active-workers-v1.json) identifies the actually observed environment, offline flags and missing optional fast kernels. These are version records, not wheel hashes or a claim that every future platform reproduces the same image. The correct reference PyTorch kernels were used without `causal_conv1d`/`fla`.

The [model identities](evidence/model-identities.json) contain SHA256 and byte lengths for all 26 actual checkpoint/config/tokenizer files, totaling 9,342,816,767 bytes for 4B and 19,329,302,955 for 9B. Weights are official ModelScope `Qwen/Qwen3.5-4B` and `Qwen/Qwen3.5-9B`, BF16 without quantization. `master` was the requested download revision; it is mutable and is **not** an upstream commit pin. A fresh download must match the published hashes before it represents the same model. Otherwise retrieve a matching historical revision or copy the original checkpoint files; report any different model bytes as a different experiment.

Preparation actually used TUNA PyPI and the official ModelScope repositories. For a fresh environment inheriting the observed GPU PyTorch base:

```bash
export PLANNING_REPRO_ROOT=/absolute/path/to/a/new/research-run
export PLANNING_REPRO_BACKUP=/absolute/path/to/a/new/persistent-backup
export PLANNING_SOURCE=/absolute/path/to/repository/research/planning_skills_v1
export PLANNING_PYTHON=/root/miniconda3/bin/python
test ! -e "$PLANNING_REPRO_ROOT"
"$PLANNING_PYTHON" -c 'import torch,torchvision; assert torch.__version__=="2.8.0+cu128"; assert torchvision.__version__=="0.23.0+cu128"'
mkdir -p "$PLANNING_REPRO_ROOT/code" "$PLANNING_REPRO_ROOT/configs"
nohup "$PLANNING_PYTHON" "$PLANNING_SOURCE/runtime_guard.py" \
  --root "$PLANNING_REPRO_ROOT" --backup "$PLANNING_REPRO_BACKUP" \
  > "$PLANNING_REPRO_ROOT/guard.log" 2>&1 &
"$PLANNING_PYTHON" -m venv --system-site-packages "$PLANNING_REPRO_ROOT/.venv"
"$PLANNING_REPRO_ROOT/.venv/bin/python" -m pip install \
  --index-url https://pypi.tuna.tsinghua.edu.cn/simple/ \
  --constraint "$PLANNING_SOURCE/constraints-observed.txt" \
  --requirement "$PLANNING_SOURCE/requirements-inference.txt"
```

These commands target an operator-provided, dedicated replication instance; the guard's hard limit invokes its whole-instance AutoDL shutdown. They do not provision another paid instance. The guard starts before dependency installation so preparation counts toward the resource limit; its original CNY rate must be updated in a new run's budget record if that instance has a different actual lease. Reusing the available compatible CUDA base avoids assuming domestic PyPI mirrors serve the exact GPU PyTorch wheels. For an offline environment, materialize the matching dependencies/checkpoints first through an accessible trusted source or SSH. The historical `bootstrap.sh` records original broad-range preparation and its original root; the pinned files above document the resolved environment rather than rewriting that history. A second fresh-instance installation has not been executed as an additional experiment.

## Frozen configurations and source

The `configs` directory preserves frozen task IDs, values, order, budgets and sampling. `.gitattributes` preserves configuration JSON bytes; compare raw bytes, not a pretty-printed JSON rewrite. Actual model-stage manifests bind config/source/weight identities. Changing only an installation path in a new identity file is deployment metadata; matching checkpoint hashes still defines model equality.

The public initial source archive [frozen-inference-source.tar.gz](evidence/frozen-inference-source.tar.gz) and [SHA index](evidence/frozen-source-index.json) preserve executed development/primary snapshots. Later transfer/probe snapshots are created before their execution and retained with raw evidence; the complete final evidence index identifies them. Use the matching stage's `frozen-source` for byte-accurate historical replay. Current Git also includes later analysis/export utilities; an unused added utility changes an overall source-manifest hash without necessarily changing an inference prompt. Never claim whole-source identity solely from equal filenames or a Git branch name.

| Stage | Frozen population | Inference/interpretation |
| --- | --- | --- |
| diagnostic-v1 | Interrupted first development cohort | Engineering-invalidated chat-EOS framing; retained expenses/raws, excluded from ability evidence |
| diagnostic-v2 | 8 tasks × 4 conditions × 2 models = 64 workflows | Corrected complete repeat, batch 4, 48 turns |
| role-placement-v1 | Same 8 development tasks × 3 placements × 2 models = 48 workflows | Reused tasks; placement ablation, batch 4, 48 turns |
| decision-context-probe-v1 | 48 observed decisions × 3 contexts × 2 models = 288 requests | Development conditional decisions; zero model-directed tool executions |
| heldout-binding-v1 | 12 new graphs / 36 variants × 7 conditions × 2 models = 504 workflows | Independent primary policy templates/seeds, batch 2, 64 turns |
| structural-transfer-v1 | 16 new graphs / 48 variants × 4 conditions × 2 models = 384 workflows if triggered | Opaque names/shuffled public order, same mechanisms, batch 2, 64 turns |
| decision-generalization-v1 | 338 observed first node/phase decisions × 3 contexts × 2 models = 2,028 requests | Post-hoc diagnostic, 11 observed/12 source graph clusters; zero model-directed tool executions |

All valid stages use greedy, thinking-disabled, direct BF16 Transformers/SDPA, 16,384 actual-token context budget, 256 output tokens and a 300-second cooperative request deadline. Workflows also have 3,600-second task deadlines. Each actual frozen config is authoritative. These settings differ from historical Ollama Q4_K_M pilots; cross-study scores are not a controlled backend or parameter-scale comparison.

## Running a fresh replication

Materialize matching source under `NEW_ROOT/code`, exact configs under `NEW_ROOT/configs`, and matching model identity files under `NEW_ROOT`. Adapt local checkpoint paths in the new identity records. Keep all model/skill/prompt/config bytes fixed within a study. The two assigned GPUs must be isolated; inference workers record PID/start identities and refuse an existing stage manifest.

```bash
NEW_ROOT="$PLANNING_REPRO_ROOT"
NEW_PY="$NEW_ROOT/.venv/bin/python"
export HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1
export OMP_NUM_THREADS=8 TOKENIZERS_PARALLELISM=false

# Keep the already started guard and its original preparation start epoch.
"$NEW_PY" "$NEW_ROOT/code/launch_experiment.py" \
  --root "$NEW_ROOT" --config "$NEW_ROOT/configs/heldout-binding-v1.json"
```

The launcher runs one model on each GPU and a real tensor batch within each model. It is not multiple competing model services. Run `postprocess_when_complete.py --root NEW_ROOT --experiment heldout-binding-v1` once to collect the complete primary replay. `launch_conditional_transfer.py --root NEW_ROOT` implements the original predeclared trigger/handoff; it can wait while primary inference continues. Original receipts show that both completed primary models triggered the entire transfer design. A fresh replication must record its own trigger decision and any greedy/batching differences, rather than force an outcome to match the original.

The generalization diagnostic uses the original private query config from the evidence archive to replay those exact observed decisions. Regenerating it from a new primary run creates a different query pool/config SHA and must be labeled accordingly. `make_generalization_probe.py` reconstructs original queries from their indexed source traces. Start `launch_queued_probe.py` from its isolated frozen source directory only after the transfer workers have been registered; it waits for each corresponding worker to exit and release CUDA. The queue does not inspect transfer scores. Individual probe requests execute no tools and allow no retries.

System-integrity failures STOP subsequent inference; wrong answers, schema errors and legal exhaustion remain recorded results. Create `NEW_ROOT/STOP` for a cooperative stop. The request stop cannot preempt an already running GPU kernel; the independent whole-instance guard remains the hard 20-hour protection. Restarting an observation connection is not authorization to restart a model run. Existing model execution results are never selectively rerun.

## Replay and accounting

`analyze.py` replays numeric tool/evaluator outcomes. `audit_frozen_prompts.py` independently checks prompt SHA, token counts, decoded raw outputs and tool observations; matched support inventories are checked where applicable. The primary original once-only audit remains unchanged. `finalize_analysis.py` adds policy-provenance diagnostics in a new directory and proves all non-corrected original per-episode fields unchanged. It preserves numeric success for arithmetic collisions instead of silently changing the evaluator.

`audit_legacy_development.py` loads actual historical frozen core modules to check the original diagnostic/probe data. The development support function's older two-argument signature receives its original arguments; its text/metadata are not replaced by later renderers. The already completed 776-call placement audit is retained, not repeated. `audit_generalization_probe.py` runs once after the new diagnostic, reconstructs exact prompts/scores, derives labels independently from public policy text and reports observed-state coverage.

For a separately versioned final diagnostic replay, with the completed original stage and its audit preserved:

```bash
"$NEW_PY" /path/to/final-analysis-source/finalize_analysis.py \
  --root /path/to/results/heldout-binding-v1 \
  --output /path/to/a/new/analysis-directory
```

Output paths are exclusive. The replay uses no model inference; exact tokenization audits additionally require the matching local tokenizer. `publish_tables.py` exports audited synthetic metadata while retaining raw actions/decision values privately. `plot_results.py` produces standalone PNG/SVG figures from validated result rows. `summarize_resources.py` counts physical batches once and includes engineering/setup work; mixed-condition batch wall is not GPU kernel time or a per-condition monetary allocation. Local GPU USD stays unknown; the user-provided whole-instance lease is estimated separately in CNY.

Final-only `make_evidence_index.py` refuses incomplete ability cohorts/unified audits and exports a byte-exact private archive plus a public hash/index. Interrupted engineering evidence is explicitly included. Raw evidence stays on the experiment machine/shared storage, with a copy outside Git in the user's first workspace. Models, caches, root download logs, credentials and device-info are excluded. Compare the archive SHA after transfer and verify its member hashes against the public index before final cleanup. A running/queued study is not proof of completed research; final findings and recommendations require its actual finished output.

`finalize_research_artifacts.py` is a separately frozen CPU-only convenience controller for this original run. It waits for both models' completion and the unified pass receipts in all three selected final studies, keeps the primary's existing versioned analysis, then invokes the isolated final-analysis source on transfer. It performs the once-only checkpoint-byte recheck, resource summary and private evidence export, and extracts a public source-only archive with exact member verification. It does not run inference, generate a final interpretation, publish raw traces or shut the instance down. Its readiness check rejects incomplete audits; partially written receipts are observed again rather than treated as failed execution. Final archive transfer/member verification, reporting and cleanup remain explicit required work.
