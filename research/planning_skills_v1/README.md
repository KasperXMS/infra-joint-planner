# Planning capacity × procedural skills research

Active objective: [objective.md](objective.md). This independent namespace does not resume the paused historical pilot. The research is sequential and adaptive; `diagnostic-v1` is development evidence, not the final scope or held-out validation.

## Network and provenance

The AutoDL instance is in mainland China. ModelScope supplies the **official `Qwen/...` repositories**, rather than an unofficial re-quantization. The TUNA PyPI mirror is selected per installation command, without changing machine-wide indexes. Weight/config/tokenizer SHA256 manifests identify the bytes actually used. A mutable download revision is not falsely presented as a commit pin. Experiment inference is offline after materialization; no HF token or cloud API key is required.

Avoid `raw.githubusercontent.com` or Hugging Face as mandatory runtime dependencies. Transfer tracked source/configuration over SSH and retain a persistent evidence copy on the instance's shared storage. Public papers are read from arXiv HTML when PDFs/author GitHub are unavailable. Domestic transport does not justify substituting a different model or changing scientific conditions unnoticed.

## Preparation and bounded execution

The runtime guard records whole-instance CNY lease estimates and GPU/cgroup telemetry. It checkpoints small evidence every minute, marks a 10-hour soft target and applies a 20-hour hard stop including AutoDL shutdown. Model files and environments are not copied repeatedly. Owned processes are checked by PID **and process start identity** before termination; process groups are killed only when explicitly registered as our own isolated session.

The independent environment inherits tested PyTorch 2.8.0+cu128 and installs Transformers/ModelScope without replacing the base environment. `environment-freeze.txt` records resolved packages. `bootstrap.sh` and `prepare_models.py` provision models; `launch_prepare.py` uses an exclusive receipt to prevent an accidental duplicate launch.

## Reproduce the first diagnostic

```bash
python -m unittest discover -s research/planning_skills_v1 -p test_microbench.py -v
python research/planning_skills_v1/make_config.py --output /path/to/configs/diagnostic-v1.json
# Once official weights and their identity manifests exist in ROOT:
CUDA_VISIBLE_DEVICES=0 ROOT/.venv/bin/python research/planning_skills_v1/run_model.py \
  --root ROOT --config /path/to/configs/diagnostic-v1.json --model Qwen3.5-4B
CUDA_VISIBLE_DEVICES=1 ROOT/.venv/bin/python research/planning_skills_v1/run_model.py \
  --root ROOT --config /path/to/configs/diagnostic-v1.json --model Qwen3.5-9B
```

Replace `ROOT` with the absolute independent run directory. For the prepared instance, `launch_diagnostic.py` waits for each weight manifest and starts the two exclusive-GPU workers. Each model has four batched workflows, not four independently competing model services. No prefill or output is silently truncated. Stop by creating `ROOT/STOP`; do not run into an existing experiment namespace.

The backend is direct Transformers, BF16, SDPA, greedy generation, disabled thinking, output reservation 256 tokens, context 16,384, 48 turns and 3,600 seconds/task. Requests have a 300-second cooperative decoding stop; an in-flight GPU kernel cannot be preempted by that Python criterion. The task deadline is checked again before executing any returned action, so late output is retained but not executed. The independent resource guard remains the hard overall protection. These choices differ from historical Ollama/Q4 pilots and are disclosed. Raw generated tokens and strict JSON/schema failures are recorded, without repair or constrained decoding. Whole batch service time is counted once in `service-batches.jsonl`; overlapping per-request latency must not be summed and relabeled GPU work. Local monetary USD cost stays unknown; the known rental rate is tracked separately in CNY.

All task data in this new microbenchmark is synthetic. Reference solving is isolated to evaluation/tests, not action selection. The ledger projects only previously observed artifact fields and invalidation notices; no private values or policy answers are supplied. Completion and final answer correctness are separate. The verifier is a deterministic provenance/freshness tool, not the historical LLM Verifier.

## Current artifacts

- [Literature and novelty ledger](literature-novelty-ledger.md)
- [Research journal and next decisions](research-journal.md)
- `microbench.py`: parameterized tasks, strict actions, deterministic environment/evaluator
- `skills.py`: frozen generic full/local procedural rule bank and observation-only ledger
- `configs/diagnostic-v1.json`: first development design and task identities
- `run_model.py`: real inference, exact context preflight, raw traces, measured resource counters

Held-out configs, results, mechanism ablations and final research report will be added as the evidence-driven loop progresses. Their absence is not represented as research completion.
