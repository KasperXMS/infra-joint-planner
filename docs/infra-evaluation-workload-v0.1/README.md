# InfraMAS Evaluation Workload v0.1

The [decision](next-phase-decision.md) is P0 Go for two original text/text+table benchmarks, P1 No-Go for full isolation, and P2 No-Go. The [dataset audit](dataset-audit.md), [selection](task-selection.md), [dependency audit](source-dependency-analysis.md), [placement](data-placement-design.md), [data model](distributed-data-model.md), [environment](environment-architecture.md), [operator map](operator-compatibility.md), [network/cost](network-and-cost-accounting.md), [eight valid probes](environment-feasibility-results.md) and [future W0/W1 contracts](workflow-feasibility-contracts.md) are the complete v0.1 report set.

## Reproduction

From this branch, install Python 3.12 and `uv sync --extra dev`. Obtain original release files with the exact hashes in [the preparation receipt](manifests/preparation-receipt.json): MultiHop `corpus.json` / `MultiHopRAG.json` and MultiModalQA `MMQA_dev.jsonl.gz`, `MMQA_texts.jsonl.gz`, `MMQA_tables.jsonl.gz`. Keep these outside Git. Prepare a **fresh empty** public directory and a separate private directory:

```bash
PYTHONPATH=src .venv/bin/python scripts/prepare_infra_evaluation_workload_v01.py \
  --multihop-corpus /private/corpus.json \
  --multihop-questions /private/MultiHopRAG.json \
  --mmqa-dataset /private/multimodalqa/dataset \
  --public-root /scratch/infra-evaluation-workload-v0.1/manifests \
  --private-root /private/infra-evaluation-workload-v0.1
```

Compare generated public manifests with the committed [`manifests/`](manifests/) directory. The private root contains source Worker `FileArtifactStore` blobs and `evaluator-private.jsonl`; it must never be committed. The retained candidate context subset includes benchmark-provided distractors. On the original two physical hosts, provision a unique study directory, deploy the code and corresponding owner blobs, create a random shared `source-token` file readable only by study services, and use the two [Worker configurations](../../configs/experiments/infra-evaluation-source-a-v01.yaml) and [source-b configuration](../../configs/experiments/infra-evaluation-source-b-v01.yaml). Check port ownership before starting. The [launch](../../scripts/launch_evaluation_source_worker_v01.sh), [probe](../../scripts/probe_evaluation_workload_v01.py), [network proxy](../../scripts/evaluation_source_link_v01.py), [calibration](../../scripts/calibrate_evaluation_link_v01.py), [probe cleanup](../../scripts/cleanup_evaluation_probe_v01.py) and [service stop](../../scripts/stop_evaluation_services_v01.sh) scripts reproduce the bounded physical checks. Do not point them at historical Worker stores or shared traffic-control rules.

The initial invalid multi-answer probe and corrected replacement are separately retained; [final sanitized probe results](feasibility-public.json) contain exactly eight valid tasks. The full private evaluator file, source payloads, token, and raw service logs are retained at `/home/super/xiaoming/infra-evaluation-workload-v0.1` and A4 `/mnt/ssd/infra-evaluation-workload-v0.1`, outside Git. Source data remain resident; study Worker/proxy processes were stopped after validation.
