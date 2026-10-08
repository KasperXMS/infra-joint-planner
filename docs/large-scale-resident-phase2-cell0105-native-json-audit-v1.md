# Phase II cell105: native specialist JSON audit

## Original attempt and stop

Cell `phase2-multihop_rag-6-21c8b34e79c81848-p1-fast-E`, attempt1, was
preserved without retry or replacement. Controller017 exited1 at
2026-10-07T21:33:31.329074UTC. At 2026-10-08T04:48:59UTC its supervisor,
controller and original atomic handles were absent; journal SHA256 remains
`03aec69d77d3876121e4a1dd31608c1a4857763893b0482eab26a6949008828c`.
There is no106 reservation. Current authority still has104 effective samples,
106 settled preserved attempts, no pending attempt, one unresolved finding,
one operational exclusion and87 unstarted nominal cells.

Raw admission flags only `terminal_failure_requires_system_audit`.
Execution completion is false and evaluation is null, not score0.
Operational, API and method audit problem lists are empty. Worker shutdown
is verified. Original trace has576 events and SHA256
`c7eeda2dfe0f0c2e7f13a141af0bec573221f862a9a7c151ac5d475886e3cfda`;
admission file SHA256
`a5c57a492dc9e64d9333c4e47784d7c2e74bbe22cafb9182577a85d5ec83454b`.

## Source-bound diagnosis

The last Manager provider response (HTTP200, finish reason `tool_calls`)
contained invalid JSON for `consult_specialist`. Frozen SDK execution surfaces
the schema parser exception as `UserError`; it is not a provider outage.
Exact tool call `call_7aedc107f87a4c588cae8a18` has1262 argument bytes and
canonical argument SHA256
`b17ed5e8d4c340e6c8c7af365dffe2bb9e6ac6a7517132f024d3efb4ca9dd3fc`.

Read-only reproduction with the already frozen native-argument reviewer passed:
its source SHA256 is
`27cb62dc9afe1e731263acaffdb73ee7e93980855c7aceb8cce49335ebaad603`.
Actual native and installed SDK lexical/resolved source hashes match the
historical Phase I proof pinned to
`d240e209996860e13fefa34c24f8ceab862c623bc91d8875e8da01bcd7223acc`.
The actual strict SpecialistRequest schema and exact malformed arguments
reproduce the original terminal exception. No truncation, response replacement,
model call or semantic repair was introduced.

The reproduced classification is
`workflow_composition_malformed_native_tool_json`; proposed reviewed admission
SHA256 is `b14c682958e355bea142cd9ffb502c056fdf4ce635c495e7343e8bf16b0ae5c1`.
This is an auditable valid semantic failure, **not a completed/answered task**.
At this note's initial freeze the separate Phase II sidecar and continuation
authority have not yet been created; reproduction alone does not authorize
dispatch or change the raw journal.

## Companion context observations

Three model actions were rejected before inference. Conservative input
estimates175010,117120 and32107 each requested2048 reserved output tokens,
against32768 context. These are preflight estimates, not actual input usage
or actual inference calls. They are evidence of context recovery difficulty,
not the sole admission finding being reviewed. No output-token/context tuning
is permitted to rescue this sample.

## Offline integration and remaining gates

A separate fifth proof namespace is being integrated without changing the
four historical namespaces, their raw/effective pairs, or original71's sole
exclusion/replacement. The new offline reviewer, continuation authority and
final adapter must pass focused/full pytest, Ruff, strict Pyright and diff
checks, followed by actual4090 Linux/source-bound verification.

Only after exclusive sidecar creation, complete five-group authority verification
and independent recipient/source/guard bootstrap may a new018 controller
dispatch original106. Controller017 and attempt105 must never be restarted.
Ordinary audit cadence remains16; next checkpoint112. Final private/manual
audit, all192/all193 reconciliation, failure/retention/adoption/quality analyses,
Q1–Q10 and named reports remain incomplete. No partial quality aggregate.
