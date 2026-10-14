# Decision space for open-ended logical workflows

The current finite operator registry can express genuine local choices without
reducing the Planner to a global topology menu. At a decision point define

\[
D_t=(x,s_t,H_t,A_t,C_t),
\]

where `x` is the original task and output contract, `s_t` contains observed
artifacts, versions and completed/running/pending actions, `H_t` is a bounded
anonymous infrastructure profile, `A_t` is the set of *currently proposed*
semantic fragments, and `C_t` records operator capabilities, evidence
dependencies, resource/budget limits, cost intervals and quality risks.
The Planner may propose new fragments; there is no fixed global topology pool.

For the Video-MME comparison, the common completed prefix is
`sample_frames(video) → frames[1..8]`. A pending `invoke_model(frames[1..8])`
can be contrasted with `make_contact_sheet(frames[1..8]) →
invoke_model(sheet)`. The second option adds an actual semantic transformation
and changes model evidence representation. The scheduler's later choice of A4
for image processing and A28 for inference is a separate **physical** decision.
Required evidence is the same original video and same sampled moments, but
the composite may lose detail. Neither graph validity nor matching action
counts proves quality equivalence.

A future decision rule is to minimize an observable *vector* of E2E latency,
communication, model service work, cloud API cost and control work over
feasible fragments, subject to original task success probability meeting a
specified threshold. Missing GPU monetary cost remains unknown. With no
calibrated quality predictor, the quality condition can only be approximated
at decision time by required-evidence contracts, operator preconditions,
image resolution/context checks, model capability profiles and conservative
risk bounds. The private benchmark evaluator is available **after** terminal
execution only; it must never steer the live choice. Structural validation
checks syntax, versions, dependencies and capability feasibility, not visual
answer correctness.

An interpretable time model follows the observed critical path:

\[
T(G,H)=T_{\mathrm{staging}}+T_{\mathrm{critical\ path}}
(\mathrm{local\ operators},\mathrm{transfers},\mathrm{model},\mathrm{control})+T_{\mathrm{terminal}}.
\]

Concurrent independent work contributes its maximum duration on the critical
path, not its sum. For the tested pair, mandatory MP4 staging is common and
must be shown separately from image transfers; this large common term can
hide a meaningful action-level difference in total E2E. With only two network
states, any interpolated break-even is explanatory, not an independently
verified threshold. A unique optimum cannot be asserted when the cost vector
contains opposing or unknown components.
