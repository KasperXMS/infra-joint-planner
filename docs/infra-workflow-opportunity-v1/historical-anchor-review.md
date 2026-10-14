# Historical anchor review

The proposed Video-MME 795 latency table (284.7/205.4 seconds at 3 Mbps and
34.9/160.8 seconds at 100 Mbps) could not be tied to a frozen task manifest,
complete logical-action trace, private evaluator result, or consistent cost
boundary in the committed evidence at `ee5c044`. It remains an **unverified
cost-crossover candidate**, not a proven quality-preserving logical-workflow
reversal. It must not be combined with the later 5 ms measurements.

The strongest reproducible Video-MME anchor is original task `795-3` on the
41.6-minute AV1+Opus MP4 `D97vMwfWxvI.mp4`, 282,442,048 bytes, SHA-256
`78c7158b4ea8a29a418f84cabe77caf0a35fb0f5416c8c1592fe781b5783a4b9`.
Task `795-2` asks a different question of this same video; the two are not
independent video sources. Original evaluator and private gold are retained on
the experiment controller. [Prior 12-cell audit](../predecision-videomme-v1.md)
used fast 100 Mbps/configured 5 ms and slow 3 Mbps/configured 50 ms, with
cloud `qwen3.8-max` Manager/Verifier and local A28 `qwen3.8-27b-v1` physical
model. Jetsons were HTB-shaped without netem; configured delay is not an
independently measured symmetric RTT.

For `795-3`, the historical fast Blind/Aware runs took 185.443/252.371 s and
scored 0/1, while slow Blind/Aware took 1069.965/1071.594 s and both scored 1.
These are stochastic Agent-generated workflows, not controlled executions of
the same pair of fixed logical strategies. The slow correct pair reduced action
bytes from 1,562,096 to 1,471,756 (5.8%), but E2E was essentially unchanged.
Its mandatory original-video staging consumed about 789 s in **both** cells;
this fixed input transfer cannot be attributed to workflow choice. The fast
pair is not quality-matched. Thus the audited evidence does not prove a
quality-constrained preference reversal.

The earlier heterogeneous MultiHop-derived placement crossover compares
physical locations for a fixed action graph. Its synthetic replication and
unchanged semantic actions make it a physical scheduling result, not a logical
workflow rewrite. Historical Video-MME 848 contact-sheet traffic savings also
fail the quality constraint because all compared answers were wrong. The 36-cell
Harness v2 study found 21/24 L2 structural differences, but no method
repeatedly preserved correctness while lowering cost. We exclude repeated
retrieval, unproductive reasoning, phase violations, and early failure from
candidate optimization opportunities.

The new fixed experiment records staging, workflow-triggered transfer, model
work and evaluation separately. It tests a narrower, executable representation
choice rather than treating the historical table as a validated anchor.
