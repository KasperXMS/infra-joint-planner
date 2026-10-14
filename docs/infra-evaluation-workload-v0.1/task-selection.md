# Candidate selection

Selection was fixed by original MultiHop row indices `(0, 1, 3, 7, 17, 26)` and MultiModalQA QIDs in [`prepare_infra_evaluation_workload_v01.py`](../../scripts/prepare_infra_evaluation_workload_v01.py). Criteria were source metadata, reasoning type, single-answer evaluator compatibility, and available raw context. No Planner output, cost crossover, or gold-answer performance was used. The [12 retained questions](manifests/task-candidates.jsonl) are all public Development tasks: 6 MultiHop-RAG and 6 MultiModalQA. The [Planner projection](manifests/planner-view.jsonl) omits gold answers, supporting-context IDs, dependency judgments and relevance counts.

| Stratum | Retained original IDs |
|---|---|
| Single-source controls | `mmqa:33cf75c43fb268f267002cf8b9c28313` (text), `mmqa:a33985b1e8b2502fc18cc8147dc27db8` (table) |
| Two-publisher reasoning | `multihop:5390ae18477c53f9`, `multihop:b9e25d4f9cdbf57f`, `multihop:a647807d9a1d0efd`, `multihop:667f4ac48afef820`, `multihop:a58e945f57294eca` |
| Three-publisher temporal reasoning | `multihop:c1c98d6cf60878e4` |
| Text+table composition/comparison | `mmqa:0ed625390ca7f919b46fd99fe85d80b5`, `mmqa:710a6d2254076ea58756c6c7cc211f1e`, `mmqa:d17931e347af95c54d4acd295f91ea5d`, `mmqa:471a2c824769af89d5d77a881462c775` |

Three inspected cases are [excluded with explicit reasons](manifests/excluded-candidates.jsonl): `crossvid:CC:0` lacks deployed original multi-video media, `crossvid:BU:0` needs independently licensed original behavior media, and `mmqa:f5326b243eed1f858865df5e3337cb10` has a three-answer list contract that the existing short-text adapter cannot preserve. The latter entered an initial operator probe before evaluator-contract review; the [original receipt](feasibility-initial-public.json) remains intact, and a single-answer replacement has its [own correction receipt](feasibility-correction-public.json). This was a workload-validity correction, not a rerun of any Planner or model outcome.

The benchmark's own candidate context IDs and distractors are retained for MultiModalQA; the MultiHop source collection contains all 609 original corpus articles. The selected tasks do not constitute an unseen test set or a statistically powered sample. Large image/video input is not represented among retained tasks. The provisional future 12/12/36 Development/Validation/Test allocation remains a design target; only this bounded Development pool was materialized.
