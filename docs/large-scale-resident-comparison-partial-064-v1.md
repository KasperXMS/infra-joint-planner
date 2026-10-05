# Partial D adoption audit at the 64-cell boundary

2026-10-06. Offline observation only; no new method, prompt tuning, runtime
change, replacement or pruning. Snapshot020 contains four completed D cells,
not all24scheduled D cells or a complete cross-workload comparison.

The independent tested comparison auditor was applied to every D attempt in
this exact immutable snapshot, checking each trace hash and binding original
admission bytes. All four attempts completed and ran their original evaluator.
Gold, artifacts, prompts, raw arguments and response bodies stay remote.

| Task / Planner / network | Original score | Returned candidate counts | Multi-consequence comparisons | Multi-feasible comparisons | Exact responses visible before choice | Selected / authorized / executed member quotes |
| --- | ---: | --- | ---: | ---: | ---: | --- |
| Video602-2 / P1 / Fast | 1.0 | [1,1] | 0 | 0 | 2 | 2 /0 /0 |
| MultiHop representative2 / P2 / Fast | 1.0 | [] | 0 | 0 | 0 | 0 /0 /0 |
| MultiHop representative1 / P2 / Fast | 0.0 | [] | 0 | 0 | 0 | 0 /0 /0 |
| MultiHop representative2 / P1 / Slow | 1.0 | [1,3,1] | 0 | 0 | 3 | 0 /0 /0 |

The first row demonstrates why selection, authorization and execution must be
separate: two single-member choices were recorded, but neither selected quote
was authorized/executed. Singleton selection is not alternatives comparison.
The last row's only three-member set comprises rejected candidates, not three
cost cards; see the [exact cell59 audit](large-scale-resident-comparison-audit-059-v1.md).
The frozen legacy cardinality metric remains unchanged:0/0/0/1 respectively.

Two P2 runs had no returned comparison sets. Their different evaluator outcomes
cannot establish an effect of unused D comparison. Exact later root visibility
proves exposure, not causal use or optimization. This early subset contains no
LongBench D outcome, no matched complete method/network cells, and no variance
estimate. Do not generalize it to all Planners/workloads, interpret low work or
an incorrect answer as savings, or prune D before the full168-cell audit.

## Append-only provenance

- Snapshot020 file SHA-256: `8dc0c5a77259f809b4b992c5e1e923965699391abf1592a5be19af44550512d1`.
- Offline auditor source SHA-256: `6327d3ed5864011f670850bce08bacb1818fff7853b6af8298a440a9ec2a35d4`.
- Its independent deployment receipt SHA-256: `401810ffbd790a03d3e87350654aa73a468155491af3f4a6a0f4c67a50fda031`.
- Remote `analysis/resident-comparison-snapshot020-audit-001.json` file SHA-256: `863405f547afc5037efd597f6478b7cdbad194c18482f62bd6889730eb146589`.

Each row binds condition/runID, unchanged trace/admission and exact receipt
counters. No original projection or admission is modified; execution and
full-private-audit/pruning permission remain unchanged. This supplement may be
used as partial measurement evidence, not as a replacement for full Phase-I
adoption/failure/private semantic audit and later legitimate Phase-II results.
