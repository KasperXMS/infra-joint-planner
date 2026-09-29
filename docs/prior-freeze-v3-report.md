# Prior Freeze Revision 3 Audit

## Scope and validation

This revision only removes model-quality-tier selection from the formal path's
LLM-facing prior and adapter contracts. It does not change the workflow
formulation, scheduler, cost or network model, benchmark, task, or 2x2 design.

- Branch: `open-ended-mas-preliminary-v1`
- Execution commit: `c3c180d29313a77ebec7961d5036ade3316b7e6e`
- Generator version: `llm-prior-v3`
- Pre-call validation: 286 tests passed; Ruff passed; strict Pyright passed;
  `git diff --check` passed.

## Revision-3 prior result

| Field | Result |
|---|---|
| Task | `multihop-multisource` |
| Source task ID | `multihop-rag-train-9bae0079038050a37a1ae583` |
| Generator/model | `workflow-formal-preliminary-2x2-v1-prior` / `deepseek-chat` |
| Backend calls | **1** |
| Attempt ID | `20260929T222546551722Z-f19f3017aed8` |
| Prompt SHA-256 | `e6bfd711234eda89542d614983ea413a345a251875fd84a37e9e3e31530e8c98` |
| Raw completion persisted | Yes, before parse/validation; 4,136 bytes |
| Draft parse | Passed |
| Draft SHA-256 | `5b56d403bda1055698b44702bea4deb061106ca08f6820431f9af6ce867690f6` |
| Constructed G0 version | **0** |
| Constructed G0 workflow ID | `prior-dec000415cad4f48dcafd2cddc517f0e` |
| Model actions | **6** |
| Every model action `quality_class` | **`null`** |
| Semantic validation | Passed |
| Static feasibility | Failed closed |
| Frozen prior path | None |
| Final frozen plan SHA | None; no validated/frozen plan was produced |
| Constructed, non-frozen G0 canonical SHA-256 | `c964883c32fa4b144bffdf77a153e57c438d802adb361c6d9e3739c8617b459f` |
| Attempt terminal status | `static_feasibility_failed` |

The durable attempt evidence is at:

```text
/home/super/xiaoming/workflow_formal_preliminary_2x2_v1/evidence/
  prior_attempts/
    multihop-rag-train-9bae0079038050a37a1ae583/
      20260929T222546551722Z-f19f3017aed8/
```

It contains `request_metadata.json`, `raw_completion.txt`, `parse_result.json`,
`draft.json`, `constructed-g0.json`, and `validation_result.json`. The previous
Revision-2 rejected attempt remains intact in its separate attempt directory.

## Failure classification

The quality-tier exposure issue is fixed: the LLM draft contained no
`quality_class`, and system conversion produced six formal model actions whose
quality class is uniformly `None`.

The prior did not freeze because `analyze-sorcerer` failed conservative static
artifact/context-envelope analysis:

```text
invoke_model has no static model class fitting its actual prompt/artifact
context envelope: action=analyze-sorcerer
```

This failure happened after semantic validation. It is not a model-quality-tier
failure and does not depend on deployment availability, placement, bandwidth,
RTT, queue, or load. Per protocol, the draft was not normalized, reduced,
edited, or retried.

## Execution boundary

- Workers started: **no**
- `tc` applied: **no**
- Matrix cells executed: **0**
- Retry/reprompt/replacement: **no**

## Conclusion

The formal resource-blind Planner can now generate G0 content without choosing
model-quality tiers, and the system enforces `quality_class=None` for both prior
and adapter-generated model actions. This single authorized call nevertheless
did not yield a frozen G0 because the generated evidence path exceeded the
available conservative static context envelope. Execution stops here pending
further authorization.
