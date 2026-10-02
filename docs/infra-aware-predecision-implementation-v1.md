# Pre-decision protocol implementation audit

Base: `575f415` (Qwen 12-run trace audit). Date: 2026-10-02.

## Minimal changes

- The opt-in native runtime uses the installed Agents SDK `RunConfig.call_model_input_filter`.
  Before **every Manager model call**, Aware obtains `ActionGateway.profile_overview()` and
  appends the existing anonymous `PhysicalProfileView`. It removes only its own previous
  snapshot message; semantic observations are preserved. Blind does not call or inject profiles.
  Specialists retain bounded SDK agents-as-tools; the Blind Verifier sees no profile.
- Generic SHORT_TEXT `OutputContract.canonical_labels` declares exact accepted strings.
  The new prospective experiment declares `Yes` and `No`, without changing the original
  MultiHop evaluator. Punctuation, Markdown, prose and case substitutions are rejected.
  Terminal model prompts receive only the declared formatting requirement. Intermediate
  materialized model notes are not forced into a label. Noncompliant candidates use the
  existing ready-for-synthesis transition; no new state, model call, or semantic guessing.
- Opt-in provenance records the actual filtered semantic model input items, hashes, current
  anonymous profile, selected versus effective action arguments, input artifact producer
  lineage, exact sanitized Verifier context, and per-action started/completed events.
  Provider reasoning items/encrypted content are omitted. Existing private observer sidecars
  and physical execution/service telemetry remain separate from the logical input.
- Original historical harness manifests are unchanged. Their source-hash checks intentionally
  reject this new runtime. Tests verify their hashes against the original committed source;
  the new experiment will have its own runtime/component hashes and config freeze.

No scheduler, physical model, operator, model requirement strategy, budget, Verifier
instruction, retrieval hint, cost guidance, or whole-plan mechanism was changed.

## Verification

Real SDK runner with deterministic synthetic provider and ASGI/fake physical substrate tests:
Blind has no H0; Aware has H0 before first reasoning and fresh Ht before subsequent reasoning;
actual provider inputs match saved provenance; no physical/private identity leakage;
Verifier remains Blind; canonical valid/invalid outputs and format recovery; private provider
reasoning omitted. Existing observer persistence/probe-loss/recovery tests remain intact.

Full pytest: **404 passed**. Ruff: passed. Strict Pyright: 0 errors / 0 warnings.
Tests make no cloud calls or benchmark executions.

## Protocol boundary

The current overview exposes the **existing** anonymous network class and queue envelope;
it does not expose routes/placement or invent missing service costs. Unknown profiles remain
unknown. This tests raw pre-decision infrastructure visibility, not cost-guided planning.

The official SDK describes the model -> tools -> continuation loop in
[Running agents](https://developers.openai.com/api/docs/guides/agents/running-agents).
The exact filter timing is verified against installed SDK 0.20.0 source and a real-runner
integration test; documentation is not used as proof of repository behavior.

Formal experiment has not run at this implementation commit. Config freeze and experiment
reports are separate commits. Historical results and archive hashes remain unchanged.
