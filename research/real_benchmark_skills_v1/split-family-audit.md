# Development-to-evaluation family review

The 8/16 task split was frozen before model outcomes in `task-selection.lock.json`. This later review uses only the original SkillsBench v1.1 task descriptions and bundled Skill names; it does not change or substitute any task. The two splits share broad benchmark categories, as intended for transfer, but no task ID or Skill directory name. The existing normalized Skill-file five-gram screen found a maximum cross-split Jaccard overlap of 0.0024 (`split-duplication-screen.json`). Lexical screening alone cannot establish semantic independence.

The closest apparent task pairs were inspected for shared **task-specific procedure, inputs and deliverable**, not just category labels:

| Development task | Evaluation task | Shared surface | Distinct procedure and deliverable |
| --- | --- | --- | --- |
| `dialogue-parser` | `data-to-d3` | Graph/visual output | Parse scripted dialogue into JSON and DOT graph versus build a D3 web app from stock CSV/history data. |
| `court-form-filling` | `offer-letter-generator` | Office documents and templates | Fill named fields in a California court PDF versus replace placeholders and conditional text in a Word offer letter. |
| `civ6-adjacency-optimizer` | `bike-rebalance` | Combinatorial optimization | Place districts on a hex map for adjacency bonuses versus route vehicles and move bike inventory. |
| `adaptive-cruise-control` | `manufacturing-fjsp-optimization` | Industrial systems | Implement vehicle speed/distance feedback control versus schedule jobs on machines under downtime constraints. |
| `econ-detrending-correlation` | `sec-financial-report` | Finance/economics category | Detrend and correlate economic time series versus analyze SEC institutional holdings. |
| `crystallographic-wyckoff-position-analysis` | `lab-unit-harmonization` | Natural science category | Analyze crystal CIF symmetry/multiplicity versus harmonize laboratory measurement units. |

This review found no near-duplicate task-specific solution procedure among those pairs. It is a qualitative boundary, not proof that a generic Skill-delivery intervention cannot transfer familiar concepts across domains. Any S2 mechanism must be specified from development traces without reading evaluation outcomes; its prompts, mappings and selection rules must remain fixed for all 16 held-out tasks before evaluation starts. The original task packages and verifiers remain unchanged.
