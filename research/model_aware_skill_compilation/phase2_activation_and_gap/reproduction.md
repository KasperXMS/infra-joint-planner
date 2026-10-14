# Reproduction boundary and commands

The benchmark source is pinned to [SkillLearnBench commit `726e1f79b96b0cb3d729d0e55a1c847e0b5353ae`](https://github.com/cxcscmu/SkillLearnBench/tree/726e1f79b96b0cb3d729d0e55a1c847e0b5353ae). The [source hash receipt](evidence/source-files.sha256.json), [task image receipt](evidence/trial-image-builds.json), [v1](frozen-manifest.json) and [v2](frozen-manifest-v2.json) manifests, and read-trigger files pin the actual treatment. The source repository, Docker daemon, downloaded Qwen weights, SSH connection configuration and full model traffic are external/local prerequisites; no password or token belongs in Git.

The study runner uses a dedicated WSL2 Docker daemon at `/root/skillsbench-local-20261013/run/docker.sock` and writes byte-exact pinned Skill and task files to `/root/skillsbench-local-20261013/private/model-aware-phase2/material`. The Agent receives the original task environment and instruction, plus the condition-specific original Skill access. Tests, expected outputs and reference solutions stay outside the task container until the Agent exits; the runner then invokes the unchanged `tests/test.sh` and copies final artifacts into the local private trial directory. The source runner's pre-Agent `/tests` mount is intentionally closed to prevent answer leakage. The remote vLLM service uses Qwen3.5-9B BF16 on GPU 0, `responses`, temperature 0, `qwen3_coder` tools, a 16,384-token context and port 18081. The WSL bridge relays raw HTTP over SSH and stores request/response bodies in `/root/skillsbench-local-20261013/private/model-aware-phase2/requests/`; it never rewrites prompts or tool schemas. The separate 27B service, if used for WP3, occupies both GPUs on port 18082.

From WSL root in `/mnt/d/Codes/infra-aware-mas-new/infra-joint-planner`, after installing/starting the previously verified Docker and model services, the preparation and validation commands are:

```bash
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/oracle_preflight.py financial-analysis-4
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/verifier_negative_control.py
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/prepare_material.py
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/build_trial_images.py
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/run_activation_matrix.py
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/analyze_activation.py
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/summarize_gpu.py
```

These scripts contain absolute paths for this study's Windows/WSL mount and will need path substitution on another host. The frozen runner refuses to overwrite an existing trial directory, and the matrix runner stops on infrastructure-invalid cells instead of silently replacing them. `--stage` and `--trial` identify every cell. The two `financial-analysis-2` S3 development probes were run separately, before the `-4` matrix, and are not included in its 3×3 validation denominator. Recreating the reported *same* trial scores is not guaranteed by temperature 0 because the Codex/vLLM Responses route exposes no verified seed control; the intent is to recreate the condition, tools and scoring boundary.

Full Agent traces, original output artifacts, verifier logs, prompt/response bodies and the SSH bridge key are retained locally. Only sanitized hashes, per-cell metrics and reports should be pushed. The [activation summary](evidence/activation-summary.json) has no full prompt, hidden expected answer or secret. The private request archive receives a hash manifest after all cells complete; possession of that archive requires controlled local access and does not imply permission to publish its contents.

For the separate WP3 development diagnostics, the source-valid offer-letter and court-form oracles both scored 1 ([safe oracle summary](evidence/oracle-preflight-summary.json)). The new [gap manifest](gap-manifest.json) fixes two 9B S2 cells and up to two conditional 27B S2 references before any gap Agent run; each cell receives the exact original family main Skill bodies through the same `developer_instructions` route and the unchanged task/verifier. The reproducible preparation and scoring commands, again from WSL root, are:

```bash
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/oracle_preflight.py offer-letter-generator-2
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/oracle_preflight.py court-form-filling-2
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/prepare_gap_material.py
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/build_gap_images.py
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/freeze_gap_manifest.py
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/run_gap_cell.py offer-letter-generator-2 S2 small --stage gap --trial 1
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/run_gap_cell.py court-form-filling-2 S2 small --stage gap --trial 1
python3 research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/analyze_gap.py
```

Run `python research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/fetch_gpu_samples.py` from the Windows repository root before the WSL GPU summary. Before freezing the gap manifest, run `python research/model_aware_skill_compilation/phase2_activation_and_gap/scripts/count_gap_skill_tokens.py` from that same Windows root; it queries the existing model tokenizer and stores only per-family counts. The 32K [non-task probe](scripts/remote_context_probe.py) temporarily switches the study-owned 9B service and restores the frozen 16K service; its [result](evidence/32k-runtime-probe.json) is separate from all task cells. The above `freeze_gap_manifest.py` is intentionally one-shot and refuses to overwrite a frozen manifest; reproducing the study again requires a new namespace and freeze.

For a conditional strong reference, stop only the study-owned 9B vLLM process, launch the pinned 27B GPTQ-Int4 service on both GPUs at 16K/port 18082, and start a second raw [model bridge](scripts/model_bridge.py) at WSL `172.17.0.1:18082` using the same private archive and bridge key. Then invoke `run_gap_cell.py court-form-filling-2 S2 strong --stage gap --trial 1`. The 27B reference is **not** a strong-model upper bound for every family; it is a same-loaded-skill diagnostic on this source-valid court instance. After the diagnostic, stop that study-owned model service and restore the 9B 16K service; never stop or restart the AutoDL instance as part of this protocol.
