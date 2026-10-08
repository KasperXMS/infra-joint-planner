# Resident Phase II: original117 terminal protocol failure

This is a narrow typed-terminal/provenance review while the queue remains live,
not the final private semantic/root-cause or quality audit.

## Preserved original attempt

- Cell: `phase2-longbench_v2-4-014b99ef3d98cb5d-p1-fast-E`, attempt1.
- Manager DeepSeek V4 Pro; fixed Blind Verifier Qwen3.8-Max; Fast; E.
- Actual revision `0ff0e9b6d0799bd62e725a76b157e64cd9df5ccd`, unchanged
 20Manager/64physical/20Verifier,8specialist,4created/2active and1200s timeout.
- Config SHA256 `8fe0c1b147d71c7efb133206e0769644c36e2982add0bc11f3698f030d634a1a`.
- Original admission SHA256 `1a87d754c4814eae77b73bff729dc414d3db78e11f271ed07f9e7a8e26707f69`.
- Result SHA256 `29db8b33e07e84fc9a5c383cd20f4f176e24c155e4e25f43d0759ba7e6677927`.
- Trace297events, SHA256 `2049a9a209e2726128aa844193b004fbd5d4ed03fdaddae60247ee5b7ba0ad10`.

Admission is valid (`completed_or_valid_semantic_failure`), with no admission
problems or operational incidents. Execution completion is false; evaluation
is absent. Missing benchmark score remains missing, not zero.

## Observed terminal failure

`logical_loop_failed` / `AgentLoopError`:

> Blind verifier returned complete without a successful manager model candidate

The unchanged `_latest_terminal_candidate` accepts only a succeeded root-owner
`LogicalModelAction` observation with nonempty text. It does not turn a Verifier
verdict, prose or an arbitrary subagent result into a new terminal answer.
The reported failure is the existing fail-closed guard, not a newly introduced
runtime crash or a reason to tune the harness for a positive result.

Existing diagnostic regression
`tests/test_native_agents.py::test_complete_verdict_without_model_candidate_fails_closed`
passed on2026-10-08 (exit0). No production/test code changed; no model was called
by this check. This unit result proves the guard's intended contract, not the
whole live run's semantic root cause.

The observed terminal class is stopping/Verifier completion protocol failure.
Whether earlier evidence selection, context recovery or composition contributed
requires the later complete manual audit; no strong primary semantic-cause or
E-method quality claim is made from this narrow observation.

## Infrastructure and continuation

Process exit0; all4Workers verified exited/errors[]; resident5instances passed
without startup subtraction; `tc.cleanup_error=None` and exact original qdisc
restoration. No operational replacement, semantic retry, prompt/budget/tool/
model/harness change or new exclusion. The result and historical evidence remain
immutable. Same020 controller continues under the existing gate; ordinary
full128 is required before129. All192 resolved/all193 preserved plus strict
global inactivity remain prerequisites for final private/retention/quality/
adoption/failure/Q1–Q10 reporting.
