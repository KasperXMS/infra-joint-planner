"""Reuse the identical inference engine; only instantiate presentation-aware tasks."""
import argparse
from pathlib import Path

import run_model
from transfer_microbench import Task

run_model.Task = Task


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--root", required=True, type=Path)
    p.add_argument("--config", required=True, type=Path)
    p.add_argument("--model", required=True)
    args = p.parse_args()
    run_model.run(args.root, args.config, args.model)
