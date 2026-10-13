# Focused offline test record

Run on 13 October 2026 against audit baseline `ee7166343539cf8696dfccdd21f71dd7d92839f6`; no LLM API, GPU service, benchmark evaluator or production Harness changes. Python used the repository `.venv` with `openai-agents==0.20.0`. Upstream source repositories were inspected, not executed.

Command:

```powershell
.venv\Scripts\python.exe -m pytest -q docs/harness-architecture-audit-v1/harness-focused-tests/test_architecture.py tests/test_native_agents.py tests/test_adaptive_workflow.py tests/test_file_artifact_store.py
```

Result: **81 passed** (4 audit characterization cases and 77 existing cases). Ruff check of `test_architecture.py`: **passed**. The test names are the evidence index:

| Test | Observed result | Meaning / limit |
|---|---|---|
| `test_parallel_gateway_exception_loses_successful_sibling_commit` | Success effect occurs; gateway exception leaves output unknown and action ID reserved | Definite in-process reconciliation defect on real-service gateway branch. No claim of historical frequency. |
| `test_verifier_complete_has_no_candidate_binding_and_selects_latest` | Verifier reason names first `A`; final uses latest `B` | Definite candidate-binding contract gap with deterministic fake verdict. Does not prove a production LLM made this precise semantic mistake. |
| `test_execution_graph_omits_inline_observation_dependency` | Prompt uses an earlier inline excerpt but graph lacks an edge | Graph describes declared artifact/control edges; unstructured information lineage is incomplete by construction. |
| `test_installed_sdk_agent_tool_failure_is_plain_text` | Nested SDK `Runner` exception becomes a plain tool-result string | Confirms deployed SDK behavior. InfraMAS wrapper's subsequent missing typed failure is established by source inspection, not a full native Runner trace. |

The first run of these new tests revealed two **test fixture mistakes** (passing one action instead of a tuple to `ExecutionGrownGraph.add`, and using `RunContextWrapper` where SDK tool callback expects `ToolContext`). Those mistakes were corrected in the independent tests. No production code was changed and no failed benchmark cell was rerun. Existing tests cover strict schema failure/recovery, Specialist handoff, terminal ownership, synthesis phase, semantic KEEP/PATCH and artifact storage; passing them confirms current intended behavior, not the absence of the identified design gaps.
