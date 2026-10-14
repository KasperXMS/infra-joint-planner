# Operator compatibility

| Required capability | Existing implementation | Bounded P1 result / limit |
|---|---|---|
| `search_local` | `bm25_retrieve` in `operators/retrieval.py` | Executes on each resident MultiHop corpus shard; four Development queries produced versioned top-three artifacts. It is deterministic lexical retrieval, not semantic extraction or proof of answer quality. |
| `read_artifact` | Existing Worker `read_artifact` operator | Receipted UTF-8 reads worked for text/table JSON candidate contexts. It has a 65,536-byte limit and rejects unsupported binary media. |
| `extract_evidence` | Existing `bm25_retrieve` and structured operators | Top-three retrieval is a deterministic evidence filter. No fake model output or new semantic extractor was introduced. Table reasoning beyond whole-object read remains unverified. |
| `transfer_artifact` | Existing `HttpWorkerClient.pull_artifact`, `HttpArtifactFetcher`, Worker `/artifact/pull` and `RuntimeExecutor._localize_inputs` | Actual A4→workstation HTTP bodies crossed the LAN. SHA256, response bytes, producer, consumer and latency are in probe receipts. This was operator-level use, not a new duplicate operator. |
| `invoke_model` | Existing Worker deployment contract and preflight | No model was added or invoked. Source Workers advertise zero deployments. Text/table and image/video model compatibility is therefore not established by P1. |

Negative behavior is explicit: direct source GET without token returns 403; missing artifact returns typed `missing_artifact` in existing Worker tests; wrong expected SHA256 returns 409 and leaves no copy; a protected Worker rejects unreceipted semantic calls. Media operators already exist but CrossVid original media and verified model capability do not. The current read-artifact size/type contract is intentionally not bypassed to make multimodal tasks appear runnable.
