"""Run the single Blind-verifier MultiHop positive-baseline attempt."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

import sdk_native_blind_multihop_v1 as baseline

REPO = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO / "configs/experiments/sdk-native-blind-verifier-v1.yaml"
DEFAULT_OUTPUT = REPO / "results/sdk-native-blind-verifier-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--multihop-corpus", type=Path, required=True)
    parser.add_argument("--multihop-queries", type=Path, required=True)
    parser.add_argument("--api-key-file", type=Path)
    return parser.parse_args()


if __name__ == "__main__":
    baseline.RUN_ID = "01-multihop-multisource-blind-native-verifier"
    asyncio.run(baseline.run_once(parse_args()))
