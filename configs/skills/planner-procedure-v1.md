# Planner procedure v1

Use the following procedure within the supplied task, tools, verifier phases and
remaining budgets. This guidance adds no runtime permissions or new tools.

## 1. Decompose the task and its dependencies

1. Read the objective and exact output contract. Identify the facts needed to
   support that output; do not infer an answer from the requested format.
2. Check the artifact catalog for existing sources, media types, content schemas
   and collection relationships. Form a subgoal only for a concrete missing fact
   or uncertainty. Record which sources and predecessor results it needs.
3. Reuse a valid completed result before creating more work. Run independent ready
   operations in parallel only when their required inputs already exist. Wait
   for a producer's successful result before calling any dependent operation.
4. Delegate only a bounded semantic uncertainty through `consult_specialist`.
   Pass the minimal relevant accessible artifacts and retain global answer
   ownership. A specialist's answer is evidence to assess, not terminal authority.

## 2. Collect and check evidence

1. Preserve source IDs and distinguish direct observations, deterministic
   transformations, and model inferences. A catalog entry describes an artifact;
   it is not its evidence payload, and its small metadata footprint does not
   make a large payload cheap to send to a model.
2. Choose existing legal tools by declared data shape. For record evidence, use
   the declared text field for BM25; use filtering/projection/aggregation only
   when they retain the facts needed by the question. For media, select relevant
   temporal content or concrete frames before model reasoning when appropriate.
3. Check returned success, output IDs and provenance. Use returned, potentially
   namespaced artifact IDs, not an assumed unprefixed output name. An output name
   in a request is not a materialized artifact. Specialist-produced artifacts
   become available to the Manager only after the handoff returns.
4. Check required source coverage and contradictions before asserting a claim.
   Missing evidence is a gap to resolve, not permission to invent a finding.
   Model reasoning over benchmark evidence belongs in `invoke_model` or a bounded
   specialist using legal tools; `read_artifact` is only for small control or
   metadata text, not for pulling benchmark evidence into Manager context.

## 3. Validate calls and budget the real input

1. Before every call, verify the function name, required fields, JSON types,
   permitted extra fields, input count and content schema using the reference
   below and the currently supplied tool schema. Keep `inputs` and `arguments`
   at the correct level; always include both for operators.
2. Count the actual information sent, not only catalog text or the number of
   artifact IDs. Manager context includes instructions, tool definitions, Skills,
   task and full accumulated messages/tool results. `invoke_model` also receives
   attached artifact payloads: a short prompt can still accompany huge evidence.
   Respect the available context/output reserve and remaining turns, tool/model
   calls, delegation, verifier and task-time budgets. Do not assume a tokenizer
   count from byte length or change any configured limit.
3. Reduce input before an oversized model call using only available tools and
   evidence-preserving choices. BM25 returns whole records, `select_fields`
   preserves entire selected values, and `aggregate_artifacts` concatenates
   complete arrays; none summarizes or truncates a long body. Lowering top_k can
   help but one record may still be too large. Use a task-appropriate smaller
   subset or a supported aggregate only if it retains required evidence. If no
   legal reduction fits, report inability within the runtime's failure path.
4. Route data only through existing semantic tools and artifact handoffs. Do not
   request a GPU, worker, deployment, placement, scheduler change or other
   physical resource control. Reserve enough remaining work for synthesis.

## 4. Read feedback, recover and finish

1. Inspect each typed failure. For `schema_validation_failed`, correct the
   missing field, nesting or type and retry only a genuinely corrected legal
   call within the existing budget. Strict validation does not silently repair
   a malformed call. An HTTP/parser error is not evidence of tool execution.
2. For unavailable artifacts, wait for the actual successful producer or use an
   already accessible result. For context rejection, reduce the input rather
   than repeat it. For insufficient evidence or contradictory findings, resolve
   the specific gap while reusing completed valid work. Do not repeat an
   unchanged failure indefinitely, fabricate tool success, or reset budgets.
3. Follow verifier feedback and the current phase. On `ready_for_synthesis`,
   stop evidence expansion: synthesis permits only `invoke_model` or the final
   response, not retrieval, structured/media tools or new specialists. A
   verifier verdict is not the task answer. On incomplete evidence, address its
   stated semantic gaps using legal actions allowed by the current phase.
4. Obtain a successful Manager-owned `invoke_model` candidate supported by
   accessible evidence and matching the output contract. A specialist answer,
   failed invocation, tool argument, or Manager's own prose cannot substitute.
   Return the successful candidate exactly as instructed; only the runtime may
   apply its declared deterministic format extraction. Respect verifier
   authorization/completion and never independently claim success without it.
   When legal actions or budgets cannot resolve the problem, preserve a truthful
   failure rather than invent a candidate or bypass terminal requirements.

## Tool contract reference and synthetic examples

These examples show function arguments, not a response envelope. The function
name is outside the JSON. They are schema examples only: replace all IDs and
field names with accessible, materialized artifacts and their declared fields.
Do not execute an example merely because it appears here.

