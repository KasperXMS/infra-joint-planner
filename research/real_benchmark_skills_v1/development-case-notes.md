# Preliminary development cases: first two 4B task pairs

These are official SkillsBench v1.1 **development** cells under the frozen configuration. They are not a held-out estimate or a claim that Skills cannot help. The original verifiers ran without framework or verifier errors. The primary outcome is binary task resolution; fractional reward and verifier subtests are explanatory only. Full trajectories, artifacts and requests remain in the private workspace and its separate local backup. The public result and trajectory digests below identify exact records without publishing their contents.

| Task | S0 resolution / reward | S1 resolution / reward | S0 → S1 effort | Observed Skill consumption |
| --- | --- | --- | --- | --- |
| `dialogue-parser` | Fail / 0.833 | Fail / 0.833 | 19 → 21 tools; 487,987 → 537,257 provider tokens; 399.7 → 479.0 s | S1 had native Skills available, but zero harness invocations and no Skill path/name in ACP tool actions. |
| `azure-bgp-oscillation-route-leak` | Fail / 0 | Fail / 0 | 11 → 11 tools; 158,878 → 157,368 tokens; 221.9 → 239.3 s | S1 had native Skills available, but zero harness invocations and no Skill path/name in ACP tool actions. |

For `dialogue-parser`, both cells passed five of six verifier checks and failed `test_visualization_validity` at the diamond-shape check. The untouched [official verifier](https://github.com/benchflow-ai/skillsbench/blob/b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af/tasks/dialogue-parser/verifier/test_outputs.py#L187-L190) requires choice nodes to use diamond shapes. This is an artifact completeness failure, not evidence of a tool API or sandbox failure. The extra S1 cost without a read action is evidence of Skill availability not turning into observed consumption in this cell; one pair cannot establish why the model did not read it.

For `azure-bgp-oscillation-route-leak`, both cells passed output structure, oscillation detection and leak detection checks, then failed `test_solution_classification`. The [official verifier](https://github.com/benchflow-ai/skillsbench/blob/b63b7b2850226b6aa4fb5929a8c1ac7bc4d9a6af/tasks/azure-bgp-oscillation-route-leak/verifier/test_outputs.py#L90-L104) checks each proposed mitigation's two resolution flags. In the captured failures, S0 marked a leak as unresolved when the oracle expectation was true; S1 marked an oscillation as unresolved when the expectation was true. Detection reached a valid intermediate stage, yet the final domain decision remained wrong. The official task reward is zero for both despite those passing subtests.

The private evidence identifiers are:

| Run ID | `result.json` SHA256 | ACP trajectory SHA256 | Original CTRF report SHA256 |
| --- | --- | --- | --- |
| `development-4b-dialogue-parser-s0-t1` | `1cae72085a8f27283976fc4ad312b81127f2b96e92642ab46ec9de8622cc973e` | `3e66ff687dcf7d03f2d2ed1e392466028979ee48c2bc2920a82190ebcf6a9162` | `59d19497120bf66d7a59abcff4e285d513489649683026533163b26f0277124d` |
| `development-4b-dialogue-parser-s1-t1` | `c5cb26512d9d68f5fe018c0927b3c9dca463c81cb88c1536163a187cefe93c5d` | `b1734cf192c7b5e8a2a1d495822d6f0ffc12a1bfadaa9d689cbf894f5ef485e7` | `87540088bdbafd75f4a98437dcf3df35449b06a2a12dcaf23c3b93a3aebd0f9c` |
| `development-4b-azure-bgp-oscillation-route-leak-s0-t1` | `9328b9398c5127db9f8fd8f728bc154085e5e7765954487e7db85d8a817fb54f` | `25f52d75919507dd9722800eacb54530e6e0b026bed3b95a3739383ab2560d9d` | `dc8d3d3d3cf60696dc010bc657c1ad087898748d5deebc0d3710c247db150ac6` |
| `development-4b-azure-bgp-oscillation-route-leak-s1-t1` | `543f3645e641d12eb58e37e169488011d79cc38a1c83fb3fb629722b84a1f308` | `67e5ed29c3b88bb084788a68240fff83515c9844941ef1bf7c503ffc22992824` | `d9bd744174b9dbe8b8bd832582947eb36db5fabde451fedb039985849a67d5b8` |

The 69 model generations in these four cells have exact prompt and completion token agreement between the API responses and the AutoDL backend generation counters. The remote counter snapshot SHA256 is `47241c82741e03947baef85c3d8333a9335fac7e76350f8b77724efe8e63fd18`; it also contains excluded infrastructure smoke requests, so counts were matched only within each completed cell's start-to-idle window. No additional generation was found in those four windows.
