# Infra-aware preliminary native v1.2

## Status

**Not run.** The required `blind-harness-v1.2` three-family validation gate did not
pass: MultiHop completed normally, LongBench ended on an A28 model-service timeout,
and Video ended before evaluator invocation because its prose candidate could not be
deterministically reduced to a unique terminal choice label.

Accordingly, the planned matrix contains zero executed cells:

| Network | Blind | Aware |
|---|---|---|
| Fast | not run | not run |
| Slow | not run | not run |

No traffic shaping was applied, no `ProfileVisibility.AWARE` run was started, and no
Blind/Aware comparison is claimed. See `docs/blind-harness-v1.2-validation.md` for
the frozen-harness audit and three case traces.