Every operator below requires top-level `inputs` (an array of artifact IDs) and
`arguments` (an object), even when `arguments` is empty. Operator parameters go
inside `arguments`, not beside it. Only `invoke_model` additionally accepts the
optional top-level `requirements` object defined by its supplied schema; it
expresses semantic execution requirements, not a worker or model deployment.
Do not add undeclared fields. Use the SDK function-call interface; do not handwrite
XML, a JSON response envelope, a DAG, or an infrastructure placement request.

| Operator | Input count | Required keys inside arguments |
| --- | --- | --- |
| invoke_model | 0-64 | prompt |
| read_artifact | 1 | none: use {} |
| bm25_retrieve | 1 | query, top_k, output_artifact_id |
| filter_records | 1 | field, op, value, output_artifact_id |
| select_fields | 1 | fields, output_artifact_id |
| derive_fields | 1 | derivations, output_artifact_id |
| aggregate_records | 1 | aggregations, output_artifact_id |
| top_k_records | 1 | field, k, output_artifact_id |
| aggregate_artifacts | 1 or more | output_artifact_id |
| sample_frames | 1 video | every_seconds, output_prefix |
| extract_clip | 1 video | start_seconds, duration_seconds, output_artifact_id |
| make_contact_sheet | 1-64 images | output_artifact_id |

`consult_specialist` is different: its top-level required fields are
`logical_agent_id`, `role`, `objective`, `instruction`; explicitly supply
`input_artifacts` as the allowed artifact-ID array. Do not wrap these fields in
`inputs` or `arguments`. Use a fresh logical agent ID for each delegation.

Structured and retrieval inputs must contain JSON arrays of objects. BM25's
`text_field` must exactly name a declared string field; its default is `text`,
not an invitation to guess a field. Comparison `op` is one of `eq`, `ne`, `lt`,
`lte`, `gt`, `gte`, `contains`. Each derivation requires `target`, `operation`,
`sources`; operations are `add`, `subtract`, `multiply`, `divide`, with at least
two sources and exactly two for subtract/divide. Each aggregation requires
`operation` and `output_field`; supply `field` for sum/min/max/avg, while count
needs no field. `group_by` is optional. Use positive integer `top_k`/`k`.

`sample_frames` permits optional `max_frames` from 1 to 32 (default 16), and
`every_seconds` must be >0 and <=3600. Its declared outputs are concrete IDs
`output_prefix/frame-000001.jpg` through the requested last frame. The clip must
be long enough to produce every declared frame; consume only returned IDs.
`extract_clip` needs start >=0 and duration >0 and <=36000. Contact sheets use
concrete image IDs, never a frame-set alias; optional columns 1-8 and cell sizes
64-2048 do not authorize unsupported inputs.

<!-- tool-example: invoke_model -->
```json
{"inputs":["evidence/reduced"],"arguments":{"prompt":"Use the supplied evidence to satisfy the current task's exact output contract."}}
```

<!-- tool-example: read_artifact -->
```json
{"inputs":["control/small-metadata"],"arguments":{}}
```

<!-- tool-example: bm25_retrieve -->
```json
{"inputs":["records/source"],"arguments":{"query":"terms from the current objective","top_k":2,"text_field":"body","output_artifact_id":"records/retrieved"}}
```

<!-- tool-example: filter_records -->
```json
{"inputs":["records/source"],"arguments":{"field":"amount","op":"gt","value":0,"output_artifact_id":"records/filtered"}}
```

<!-- tool-example: select_fields -->
```json
{"inputs":["records/source"],"arguments":{"fields":["record_id","body"],"output_artifact_id":"records/projected"}}
```

<!-- tool-example: derive_fields -->
```json
{"inputs":["records/source"],"arguments":{"derivations":[{"target":"total","operation":"add","sources":["left","right"]}],"output_artifact_id":"records/derived"}}
```

<!-- tool-example: aggregate_records -->
```json
{"inputs":["records/source"],"arguments":{"group_by":["category"],"aggregations":[{"operation":"count","output_field":"count"}],"output_artifact_id":"records/grouped"}}
```

<!-- tool-example: top_k_records -->
```json
{"inputs":["records/source"],"arguments":{"field":"amount","k":2,"descending":true,"output_artifact_id":"records/top"}}
```

<!-- tool-example: aggregate_artifacts -->
```json
{"inputs":["records/part-one","records/part-two"],"arguments":{"output_artifact_id":"records/combined"}}
```

<!-- tool-example: sample_frames -->
```json
{"inputs":["media/source-video"],"arguments":{"every_seconds":1,"max_frames":2,"output_prefix":"media/frames"}}
```

<!-- tool-example: extract_clip -->
```json
{"inputs":["media/source-video"],"arguments":{"start_seconds":0,"duration_seconds":2,"output_artifact_id":"media/clip"}}
```

<!-- tool-example: make_contact_sheet -->
```json
{"inputs":["media/frames/frame-000001.jpg","media/frames/frame-000002.jpg"],"arguments":{"output_artifact_id":"media/sheet"}}
```

<!-- tool-example: consult_specialist -->
```json
{"logical_agent_id":"evidence-check-1","role":"evidence analyst","objective":"Resolve one stated evidence gap.","instruction":"Use only the allowed artifacts; return supported findings, source IDs and unresolved uncertainty.","input_artifacts":["evidence/reduced"]}
```
