from __future__ import annotations

import argparse
import json
from pathlib import Path

from infra_joint.heterogeneous.workload import MIB, freeze_semantic_workload


def _arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Freeze deterministic S/M/L semantic payloads for heterogeneous v1."
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("configs/local/data/multihop"),
    )
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--small-mib", type=float, default=8.0)
    parser.add_argument("--medium-mib", type=float, default=32.0)
    parser.add_argument("--large-mib", type=float, default=128.0)
    parser.add_argument("--model-instance-id", default="a28-deepseek-chat")
    parser.add_argument("--context-window-tokens", type=int, default=64_000)
    parser.add_argument("--reserved-output-tokens", type=int, default=1_024)
    parser.add_argument("--prompt-token-upper-bound", type=int, default=2_048)
    parser.add_argument("--local-top-k", type=int, default=100_000)
    parser.add_argument("--final-top-k", type=int, default=2)
    parser.add_argument("--overwrite", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = _arguments()
    labels = ("S", "M", "L")
    mib_values = (args.small_mib, args.medium_mib, args.large_mib)
    targets = {
        label: round(value * MIB) for label, value in zip(labels, mib_values, strict=True)
    }
    manifest = freeze_semantic_workload(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        payload_targets=targets,
        model_instance_id=args.model_instance_id,
        context_window_tokens=args.context_window_tokens,
        reserved_output_tokens=args.reserved_output_tokens,
        prompt_token_upper_bound=args.prompt_token_upper_bound,
        local_top_k=args.local_top_k,
        final_top_k=args.final_top_k,
        overwrite=args.overwrite,
    )
    print(json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
