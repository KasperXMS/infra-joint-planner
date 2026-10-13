# Preliminary development cases: first three 4B task pairs

These are official SkillsBench v1.1 **development** cells under the frozen configuration. They are not a held-out estimate or a claim that Skills cannot help. The original verifiers ran without framework or verifier errors. The primary outcome is binary task resolution; fractional reward and verifier subtests are explanatory only. Full trajectories, artifacts and requests remain in the private workspace and its separate local backup. The public result and trajectory digests below identify exact records without publishing their contents.

| Task | S0 resolution / reward | S1 resolution / reward | S0 → S1 effort | Observed Skill consumption |
| --- | --- | --- | --- | --- |
| `dialogue-parser` | Fail / 0.833 | Fail / 0.833 | 19 → 21 tools; 487,987 → 537,257 provider tokens; 399.7 → 479.0 s | S1 had native Skills available, but zero harness invocations and no Skill path/name in ACP tool actions. |
| `azure-bgp-oscillation-route-leak` | Fail / 0 | Fail / 0 | 11 → 11 tools; 158,878 → 157,368 tokens; 221.9 → 239.3 s | S1 had native Skills available, but zero harness invocations and no Skill path/name in ACP tool actions. |
| `econ-detrending-correlation` | Fail / 0 | Fail / 0 | 35 → 55 tools; 1,331,147 → 1,413,150 tokens; 1,042.5 → 970.0 s | S1 had native Skills available, but zero harness invocations and no Skill path/name in ACP tool actions. |

For `dialogue-parser`, both cells passed five of six verifier checks and failed `test_visualization_validity` at the diamond-shape check. The untouched [official verifier](https://github.com/benchflow-ai/skillsbench/blob/b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af/tasks/dialogue-parser/verifier/test_outputs.py#L187-L190) requires choice nodes to use diamond shapes. This is an artifact completeness failure, not evidence of a tool API or sandbox failure. The extra S1 cost without a read action is evidence of Skill availability not turning into observed consumption in this cell; one pair cannot establish why the model did not read it.

For `azure-bgp-oscillation-route-leak`, both cells passed output structure, oscillation detection and leak detection checks, then failed `test_solution_classification`. The [official verifier](https://github.com/benchflow-ai/skillsbench/blob/b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af/tasks/azure-bgp-oscillation-route-leak/verifier/test_outputs.py#L90-L104) checks each proposed mitigation's two resolution flags. In the captured failures, S0 marked a leak as unresolved when the oracle expectation was true; S1 marked an oscillation as unresolved when the expectation was true. Detection reached a valid intermediate stage, yet the final domain decision remained wrong. The official task reward is zero for both despite those passing subtests.

For `econ-detrending-correlation`, both cells failed `test_answer_file_exists`; the three tests dependent on that file were skipped. S0 reached the original 900-second Agent budget after 35 tool calls, with a complete timeout trajectory and no pending tool action. S1 made 55 tool calls and ended its turn without a timeout, yet still did not produce the required answer file. This pair distinguishes termination behavior from successful artifact delivery. It does not show that Skill availability caused the termination change: no Skill read action was observed in S1, and there is one greedy trial per condition.

The private evidence identifiers are:

| Run ID | `result.json` SHA256 | ACP trajectory SHA256 | Original CTRF report SHA256 |
| --- | --- | --- | --- |
| `development-4b-dialogue-parser-s0-t1` | `1cae72085a8f27283976fc4ad312b81127f2b96e92642ab46ec9de8622cc973e` | `3e66ff687dcf7d03f2d2ed1e392466028979ee48c2bc2920a82190ebcf6a9162` | `59d19497120bf66d7a59abcff4e285d513489649683026533163b26f0277124d` |
| `development-4b-dialogue-parser-s1-t1` | `c5cb26512d9d68f5fe018c0927b3c9dca463c81cb88c1536163a187cefe93c5d` | `b1734cf192c7b5e8a2a1d495822d6f0ffc12a1bfadaa9d689cbf894f5ef485e7` | `87540088bdbafd75f4a98437dcf3df35449b06a2a12dcaf23c3b93a3aebd0f9c` |
| `development-4b-azure-bgp-oscillation-route-leak-s0-t1` | `9328b9398c5127db9f8fd8f728bc154085e5e7765954487e7db85d8a817fb54f` | `25f52d75919507dd9722800eacb54530e6e0b026bed3b95a3739383ab2560d9d` | `dc8d3d3d3cf60696dc010bc657c1ad087898748d5deebc0d3710c247db150ac6` |
| `development-4b-azure-bgp-oscillation-route-leak-s1-t1` | `543f3645e641d12eb58e37e169488011d79cc38a1c83fb3fb629722b84a1f308` | `67e5ed29c3b88bb084788a68240fff83515c9844941ef1bf7c503ffc22992824` | `d9bd744174b9dbe8b8bd832582947eb36db5fabde451fedb039985849a67d5b8` |
| `development-4b-econ-detrending-correlation-s0-t1` | `6a435f5573e3f7a5406966f10e5b4838f049ec1906cd28c805c247344adbc31e` | `36a1010c0a3444c2f82e5e031cc2b5eaa1cf261fd0123ff9c0dbe1d226698619` | `db0867811ef6eb5146a22dbd429d59a18077b387f95c09ec945552be3b788b69` |
| `development-4b-econ-detrending-correlation-s1-t1` | `f22eab76c978337c62522ff44411d50c4da1051b9ae6eb4f2ff31a60307d528e` | `461a81032b6765f83173811146af4fd945227037d56c88e5c4771563a8a5a510` | `4b38cd8c117ea0d47c2c7b2f8d5139228aa82eb65fbe4992e64690f51985e5f6` |

The 69 model generations in these four cells have exact prompt and completion token agreement between the API responses and the AutoDL backend generation counters. The remote counter snapshot SHA256 is `47241c82741e03947baef85c3d8333a9335fac7e76350f8b77724efe8e63fd18`; it also contains excluded infrastructure smoke requests, so counts were matched only within each completed cell's start-to-idle window. No additional generation was found in those four windows.
