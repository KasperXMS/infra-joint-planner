# Development trace review rubric

The official verifier decides task resolution. Trace review explains *how* a cell reached that outcome; it must not change the task score or provide an excuse to rerun a failed answer. Use the frozen task and its original test names, `result.json`, the ACP trajectory, private model request metadata, and output artifacts. Cite run ID, trajectory step indices, verifier test names and SHA256 digests. Keep full prompts, tool output, credentials and generated artifacts private.

For each S1 cell, code the following evidence levels independently:

| Code | Minimum evidence | Limit |
| --- | --- | --- |
| Available | BenchFlow `include_task_skills=true` plus sandbox proof for native directory | Does not show the model noticed the skill |
| Discovered | Agent lists/references the native skill path or name in a tool action or thought | Could be a superficial mention |
| Read | Tool action opens `SKILL.md` or a bundled reference/script for content | Reading alone does not show correct use |
| Executed | Tool action runs a bundled script or command from the skill | Execution may fail or target the wrong data |
| Applied | Trace and artifact show a specific procedural step used on task data | Requires human review; path regex cannot establish this |
| Helpful/harmful | Matched S0/S1 official outcomes and supporting trajectory differences | One greedy trial cannot establish a general causal mechanism |

Code failure factors only where there is affirmative evidence. Categories may coexist: domain knowledge, skill discovery/consumption, tool argument grounding, action sequencing/state tracking, failed-action recovery, artifact/termination completeness, and sandbox/infrastructure. A clean verifier run with reward below one is a task failure; a missing verifier/failed environment is an infrastructure fault. Report unresolved causes as `undetermined`. Tool calls marked `failed` by ACP are candidate tool errors; review their actual status before treating them as model errors. Repeated actions count only when the same relevant operation is retried without useful new state. Recovery success requires a failed step followed by a corrective action and verifier-relevant progress.

Use `extract_trace_signals.py` only to locate candidate skill paths and failed tool steps. Its name/path search can miss indirect use or flag a mention in an edited file; review the original private trajectory before assigning `read`, `executed`, or `applied`. Separate failed ACP `think` and unclassified `other` calls from failed `execute`/`read`/`edit` actions before calculating an environment tool-error rate. In the early economics S1 trace, eight failed calls are all `think` events, so counting them as eight failed terminal actions would be incorrect. Keep verifier subtest fractions separate from official task success. Compare task pairs and both model sizes descriptively; lack of a skill-use action in one run is an observation, not a law about the model.
