# Cross-source dependency audit

Classification uses original support annotations **plus question semantics and limited source inspection**; it is not inferred solely from document count or model failure. `D0` means one source is sufficient, `D1` means multiple sources are relevant but necessity is unresolved, and `D2` means the named relation requires source combination under the original question. These are audit labels, excluded from the runtime Planner view. A formal source ablation remains separate future work.

| Class | Tasks | Basis and caveat |
|---|---|---|
| D0 (2) | MultiModalQA `33cf75…` TextQ; `a33985…` TableQ | Original supporting context lies within one text or table artifact respectively. Other candidate docs remain available as distractors. |
| D1 (2) | MultiHop `5390ae…`, `b9e25…` | Two annotated publishers, but the named entity might be recoverable from one article alone; no D2 claim. |
| D2 (4) | MultiHop `a64780…`, `667f4a…`, `a58e94…`, `c1c98d…` | Questions explicitly compare or relate named publisher reports; `c1c98d…` spans three publishers. Original report text was spot-checked. These judgments concern the stated comparison, not the possibility of guessing a short yes/no answer. |
| D2 (4) | MultiModalQA `0ed625…`, `710a6d…`, `d17931…`, `471a2c…` | Each original `Compose`/`Compare` question links a text-derived entity/fact to a table-derived entity/fact; original text and table support IDs were inspected. The grouping is **experimental modality service placement**, not evidence that Wikipedia itself used separate Agents. |

Gold evidence references and answer labels are stored only in `evaluator-private.jsonl` on the experiment machine. Public candidate audit rows record D classes for researchers, while [`planner-view.jsonl`](manifests/planner-view.jsonl) contains only question, answer contract and allowed source collection/candidate references. No per-question oracle partition selects only gold documents: MultiHop installs the full corpus, and MultiModalQA installs every benchmark-advertised candidate context for the retained/inspected Development subset, including distractors. That MMQA subset is suitable for P1 feasibility, not yet for a full-corpus retrieval benchmark.
