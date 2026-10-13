# Infra-aware Workflow Adapter readiness

Engineering result: **conditional Go for an isolated Adapter prototype; No-Go for claiming a rigorous live Adapter experiment from this branch alone.** The correctness and state interfaces needed to build such an experiment now exist, but distributed fault behavior and representative provenance coverage have not been validated on real infrastructure.

| Question | Current evidence |
|---|---|
| Q1: partial batch failure | Yes in deterministic fault injection: successful sibling commits and receipt survives. |
| Q2: candidate-bound `complete` | Yes in native runtime tests: ID, output SHA256, evidence version, ownership, success, and output contract checked. |
| Q3: typed Specialist result | Yes in Fake SDK tests: failed nested agent is a typed failure with real source IDs and no invented terminal ID. |
| Q4: open-ended SDK proposal | Yes in opt-in bridge test: SDK function calls still generate semantic actions incrementally. |
| Q5: versioned pending workflow | Yes: open fragments, sealed formal plan, separate execution state, and transition records. |
| Q6: KEEP/PATCH without prefix rewrite | Yes in formal and v2 tests: existing validator, exact version, pending-only edits, quiescent frontier. |
| Q7: unknown information lineage | Yes for tested rewrites: relevant unknown provenance rejects revision; full free-text lineage inference is unsupported. |
| Q8: no blind replay | Yes in receipt and cancellation tests: uncertain effects remain indeterminate; no-resume policy is explicit. Real crash behavior is unverified. |
| Q9: compatibility | Focused native/control/formal suites pass; frozen historical manifests still reject runtime drift. Benchmark, evaluator, Scheduler, Skills, and historical results unchanged. |
| Q10: next step | Build a new, versioned Adapter condition only after live multi-process fault tests and lineage coverage review. Do not attribute Harness fixes to Adapter benefit. |

This is an engineering assessment, not an experimental TSR or cost result. GPU monetary cost remains unknown and no Adapter algorithm or large-model evaluation was launched.
