"""Compare retained single-answer adapters to unmodified upstream evaluators."""

from __future__ import annotations

import argparse
import asyncio
import importlib.util
import json
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

from infra_joint.benchmarks.multihop_rag import MultiHopOfficialTokenOverlapEvaluator
from infra_joint.benchmarks.multimodalqa import MultiModalQAOfficialEvaluator
from infra_joint.core.task import OutputContract, OutputFormat, TaskContract


def load_module(path: Path, name: str) -> ModuleType:
    sys.path.insert(0, str(path.parent))
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load evaluator: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


async def check(
    private_path: Path, multihop_evaluator: Path, mmqa_evaluator: Path
) -> dict[str, Any]:
    native_mh = load_module(multihop_evaluator, "native_mh_evaluator")
    native_mmqa = load_module(mmqa_evaluator, "native_mmqa_evaluator")
    rows = [json.loads(line) for line in private_path.read_text(encoding="utf-8").splitlines()]
    compared = {"MultiHop-RAG": 0, "MultiModalQA": 0}
    mismatches = []
    for row in rows:
        is_mh = row["task_id"].startswith("multihop:")
        benchmark = "MultiHop-RAG" if is_mh else "MultiModalQA"
        gold = row["answer"] if is_mh else str(row["answers"][0]["answer"])
        evaluator = (
            MultiHopOfficialTokenOverlapEvaluator(gold)
            if is_mh
            else MultiModalQAOfficialEvaluator((gold,))
        )
        task = TaskContract(
            task_id=row["task_id"],
            benchmark_id=benchmark,
            objective="evaluator parity probe",
            artifacts=(),
            output_contract=OutputContract(format=OutputFormat.SHORT_TEXT),
            evaluator_id=row["evaluator_ref"],
        )
        for prediction in (gold, "___definitely_wrong___", gold.upper()):
            result = await evaluator.evaluate(task, prediction)
            native = (
                float(
                    native_mh.has_intersection(
                        native_mh.extract_answer(prediction).lower(), gold.lower()
                    )
                )
                if is_mh
                else float(native_mmqa.list_f1([prediction], [gold]))
            )
            compared[benchmark] += 1
            if abs(result.benchmark_score - native) > 0.01:
                mismatches.append({"task_id": row["task_id"], "prediction_kind": "redacted"})
    return {
        "native_sources": {
            "MultiHop-RAG": str(multihop_evaluator),
            "MultiModalQA": str(mmqa_evaluator),
        },
        "comparison_counts": compared,
        "mismatch_count": len(mismatches),
        "mismatches": mismatches,
        "test_predictions": ["gold", "unrelated", "uppercase_gold"],
        "limitation": "Single-answer parity only; excluded multi-answer case is not covered",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--private", type=Path, required=True)
    parser.add_argument("--multihop-evaluator", type=Path, required=True)
    parser.add_argument("--mmqa-evaluator", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    result = asyncio.run(
        check(args.private, args.multihop_evaluator, args.mmqa_evaluator)
    )
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {
                "comparison_counts": result["comparison_counts"],
                "mismatches": result["mismatch_count"],
            }
        )
    )


if __name__ == "__main__":
    main()
