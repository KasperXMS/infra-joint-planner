# Mechanism scope and closest prior work

This study distinguishes a static skill bank from a deterministic runtime rendering intervention. The latter joins already observed, valid parent artifacts to every public node's policy. It never selects an operation, schedules a node, performs a tool action, repairs a call, or accesses the reference answer. Its proposed value is reducing the model's burden of finding and binding relevant current inputs, not providing new procedural knowledge.

The strongest alternative explanation is renewed attention to current facts. The unjoined control repeats the same policies and artifact facts with the same multiplicities and matches dynamic tokenizer length at each state. It retains ordered parent names, so the information needed for the same decisions is available. Joined versus unjoined can therefore test presentation organization, although padding, serialization and attention locality remain inseparable aspects of that presentation. It does not establish an internal neural mechanism.

## Closest work and boundaries

- [StateMem, v1, sections 5 and 6.4](https://arxiv.org/html/2608.19652v1): structured current state, deterministic dependency rechecking and a length/cost-matched answer wrapper already cover much of the broad idea. That wrapper also traces standing-rule inputs. Our narrower question concerns autonomous, repeated tool-action selection and rebuilding before a terminal answer, with exact observed-input conditional policy scoring. This is a distinction in evaluation and attribution, not proof of algorithmic novelty.
- [SkillSmith, v1, sections 3–4](https://arxiv.org/html/2605.15215v1): compiled runtime interfaces expose operators, inputs, policies and fallback, and may execute typed operators. Our adapter is deliberately weaker: it renders facts and all public policies but delegates every action and branch choice to the measured model. Existing compilation results prevent claiming that runtime interfaces or reduced repeated interpretation are new.
- [SkVM, v3, section 4.2](https://arxiv.org/html/2604.03088v3): environment binding repairs runtime software dependencies before skills execute; this differs from binding observed artifact values to an action policy. Its wider capacity-conditioned compilation and runtime optimization nevertheless overlap the general research direction. Terminological differences cannot establish novelty.

## Falsifiable outcomes

If joined and unjoined support improve equally, favor refreshed current-state presentation over a special joining mechanism. If neither improves full-workflow success despite better one-step decisions, characterize the gap between conditional operation accuracy and autonomous scheduling/recovery. If joined support wins, require an independent transfer condition before recommending a mechanism, and report token overhead and capability failures rather than only successful trajectories.

Static role placement is a separate control: identical content moved between system instructions and the latest user message changes delivery as well as salience. The development result therefore cannot establish that fine-grained skills intrinsically hurt a smaller model. The held-out comparison tests whether that particular placement effect reproduces under new policies and graphs.

All findings remain conditional on these two Qwen3.5 BF16 checkpoints, a supplied dependency graph, strict raw JSON tools, greedy thinking-disabled generation, and a controlled synthetic stress distribution. No result alone identifies a universal parameter-count threshold or real benchmark transfer.
