"""Run on the dataset host: freeze audited cost-only history, never export raw traces."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from infra_joint.control.consequence_profiles import CostHistory, EmpiricalConsequenceProfiles
from infra_joint.control.cost_history import extract_cost_history


def file_sha256(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def verified_json(path: Path, expected_sha256: str) -> dict[str, Any]:
    if file_sha256(path) != expected_sha256:
        raise ValueError("source audit hash mismatch")
    return json.loads(path.read_text(encoding="utf-8"))


def verified_trace(directory: Path, record: dict[str, Any]) -> list[dict[str, Any]]:
    root = directory.resolve(strict=True)
    hashes: dict[str, str] = record["evidence_hashes"]
    trace_key = f"runs/{record['run_id']}/trace.jsonl"
    result_key = f"runs/{record['run_id']}/result.json"
    if trace_key not in hashes or result_key not in hashes:
        raise ValueError("missing trace/result provenance")
    for relative, expected in hashes.items():
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root) or file_sha256(path) != expected:
            raise ValueError("historical evidence provenance mismatch")
    # splitlines would split legal Unicode separators inside JSON strings.
    return [json.loads(line) for line in (root / trace_key).read_text(encoding="utf-8").split("\n")
            if line.strip()]


def eligible(record: dict[str, Any], *, crossbenchmark: bool) -> bool:
    validation = record["validation"]
    if (validation["validity"] != "operational_checks_pass" or validation["problems"]
            or validation["probe_errors"] or record.get("probe_errors", [])):
        return False
    if crossbenchmark:
        return bool(record["persistence"]["pass"] and record["provenance"]["pass"]
                    and record["summary"]["logical_privacy_pass"]
                    and record["terminal_answer_provenance_pass"] is not False)
    return True


def build_history(
    crossbenchmark: dict[str, Any], multihop: dict[str, Any], leakage: dict[str, Any],
) -> tuple[CostHistory, list[dict[str, Any]], list[dict[str, str]]]:
    """Eligibility is fixed by operational audits, never by completion or quality."""
    records = crossbenchmark["effective_records"]
    if (len(records) != 24 or crossbenchmark["missing_primary_cells"]
            or crossbenchmark["unresolved_cells"]):
        raise ValueError("crossbenchmark source is not the frozen complete 24-cell block")
    leak_records = {record["run_id"]: record for record in leakage["records"]
                    if record["block"] == "existing-multihop"}
    if len(leak_records) != 12 or len(multihop["runs"]) != 12:
        raise ValueError("MultiHop recipient audit coverage mismatch")
    candidates = [(record, Path(record["attempt_evidence_directory"]), True)
                  for record in records]
    exclusions: list[dict[str, str]] = []
    for record in multihop["runs"]:
        leak = leak_records[record["run_id"]]
        if leak["affected"]:
            exclusions.append({"run_id": record["run_id"],
                               "reason": "specialist_dynamic_profile_exposure"})
            continue
        if leak["blind_manager_direct_profile_errors"] or leak["verifier_profile_errors"]:
            raise ValueError("unexpected logical recipient leakage")
        directory = Path(leak["evidence_directory"])
        trace_key = f"runs/{record['run_id']}/trace.jsonl"
        if record["evidence_hashes"][trace_key] != leak["trace_sha256"]:
            raise ValueError("recipient audit and cost audit trace hashes differ")
        candidates.append((record, directory, False))
    if len(candidates) != 33 or len(exclusions) != 3:
        raise ValueError("frozen eligible history coverage mismatch")
    histories: list[CostHistory] = []
    manifest: list[dict[str, Any]] = []
    run_ids: set[str] = set()
    for record, directory, is_crossbenchmark in candidates:
        if not eligible(record, crossbenchmark=is_crossbenchmark):
            raise ValueError("audited clean history no longer passes eligibility")
        run_id = record["run_id"]
        if run_id in run_ids:
            raise ValueError("duplicate historical run")
        run_ids.add(run_id)
        condition = record["condition"]
        if condition not in {"fast-blind", "fast-aware", "slow-blind", "slow-aware"}:
            raise ValueError("unknown historical network condition")
        events = verified_trace(directory, record)
        history = extract_cost_history(events, run_id=run_id,
                                       network_category="fast" if condition.startswith("fast")
                                       else "constrained")
        histories.append(history)
        manifest.append({"run_id": run_id, "condition": condition,
                         "evidence_directory": str(directory),
                         "source_hashes": record["evidence_hashes"],
                         "model_receipts": len(history.models),
                         "operator_receipts": len(history.operators),
                         "transfer_receipts": len(history.transfers)})
    combined = CostHistory(
        models=tuple(item for history in histories for item in history.models),
        operators=tuple(item for history in histories for item in history.operators),
        transfers=tuple(item for history in histories for item in history.transfers),
    )
    return combined, manifest, exclusions


def support_summary(history: CostHistory) -> dict[str, Any]:
    profiles = EmpiricalConsequenceProfiles(history, minimum_support=3)
    model_results = [profiles.model_service(
        model_class=item.model_class, execution_surface_sha256=item.execution_surface_sha256,
        conservative_input_tokens=item.conservative_input_tokens, image_count=item.image_count,
        output_budget=item.output_budget,
    ) for item in history.models]
    operator_results = [profiles.operator_work(
        item.operator, item.input_bytes, execution_surface_sha256=item.execution_surface_sha256,
    ) for item in history.operators]
    transfer_results = [profiles.transfer(
        item.network_category, item.bytes_transferred, path_surface_sha256=item.path_surface_sha256,
    ) for item in history.transfers]
    return {"minimum_support": 3, "model_receipts": len(history.models),
            "operator_receipts": len(history.operators),
            "transfer_receipts": len(history.transfers),
            "model_support": dict(Counter(item.source for item in model_results)),
            "operator_support": dict(Counter(item.source for item in operator_results)),
            "transfer_support": dict(Counter(item.source for item in transfer_results)),
            "model_envelope_unknown": sum(item.conservative_input_tokens is None
                                          for item in history.models),
            "quantiles_are_confidence_intervals": False,
            "quality_used_for_selection_or_fitting": False}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("crossbenchmark", "multihop", "leakage"):
        parser.add_argument(f"--{name}-audit", type=Path, required=True)
        parser.add_argument(f"--{name}-sha256", required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    args = parser.parse_args()
    sources = {name: {"path": str(getattr(args, f"{name}_audit")),
                      "sha256": getattr(args, f"{name}_sha256")}
               for name in ("crossbenchmark", "multihop", "leakage")}
    audits = {name: verified_json(Path(source["path"]), source["sha256"])
              for name, source in sources.items()}
    history, runs, excluded = build_history(audits["crossbenchmark"], audits["multihop"],
                                          audits["leakage"])
    text = history.model_dump_json(indent=2) + "\n"
    summary = support_summary(history)
    repository = Path(__file__).resolve().parents[1]
    source_paths = (Path(__file__),
                    repository / "src/infra_joint/control/cost_history.py",
                    repository / "src/infra_joint/control/consequence_profiles.py")
    manifest = {"version": "cost-history-freeze-v0", "created_at": datetime.now(UTC).isoformat(),
                "extractor_sha256": file_sha256(Path(__file__)), "sources": sources,
                "extractor_source_hashes": {str(path.relative_to(repository)): file_sha256(path)
                                            for path in source_paths},
                "runs": runs, "excluded_runs": excluded, "summary": summary,
                "cost_history_sha256": sha256(text.encode()).hexdigest(),
                "constraints": {"ready_input_envelope_not_actual_tokenizer": True,
                                "physical_surface_hashes_internal_only": True,
                                "operator_wrapper_not_pure_compute": True,
                                "initial_materialization_excluded": True,
                                "historical_model_cache_state_not_controlled": True}}
    # Create exclusively only after all source/eligibility/receipt checks pass.
    args.output_directory.mkdir(parents=True, exist_ok=False)
    (args.output_directory / "cost-history.json").write_text(text, encoding="utf-8")
    (args.output_directory / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(json.dumps({"output_directory": str(args.output_directory), "eligible_runs": len(runs),
                      "excluded_runs": len(excluded),
                      "history_sha256": manifest["cost_history_sha256"],
                      "manifest_sha256": file_sha256(args.output_directory / "manifest.json"),
                      "summary": summary}))


if __name__ == "__main__":
    main()
