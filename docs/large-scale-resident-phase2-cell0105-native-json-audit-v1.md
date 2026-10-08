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

## Implementation freeze and actual validation

Offline integration is committed separately at
`05aafae50548e9742115fcddba7a2660307d7d68`: three new audit scripts and three
new test files, with no historical execution/audit source edit. The final
source run passes2423 tests, with7 existing Windows platform skips, in257.12s;
all109 newly added tests pass. Whole-project Ruff, strict project Pyright,
explicit strict Pyright for the three new scripts and diff check pass.

Actual4090 Linux verification passes837 tests with no skip in12.10s across
28 test files. Its initial collection failure is preserved separately: a
historical reviewed-private test helper was absent from the production import
closure. The unchanged helper was copied to an independent test-support path
(SHA256 `5be5132ed389d8231d92616299383423c3dcaaf9bc1861ad241b5524fffe7599`);
the same test selection then passed. That path is not added to the formal
controller import path. No test was removed to obtain the passing validation.

Actual source-only archive:175 members,1798144 bytes, SHA256
`c1741c53f90f82303bc871f70389ece1a7b0a8561a35a9b81c9d01aba75247bc`.
Owned namespace `audit-tools/resident-phase2-native-control-001` does not replace
the Worker application. The final adapter imports135 sources; all132 historical
source hashes remain unchanged. Its externally pinned closure is
`e97861bc04eaa913823a70f6929bac2a26c0a66a5ace98cbf1d414c6cfbad4c8`.
Measured execution004 hash remains
`16453c240789388fc54c1319334ddbfeca2f0878308b85e643afc2d6d509799c`.

Exclusive validation receipts:

- Local: `ede3e056fbd617419a3614f929883ec8146a6e7494044d6f4ae9beb46e7f5638`.
- Linux: `28b6c321bba3b0c45ea536d40c15a3cf38c8ccc1fc81004dbe0f1e6d1294a8a2`.
- Initial collection failure: `100f5e2f44d11c452e99763cd93b45c4ff9fbf04a503b7af68a0421c996df25b`.

At2026-10-08T05:00:14.699957UTC the exclusive sidecar creator is live,
PID3618263/start196274456, session97633. This is an audit process, not a task
rerun. Its receipt, new native001 authority, independent bootstrap and018
launch have not yet passed. Observe this same creator; do not resubmit it.
