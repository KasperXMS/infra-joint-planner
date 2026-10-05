# Resident model pool v1: preparation audit

2026-10-05. This is prospective environment preparation, not deployment
calibration, a benchmark result, or permission to replace the frozen schedule.

## Verified assets and current boundary

The inactive [manifest](../configs/preparation/resident-model-pool-v1.yaml)
contains three distinct artifacts and five proposed instances: 4B Instruct on
A4, 8B Instruct on A5 and GPU1, and the existing qwen35 27.3B on A28 and GPU0.
All five isolated model stores have already passed full content verification.
They are not five different models. Cross-device replicas preserve a way to
distinguish device/locality choice from model substitution.

Source-content receipt SHA-256:
`c67605618fbccf79d8ee7980bb04e2e75566c36809bbb9271c329ef9fd5670d0`.
Five-store completion SHA-256:
`3d05d3ba3e8545bb9d5244c3f31d892bfaa64243802ed9449422e7620f7593af`.
The preceding preparation handoff, with commit e1c3917 and 961 passing tests,
has SHA-256
`fb7fbb83f5579de8fd3d02fa12fa592e476fbf2ed7a7384d98a90e085f3f2074`.
These receipts certify preparation only; validated model contracts remain null.

### Model diversity is not capability-class proliferation

The existing `control/capabilities.py` builder groups deployments by semantic
capability signature (modalities, host capabilities, context/output envelope,
image-token/output-byte bounds, and explicitly supplied quality classes). Model
name, architecture, parameter count, deployment identity, and replica count do
not themselves create separate advertised classes. Therefore three distinct
weights do not imply three anonymous static model classes. Do not change this
builder or invent `high_quality` / `low_latency` labels to make the pool look
more diverse. Blind and Aware must receive the same calibrated static contract.
Record actual physical model identity privately for execution audit; otherwise
a new-pool latency/quality difference could include model substitution, not just
a device/locality decision.

## Read-only live prerequisite inventory

The inventory uses only GET `/api/version`, GET `/api/ps`, selected process
identity/environment fields, memory/port information, and isolated-store
manifest hashes. No model loading, inference, Planner call, benchmark cell,
configuration change, or shaping operation occurs.

| Node | Default server 11434 | Existing experiment server 11435 | New target ports | Loaded models at observation |
|---|---|---|---|---|
| A4 | 0.33.3 | No HTTP service reached | 11436 not listening | None on 11434 |
| A5 | 0.33.3 | No HTTP service reached | 11436 not listening | None on 11434 |
| A28 | 0.33.3 | 0.34.0 | 11436 not listening | None on either service |
| strong-4090 | 0.34.0 | 0.34.0 | 11436 / 11437 not listening | None on either service |

The 4090 GPUs report the expected separate UUIDs, 24,564 MiB each, with
438 / 411 MiB used respectively. Available host/unified memory is approximately
59.4 GiB on 4090, 27.4 GiB on A4, 26.6 GiB on A5, and 56.8 GiB on A28.
These are point-in-time observations, not a KV-cache capacity or simultaneous
five-model residency test. Empty `/api/ps` is not warm-start readiness.

Existing user-owned experiment servers on A28 and 4090 have keep-alive `30m`,
one parallel request, one loaded model, `q8_0` KV cache, and flash attention.
They are unchanged and do not establish the desired permanent-residency
contract. Root-owned default processes are not fully inspectable by this user;
their responsive API version and loaded-model list are observed independently.

Inventory receipt on 4090:
`/home/super/xiaoming/resident-model-pool-v1/residency-inventory-001/inventory.json`,
SHA-256 `c1c9b6a5542ae2c65dd38869eabcbbb793e57a1a20da1f3eaa85605ae378084b`.

### Process-scan correction

The initial broad argv-substring scan incorrectly classified the inline probe
itself on each host as an experimental process. Those four rows are not valid
live experiment handles. A second, independent scan examines only a Python
script basename or `-m` module identity, excludes inline `-c` and stdin `-`, and
finds no matching experiment processes on any of the four nodes. The original
receipt is immutable; its other observations are not rewritten.

