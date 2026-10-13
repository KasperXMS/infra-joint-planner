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
