# Cost and quality comparison method

Each Stage 2 cell retains the original evaluator score and Completion flag.
Cost is a vector rather than a weighted synthetic score:

`(task E2E, known cloud API USD, physical model-service work, network bytes,
control-plane calls)`.

Manager, Specialist and Verifier request receipts include prompt and
completion tokens, provider latency and known cloud price. The physical
service-work counter sums successful Executor model telemetry and is not the
same as task E2E or request waiting time. GPU electricity, rental and
opportunity cost cannot be priced reliably from this experiment and remain
unknown. An absent price or usage value is never converted to zero.

All method comparisons are paired by source task, network and trial. The
analysis presents both successful and failed trajectories. A method's
shorter failed run does not count as an efficiency win against a completed
Blind run. Additional Raw Aware or Ledger guidance is reported as observed
control-plane calls and reflected in role request/token totals; it is not
treated as free. With two trials per paired condition, no statistical
significance or general causal effect is claimed.

## Measured Stage 2 vector

The table sums both networks and both trials for each of the same three
anchors. MB means decimal megabytes. `C_control` is represented by actual
Manager/Verifier provider calls and tokens rather than a fabricated price.

| Method | Completion | TSR | Sum E2E, s | Known cloud USD | Physical service work, s | Network, MB | Manager calls | Verifier calls |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Blind | 7/12 | 3/12 | 3690.1 | 1.7127 | 622.5 | 1166.8 | 123 | 123 |
| Raw Aware | 8/12 | 2/12 | 3248.8 | 1.4476 | 555.1 | 1165.0 | 88 | 88 |
| Cost Ledger | 7/12 | 1/12 | 2803.0 | 1.1364 | 401.4 | 1164.9 | 74 | 74 |

| Method | Manager prompt/output tokens | Verifier prompt/output tokens | Raw-profile or ledger guidance events | Physical inference calls |
| --- | ---: | ---: | ---: | ---: |
| Blind | 1,592,816 / 59,397 | 1,330,495 / 20,696 | 0 | 11 |
| Raw Aware | 1,042,108 / 45,633 | 974,843 / 14,684 | 88 raw-profile | 11 |
| Cost Ledger | 827,295 / 37,648 | 766,096 / 12,609 | 74 ledger | 10 |

Guidance events are injected before Manager decisions; they are not separate
priced provider calls. Manager is local and has unknown GPU monetary cost.
The known cloud spend comes from the fixed cloud Verifier in these Stage 2
cells; Specialist was not invoked. No role request is missing prompt or output
token usage, and no cloud-priced call has unknown USD in the receipts.

The aggregate vector cannot establish efficiency because TSR falls from
3/12 Blind to 2/12 Aware and 1/12 Ledger. Failed or wrong-answer work is a
real cost: the 10 non-successful Aware cells consumed 2170.6 s and $1.2626;
the 11 non-successful Ledger cells consumed 2736.1 s and $1.0745. These
subsets have different task mixes and are not matched cost estimates. The only
pair where both methods scored 1 was Slow Video trial 2 Aware versus Blind:
E2E 866.6 versus 969.7 s, physical work 25.4 versus 38.0 s, known cloud
$0.0787 versus $0.0838, with identical 282.442 MB transfer. The companion
trial lost correctness (Aware 0, Blind 1), so this favorable cost vector is
not repeatable quality-preserving evidence.

Slow Video spends roughly 14–16 minutes per cell largely moving the same
282 MB original video at about 2.8 Mbps; Fast Video transfers the same asset
at about 92–95 Mbps. Transfer bytes are therefore almost invariant across
methods. No method demonstrated a repeatable reduction of the dominant
initial data movement while keeping the answer correct. Differences in
Physical Scheduler placement are recorded separately from logical actions;
the scheduler and Executor pool were not changed. Electricity, GPU rental and
opportunity cost remain unknown, so none of the monetary comparisons is a
full resource-cost comparison.
