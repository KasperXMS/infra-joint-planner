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

The sidecar creator subsequently completed exit0. Exclusive sidecar SHA256:
`da3d543320a59237e029d8921559b4b4c0c62ff808463312edf382004a1750cc`.
It confirms one malformed native argument failure, with original journal
03aec69d...8828c unchanged, no retry, no new model calls, no body export and
no measured execution change. This append supersedes only the preceding live
creator status; it does not change the historical attempt.

At2026-10-08T05:06:04.492447UTC a distinct native001 authority creator is
live: PID3620915/start196309434, session12553. It targets fresh
`phase2-field-reviewed-control-freeze-010.json`,
`phase2-field-ledger-freeze-010.json`, and
`phase2-native-environment-cadence-freeze-001.json`. No authority completion,
independent bootstrap or018 launch is yet claimed. Observe this exact creator,
never restart017 or retry105. All final requirements remain incomplete.

## Authority completed; independent bootstrap started

Native001 authority creator12553 subsequently completed exit0. Manifest:
`b3c48708b7595812dcac624dbfc82942bc6b7bf5cc17bcf581aa674e506ff96d`;
control010: `e324868b2203de2f733d6b708f910115836ea8602411787dbdabe8bcb5586bf7`;
ledger010: `1533b2b5eba3dd696c31a0f6856d73c69e2e2ac1bd40d09421768137c6ea9221`.
The control payload remains byte-identical to009. All13 historical raw/effective
review pairs, all five disjoint groups, original71 exclusion and its sole
replacement, execution004 and original schedule remain bound. Raw journal
03aec69d...8828c is unchanged. Creator verifies105 admitted nominal cells,
106 preserved attempts, no pending/unresolved finding and one exclusion.
**Admitted nominal cells include valid semantic failures; this does not mean
105 execution completions or correct answers.**

At2026-10-08T05:17:49.352243UTC independent bootstrap1887 is live:
PID3626140/start196379922. It must reproduce the full original gate, all106
trace/recipient request hashes, unchanged132 ancestor sources within the135
actual-import closure, exact five-group membership, and the actual new final
path's incomplete-inventory refusal before private body/output. No bootstrap
receipt or018 launch yet. Observe this handle; do not resubmit. Nextordinary112;
all192/all193 and all final private/manual/quality/Q1–Q10 obligations persist.

## Independent bootstrap completed

Bootstrap1887 completed exit0. Exclusive readback receipt SHA256:
`c1fd724845148d6a9fb4cf45e11c648f071dbde69c6d95421247bdd986ce383f`.
It independently verifies105 admitted nominal cells,106 preserved attempts,
zero pending/unresolved, one exclusion and87 unstarted; all106 trace and
1727 actual SDK request hashes. Recipients:777Manager,776fixed Blind Verifier,
174specialist. Exact root feedback matches:193profile,400ledger,205rules;
visibility is not evidence of causal adoption. All135 imported sources and
132 historical ancestor hashes reproduce the externally pinned closure.

The **actual** new final adapter rejects the incomplete run inventory with
`final bundle requires all192 resolved and all193 preserved`, before private
body/output; probe output remains absent. No private semantic/manual audit or
quality aggregation has been performed. Original105 completionfalse and null
evaluation remain independently verified. Only now may a new018 controller
resume original106 under unchanged16-cell cadence and execution004. Next112;
old017 and original105 must never be restarted.

## New018 resumed the original schedule

After independent bootstrap success, an exclusive new018 launch completed.
Supervisor3633931/start196483150 and controller3633932/start196483152 are bound
to native001 and the exact readback receipt; supervisor file SHA256
`80fd098c123c8da6d5f71d59ac3de253becf000ed9db532bcb6bfb5fe783b160`.
The independently created live receipt
`5b39773ac2d11176f56e122448583054094a0d9100bc27ec24dd20dfabd961ca`
checks their exact argv, start ticks and metadata. Actual final guard rejects
active execution with `private body audit requires inactive queue and atomic actions`,
before private body/output. No live final probe file is created.

At2026-10-08T05:37:00.625679UTC, original106
`phase2-multihop_rag-6-21c8b34e79c81848-p2-slow-B0`, attempt1, is live:
atomic3635073/start196494959.105admitted/106settled+1pending=107preserved,
zero unresolved, one exclusion and86 unstarted. Journal SHA256
`920e4cb0969d8df143a8ccfa044ad2c67a1d85c9af8e89b3989e4a4fa4cf51a8`
extends the immutable original105 prefix. No105retry or old017restart. Ordinary
cadence16, next112, measured execution004 and all source/privacy/quality gates
remain unchanged. Original192/all193 and all final private/manual/terminal/
failure/retention/adoption/quality/Planner/workload/Q1–Q10 audits remain required.
