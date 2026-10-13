# Workflow difference analysis method

The Stage 2 comparison pairs each Raw Aware or Ledger run with Blind on the
same source task, network and trial. All three use the same H1 execution
contract and Physical Scheduler. Comparisons use the ordered logical actions,
operators, normalized specialist ownership, declared dependencies, artifact
input flow, output semantic/media types and model requirements. Physical
binding uses the actual selected agent and deployment from each execution
receipt. Anonymous specialist IDs and physical completion order are
normalized before comparison.

The levels are:

- **L0:** the compared logical signature and physical binding are equal.
- **L1:** logical signature is equal, but physical binding differs.
- **L2:** logical operation, dependency, information flow, output semantic
  type, ownership or model requirement differs.

The redacted export also carries SHA256 fingerprints of tool arguments and
model prompts. A hash difference alone is called *textual content change*;
it is not proof of a meaningful semantic change, since stochastic sampling
can change wording under the same policy. L2 is therefore a conservative
structural signal. A useful infrastructure-aware mechanism additionally
requires cross-trial repetition, preserved task evidence and quality, and a
paired resource improvement. A lower-cost failure or early stop is not a
workflow optimization.

H2 is reported separately. Its post-run KEEP attempt cannot be interpreted
as a pre-execution planning decision or an L2 improvement.
