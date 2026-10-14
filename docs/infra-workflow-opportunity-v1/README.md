# InfraMAS workflow opportunity v1

**Result:** On original Video-MME 795-3, both fixed logical workflows passed
the unchanged evaluator under both network states (4/4 cells). The local
contact-sheet workflow was faster by 157.554 s at 100 Mbps and 3.464 s at
3 Mbps, so no workflow preference reversal was observed. Repeated exact
evidence/prompt requests showed a large unmeasured serving warm/cache-state
effect. The Adapter decision is [No-Go](infra-aware-adapter-go-no-go.md).
Separate request-level Verifier v2.1 validation reached 8/8 valid final
decisions in 12 provider attempts.

The controlled comparison uses source commit `ee5c044` and branch
`infra-workflow-opportunity-v1`. [Source/task/model hashes](../../results/infra-workflow-opportunity-v1/source-task-model-manifest.json),
the [fixed experiment definition](../../configs/experiments/infra-workflow-fixed-v1.json),
and the [redacted Verifier request result](../../results/infra-workflow-opportunity-v1/verifier-live-public.json)
are committed. Raw task data, cloud requests, API credentials and full traces
remain on the experiment controller under a separate namespace.

On a controller with the same original source mounts, four existing Worker
hosts, serving deployment and `tc` sudo permissions, prepare a **new**
experiment root and point the config to its own unused Worker ports/stores.
The script deliberately refuses to overwrite old evidence:

```bash
PYTHONPATH=src .venv/bin/python scripts/infra_workflow_fixed_v1.py \
  --root /home/super/xiaoming/infra-workflow-opportunity-v1 \
  --config configs/experiments/infra-workflow-fixed-v1.json \
  --attempt transport-fix-1 --prepare
PYTHONPATH=src .venv/bin/python scripts/infra_workflow_fixed_v1.py \
  --root /home/super/xiaoming/infra-workflow-opportunity-v1 \
  --config configs/experiments/infra-workflow-fixed-v1.json \
  --attempt transport-fix-1
PYTHONPATH=src .venv/bin/python scripts/analyze_infra_workflow_fixed_v1.py \
  --root /home/super/xiaoming/infra-workflow-opportunity-v1 \
  --attempt transport-fix-1 \
  --output /home/super/xiaoming/infra-workflow-opportunity-v1/controlled-public.json
```

The first two commands are the exact frozen condition. An independent rerun
requires a fresh root, unique attempt and unused ports, with the root guard
updated before a new freeze; it must not overwrite this study. The sanitized
analysis script reads only the existing results and can be rerun read-only.

The cloud Verifier request-only test is independent:
`scripts/infra_workflow_verifier_live_v1.py --help` describes its historical
context root, case manifest and metadata-only output. Access to the original
private contexts and endpoint credential is required. No raw task or provider
body should be copied to a public repository.
