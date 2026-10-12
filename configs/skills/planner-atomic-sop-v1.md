# Planner atomic SOP v1

Apply the condition-action rules below to the current state. Each rule uses only
the supplied tools and existing runtime constraints; it creates no new guard,
phase, permission, retrieval mechanism or resource control.

## A. Task and dependency state

- IF starting a task, THEN read its objective and exact output contract; list the
  facts needed for a supported output before choosing an operation.
- IF a required fact is already supported by a valid result, THEN reuse that
  result; do not create another subgoal for the same fact.
- IF a fact is missing, THEN define one concrete semantic gap and identify its
  necessary source artifacts or predecessor results.
- IF an operation depends on an unfinished producer, THEN wait for its successful
  returned result before issuing that dependent call.
- IF operations are independent and all inputs already exist, THEN parallel
  calls are permitted; independence does not permit assumed future outputs.
- IF one bounded uncertainty benefits from delegation and budget permits it,
  THEN call `consult_specialist` with a fresh logical ID, explicit role/objective/
  instruction and only the necessary accessible input artifacts.
- IF a specialist returns, THEN assess its evidence and received artifact handoff;
  retain Manager ownership of global reasoning and the final candidate.

## B. Evidence state

- IF consulting a catalog entry, THEN treat it as metadata about a payload; its
  size or presence does not show that you have read the payload's evidence.
- IF selecting an operation, THEN use the artifact's declared media/content
  schema and collection relationship; do not guess a text field or record shape.
- IF using record retrieval, THEN use an existing BM25 tool with the declared
  string field and task-relevant query; whole records retain their full values.
- IF using a transformation, THEN preserve source identity and the facts needed
  by the objective; distinguish transformed facts from model inferences.
- IF multiple sources are required, THEN verify coverage before making the claim.
- IF evidence is missing or contradictory, THEN keep that gap explicit and resolve
  it through permitted actions; do not replace it with an invented observation.
- IF reasoning over benchmark evidence, THEN pass relevant materialized artifacts
  to `invoke_model` or a bounded specialist's legal tools; do not use
  `read_artifact` to pull benchmark evidence into Manager context.
- IF reading small control/metadata text, THEN `read_artifact` is permitted with
  one accessible UTF-8 artifact and `arguments: {}` within its configured size cap.
- IF an operator reports success, THEN use its actual returned, possibly
  namespaced IDs; a requested output ID alone is not materialization.
- IF an artifact is only named by a future plan or an unfinished specialist,
  THEN do not consume it; await successful production and the authorized handoff.

## C. Call, context and budget state

- IF preparing an operator call, THEN check the current function schema and the
  reference below: top-level `inputs` array plus `arguments` object are mandatory,
  including an empty arguments object where appropriate.
- IF preparing `consult_specialist`, THEN use its separate top-level fields;
  do not wrap them in operator-style `inputs`/`arguments`.
- IF serializing a call, THEN use the SDK function interface, valid JSON types
  and declared keys only; do not write XML or invent an action/DAG envelope.
- IF estimating Manager context, THEN include instructions, tool definitions,
  Skills, task and full message/tool-result history, with output room reserved.
- IF estimating a model-tool input, THEN account for attached artifact payloads
  as well as the prompt; few IDs or small catalog entries do not imply small
  evidence. Byte size is not a tokenizer count.
- IF the real input may exceed the available budget, THEN choose a smaller legal
  evidence-preserving input before calling the model; do not change limits or
  rely on truncation.
- IF reducing record count with BM25 or top-k, THEN remember one retained record
  can still contain a large body; check the retained information budget.
- IF projecting fields, THEN remember selected values remain whole; projection
  does not shorten a retained body field.
- IF combining artifacts, THEN remember `aggregate_artifacts` concatenates whole
  arrays; combining them does not summarize or shrink their payloads.
- IF a supported filter, aggregate, temporal clip or frame selection can reduce
  input without losing required evidence, THEN use that existing operator;
  otherwise do not pretend a smaller representation was produced.
- IF planning another call or delegation, THEN respect remaining turn, tool/model,
  subagent, verifier and time budgets and leave room for terminal synthesis.
- IF data must move between stages, THEN use legal tool inputs and artifact
  handoffs only; do not choose workers, deployments, GPUs, placement or scheduling.

## D. Feedback, recovery and terminal state

- IF a typed call fails, THEN inspect the observed code before choosing a change.
- IF `schema_validation_failed`, THEN correct the actual required field, nesting,
  enum or type; retry only the corrected call within the unchanged budget.
- IF a provider HTTP/parser error occurs, THEN do not infer tool execution or
  fabricate a successful artifact; application Schema validation may never have
  received a parsed call.
- IF an artifact is inaccessible, THEN use an accessible valid result or wait
  for its actual successful producer/handoff; do not invent an ID or contents.
- IF context is rejected, THEN reduce the actual input; do not resend it unchanged.
- IF reasoning or evidence is insufficient, THEN address the specific gap and
  retain valid completed work rather than repeat the entire workflow.
- IF the same unchanged operation fails, THEN do not repeat it indefinitely;
  no recovery rule resets runtime budgets or supplies missing evidence.
- IF verifier feedback is incomplete, THEN treat the stated gap as feedback, not
  an answer, and act only within the phase's permitted tools.
- IF `ready_for_synthesis`, THEN stop evidence expansion; only `invoke_model` or
  a final response is permitted. Do not retrieve, transform, process media or
  start a specialist during synthesis.
- IF no successful Manager-owned `invoke_model` candidate exists, THEN do not
  finish from a specialist response, failed call, tool argument or fresh prose.
- IF synthesis is authorized and evidence is available, THEN invoke the model
  as Manager with the required evidence and exact task output contract.
- IF the successful candidate and verifier status permit completion, THEN return
  that candidate exactly as instructed; any permitted deterministic format
  extraction belongs to the runtime, not an invented replacement answer.
- IF no legal action or remaining budget can resolve the failure, THEN preserve
  a truthful failure; never claim success or bypass terminal requirements.

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
