# Planning capacity × procedural skills research

Active objective: [objective.md](objective.md). This independent namespace does not resume the paused historical pilot. The research is sequential and adaptive. `diagnostic-v1` was invalidated by a chat-EOS decoding error and is retained as engineering evidence only; `diagnostic-v2` repeats the entire development design after that correction.

Completed development: 64 corrected workflows, 48 role-placement workflows, and 288 one-step context/decision probes. The latter are not workflow TSR. The frozen [held-out study](heldout-protocol.md) contains 504 workflows across 12 graph clusters, seven support conditions and both models. It uses batch two per GPU and 64 turns. Frozen configs and manifests define each stage; the first-stage budgets below do not describe every later stage.

## Network and provenance

The AutoDL instance is in mainland China. ModelScope supplies the **official `Qwen/...` repositories**, rather than an unofficial re-quantization. The TUNA PyPI mirror is selected per installation command, without changing machine-wide indexes. Weight/config/tokenizer SHA256 manifests identify the bytes actually used. A mutable download revision is not falsely presented as a commit pin. Experiment inference is offline after materialization; no HF token or cloud API key is required.

Avoid `raw.githubusercontent.com` or Hugging Face as mandatory runtime dependencies. Transfer tracked source/configuration over SSH and retain a persistent evidence copy on the instance's shared storage. Public papers are read from arXiv HTML when PDFs/author GitHub are unavailable. Domestic transport does not justify substituting a different model or changing scientific conditions unnoticed.

The ModelScope SDK's supported `MODELSCOPE_DOWNLOAD_PARALLEL_WORKERS=8` enables range streams for large files. `resume_parallel_download.py` documents the one-time pre-inference migration of existing single-stream prefixes to the SDK's resumable parts, rather than redownloading them. File sizes are checked against official repository metadata and actual completed weight/config/tokenizer bytes are hashed. These transport settings are unrelated to inference concurrency.

## Preparation and bounded execution

The runtime guard records whole-instance CNY lease estimates and GPU/cgroup telemetry. It checkpoints small evidence every minute, marks a 10-hour soft target and applies a 20-hour hard stop including AutoDL shutdown. Model files and environments are not copied repeatedly. Owned processes are checked by PID **and process start identity** before termination; process groups are killed only when explicitly registered as our own isolated session.

The independent environment inherits tested PyTorch 2.8.0+cu128 and installs Transformers/ModelScope without replacing the base environment. `environment-freeze.txt` records resolved packages. `bootstrap.sh` and `prepare_models.py` provision models; `launch_prepare.py` uses an exclusive receipt to prevent an accidental duplicate launch.

## Reproduce a frozen stage

```bash
python -m unittest discover -s research/planning_skills_v1 -p test_microbench.py -v
# Copy the committed frozen config into a NEW run root's configs directory.
# Once official weights and identity manifests exist in ROOT:
ROOT/.venv/bin/python research/planning_skills_v1/launch_experiment.py \
  --root ROOT --config ROOT/configs/heldout-binding-v1.json
ROOT/.venv/bin/python research/planning_skills_v1/postprocess_when_complete.py \
  --root ROOT --experiment heldout-binding-v1
```

Replace `ROOT` with the absolute independent run directory and materialize the matching source under `ROOT/code`. `launch_experiment.py` waits for each model identity and starts the two exclusive-GPU workers. Development used four batched workflows per model; held-out uses two. These are actual tensor batches within one model per GPU, not independently competing model services. No prefill or output is silently truncated. Stop by creating `ROOT/STOP`; do not run into an existing experiment namespace. Historical source snapshots and their SHA256 index are preserved in `evidence/frozen-inference-source.tar.gz`.

The backend is direct Transformers, BF16, SDPA, greedy generation, disabled thinking, output reservation 256 tokens, context 16,384, 48 turns and 3,600 seconds/task. Requests have a 300-second cooperative decoding stop; an in-flight GPU kernel cannot be preempted by that Python criterion. The task deadline is checked again before executing any returned action, so late output is retained but not executed. The independent resource guard remains the hard overall protection. These choices differ from historical Ollama/Q4 pilots and are disclosed. Raw generated tokens and strict JSON/schema failures are recorded, without repair or constrained decoding. Whole batch service time is counted once in `service-batches.jsonl`; overlapping per-request latency must not be summed and relabeled GPU work. Local monetary USD cost stays unknown; the known rental rate is tracked separately in CNY.

All task data in this new microbenchmark is synthetic. Reference solving is isolated to evaluation/tests, not action selection. The ledger projects only previously observed artifact fields and invalidation notices; no private values or policy answers are supplied. Completion and final answer correctness are separate. The verifier is a deterministic provenance/freshness tool, not the historical LLM Verifier.

## Current artifacts

- [Literature and novelty ledger](literature-novelty-ledger.md)
- [Research journal and next decisions](research-journal.md)
- [Completed development findings and resource tables](development-findings.md)
- [Completed primary held-out findings](heldout-findings.md)
- [Frozen held-out protocol](heldout-protocol.md)
- [Mechanism scope and closest prior work](mechanism-scope.md)
- [Mainland deployment details](mainland-reproducibility.md)
- `microbench.py`: parameterized tasks, strict actions, deterministic environment/evaluator
- `skills.py`: frozen generic full/local procedural rule bank and observation-only ledger
- `configs/diagnostic-v1.json`: first development design and task identities
- `run_model.py`: real inference, exact context preflight, raw traces, measured resource counters

The held-out study is running. Its outcome will determine independent transfer/remaining mechanism tests; launching a matrix does not constitute research completion. `analyze_heldout.py` performs deterministic trace replay and paired graph-cluster analysis; `audit_frozen_prompts.py` reconstructs exact prompts/token counts and support facts once after the batch, without inference. `summarize_resources.py` includes preparation and engineering work; `plot_results.py` renders standalone scientific figures from validated real results.

`finalize_analysis.py` applies the documented policy-provenance diagnostic correction to a completed study into a **new** analysis directory. It retains the initial summary and exact-prompt audit, verifies every original per-episode field outside the explicitly corrected diagnostics is unchanged, and performs no model calls. Example after the original postprocessing passes: `python finalize_analysis.py --root ROOT/results/heldout-binding-v1 --output ROOT/results/heldout-binding-v1/analysis-v2`. Run each study in a separate process so its explicit task constructor remains isolated. The frozen numeric success evaluator is unchanged, including numerically correct outputs that happen to use an incorrect operation.