Correction receipt in the same directory:
`process-marker-correction-001.json`, SHA-256
`ce937982b55467378bd2c1729de05746dc64e00679eec7b5db5c87658699a714`.
This is an audit-probe correction, not a benchmark retry or Agent repair.

## Runtime-version preparation

A4/A5 default servers are not the same version as the existing experiment
runtime. Prospective instances must not silently inherit this difference.
Isolated copies of the existing A28 arm64 0.34.0 runtime are now prepared through
4090, with all 36 regular-file hashes/modes and 20 in-root symlink targets
compared at each recipient. The default binaries, old servers, and frozen formal
app are not replaced. This preparation does not start the copied binary as a
server. Both copies execute `--version` and report client version 0.34.0; its
warning that no target server is running is expected, not an inference result.

| Recipient | New isolated runtime | Copy + full hash seconds | Recipient receipt SHA-256 |
|---|---|---:|---|
| A4 | `/mnt/ssd/resident-model-pool-v1/runtime/ollama-0.34.0` | 348.117 | `645057889493432c7a4eef44dc401567cdc419fa46597bb90d66056f10a29882` |
| A5 | `/mnt/ssd/resident-model-pool-v1/runtime/ollama-0.34.0` | 293.847 | `f551635d63b912646f9b512ccd646cf8412b7a6f8362af8b916aa0db7ab3a161` |

Final completion receipt on 4090:
`/home/super/xiaoming/resident-model-pool-v1/runtime-completion-001/completion.json`,
SHA-256 `4db10547d81248051e67e9c96bd4532673a7cad43ebe88c71d763bac746108f5`.
Total completion-helper duration is 521.563s, including relay completion and
parallel recipient copying/verification. These are setup measurements, not
benchmark E2E or model-service latency. No model/runtime payload traverses the PC.

The first preparation process ends with a genuine 240-second copy deadline:
`runtime-preparation-001/failure.json`, SHA-256
`521b9d0d7a7abba6ad72c0d99c1822f62c4155b11587fac643ad05105def4f39`.
Its process is independently verified gone before repair. A completion helper
preserved every already hash-matched relay file and transferred only missing or
incomplete files into the explicit new owned runtime root, then verifies the
entire runtime before distribution. The source files and original failed
receipt are retained. This is file preparation, not a model/benchmark retry.

Post-preparation attestation verifies the original queue, offline audit/snapshot,
and both preparation processes are gone; rechecks the A4/A5 binaries against
the source binary SHA; and observes the old servers still empty and new ports
still without Ollama services. It preserves the earlier inventory rather than
overwriting it. Receipt `runtime-completion-001/post-preparation-attestation-001.json`,
SHA-256 `ed0d9860c6b99ce6040fbba618bebcfa4c7b93dc3d47d64fa8e332359d9bc35d`.
Default A4/A5 servers remain 0.33.3, confirming no in-place runtime replacement.

## Remaining gates

No five-instance service, warm-up, modality/context/output test, service profile,
or simultaneous-residency result is claimed. In particular, 32K/2048 is still a
calibration target for the new small-model instances; metadata context is not
deployment capability. Unknown quality labels and service costs remain unknown.

The old block remains at 42 admitted cells out of 168, with 38 evaluated and
four unevaluated nominal failures. The queue is not resumed. The decision to
finish that block or cut over to a separate new environment remains unresolved.
No method is pruned mid-block, no old evidence is overwritten, and old/new model
pools are not pooled into a matched comparison. All model/runtime payload
preparation occurs remotely; the development PC receives only bounded metadata.

## Local regression

After binding the prepared runtimes in the inactive manifest and adding its
eleventh integrity test, full pytest **962 passed in 32.64s**, Ruff
passes, strict Pyright with the project virtualenv reports zero errors/warnings,
and `git diff --check` passes. Only preparation metadata/tests and documentation
change; executable substrate and formal experiment configs are unchanged. This
does not certify a runnable new environment or permit mixing comparison blocks.
