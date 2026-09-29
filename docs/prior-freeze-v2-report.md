# Prior Freeze v2 Audit

## Scope and stop condition

This audit covers the single newly authorized resource-blind prior call for the
frozen workflow-centric formal path. The call stopped fail-closed during prior
validation. No Worker process, `tc` network control, adaptation, or 2x2 matrix
cell was started.

## Implementation revision and validation

- Branch: `open-ended-mas-preliminary-v1`
- Commit used on the 4090 host: `c4e8cf2338d2ab514e6e57b7052deeac05b1d610`
- Generator contract: `PriorWorkflowDraft` (`prior-workflow-draft-v1`)
- System-owned metadata: deterministic `workflow_id`; forced `version=0`
- Generator version: `llm-prior-v2`
- Before the call: full pytest passed (277 tests), Ruff passed, strict Pyright
  passed, and `git diff --check` passed.

## Single-call result

| Field | Result |
|---|---|
| Task label | `multihop-multisource` |
| Source task ID | `multihop-rag-train-9bae0079038050a37a1ae583` |
| Generator | `workflow-formal-preliminary-2x2-v1-prior` / `llm-prior-v2` |
| Model | `deepseek-chat` |
| Backend calls | **1** |
| Attempt ID | `20260929T215316608947Z-bc7441d442a8` |
| Prompt SHA-256 | `3c5c0b7b5f3fbcc372cc749bb6d3a65460a582e135196fea7855b4b344b5957e` |
| Static-capability SHA-256 | `ab2452d152328e674f2ccfdbd48a67a9558f047d89df3a1e1c8977bbc0b3b1bb` |
| Public-bundle SHA-256 | `64aea6d3a8775168398f326cb398382dbe38ec9e7b0c0941b7fb4693e6a731ce` |
| Raw completion persisted | Yes, before parse/validation; 6,639 bytes |
| Draft parse | Passed |
| Draft canonical SHA-256 | `e59046684b5684da768dd2eb3e7f2bf7c638ae645c33b8ab8a8e42e3dad84792` |
| Constructed G0 workflow ID | `prior-c455933b2c842fa8ac32ce56e18e1ca7` |
| Constructed G0 version | **0** |
| Semantic validation | Failed closed |
| Static-feasibility propagation | Not run, because semantic validation rejected the model requirements first |
| Frozen prior path | None |
| Final plan SHA | None; no validated/frozen plan was produced |
| Attempt status | `semantic_validation_failed` |

The durable rejected-attempt evidence is stored at:

```text
/home/super/xiaoming/workflow_formal_preliminary_2x2_v1/evidence/
  prior_attempts/
    multihop-rag-train-9bae0079038050a37a1ae583/
      20260929T215316608947Z-bc7441d442a8/
```

It contains `request_metadata.json`, `raw_completion.txt`, `parse_result.json`,
`draft.json`, `constructed-g0.json`, and `validation_result.json`. No frozen
prior file exists.

## Failure classification

Primary cause: **static capability misuse in semantic workflow content**.

The draft's `analyze-sorcerer` model action requested all of:

- modality `text`;
- minimum context 8,192 tokens;
- reserved output 1,024 tokens;
- required capability `model`;
- quality class `high_quality`.

The resource-blind generator had the static capability contract in its input,
but no abstract model class matched that complete requirement set. Validation
therefore rejected the draft with:

```text
model action is statically infeasible: analyze-sorcerer
```

This is not a dynamic deployment-availability, placement, bandwidth, load, or
queue failure. The harness did not normalize the requirement, substitute a
model, edit the draft, or retry.

## Conclusion

The revised boundary successfully made formal metadata system-owned and made a
rejected prior fully auditable. However, the one authorized call did **not**
produce a clean frozen G0 because its semantic model requirement contradicted
the Planner-visible static capability contract. Per the stop rule, no second
call and no 2x2 experiment were run.
