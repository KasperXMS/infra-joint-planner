import json

import pytest

from infra_joint.benchmarks.base import BenchmarkSettingKind
from infra_joint.benchmarks.longbench_v2 import (
    FixedWidthColumn,
    FixedWidthStructuredContext,
    FixedWidthType,
    IdentityContext,
    LongBenchV2Adapter,
    LongBenchV2Sample,
    MultiDocumentContext,
)


def official_sample(context: str) -> LongBenchV2Sample:
    return LongBenchV2Sample.model_validate(
        {
            "_id": "lb2-structured-1",
            "domain": "Economics",
            "sub_domain": "Long structured data understanding",
            "difficulty": "hard",
            "length": "long",
            "question": "Which row has the largest count?",
            "choice_A": "Alpha",
            "choice_B": "Beta",
            "choice_C": "Gamma",
            "choice_D": "Delta",
            "answer": "B",
            "context": context,
        }
    )


def test_identity_context_preserves_exact_utf8_bytes_and_hides_gold() -> None:
    sample = official_sample("Full context\nwith Unicode: 香港")
    bundle = LongBenchV2Adapter("THUDM/LongBench-v2@revision").adapt(
        sample, IdentityContext(artifact_id="full-context")
    )

    prepared = bundle.prepared_artifacts[0]
    assert prepared.content.decode("utf-8") == sample.context
    assert prepared.spec == bundle.execution.task.artifacts[0]
    assert bundle.execution.validity.setting_kind == BenchmarkSettingKind.OFFICIAL_EQUIVALENT
    assert bundle.execution.transformations[0].audit["source_sha256"] == prepared.sha256_hex
    task_json = bundle.execution.task.model_dump_json()
    assert '"answer"' not in task_json
    assert '"gold' not in task_json
    assert bundle.execution.task.output_contract.choices == ("A", "B", "C", "D")


def test_multi_document_split_reconstructs_original_context_exactly() -> None:
    context = "First report.\n=== DOCUMENT ===\nSecond report.\n=== DOCUMENT ===\nThird."
    sample = official_sample(context)
    bundle = LongBenchV2Adapter("revision").adapt(
        sample,
        MultiDocumentContext(
            delimiter="\n=== DOCUMENT ===\n",
            artifact_prefix="report",
        ),
    )

    assert [artifact.spec.artifact_id for artifact in bundle.prepared_artifacts] == [
        "report-0001",
        "report-0002",
        "report-0003",
    ]
    reconstructed = b"".join(artifact.content for artifact in bundle.prepared_artifacts).decode(
        "utf-8"
    )
    assert reconstructed == context
    audit = bundle.execution.transformations[0].audit
    assert audit["source_sha256"] == audit["reconstructed_sha256"]
    assert audit["document_count"] == 3


def structured_context() -> str:
    return "\n".join(
        (
            f"{'NAME':<10}{'COUNT':>6}{'PRICE':>8}",
            f"{'Alpha':<10}{12:>6}{'10.50':>8}",
            f"{'Beta':<10}{25:>6}{'7.00':>8}",
        )
    )


def structured_representation() -> FixedWidthStructuredContext:
    return FixedWidthStructuredContext(
        columns=(
            FixedWidthColumn(name="NAME", start_char=0, end_char=10),
            FixedWidthColumn(
                name="COUNT",
                start_char=10,
                end_char=16,
                value_type=FixedWidthType.INTEGER,
            ),
            FixedWidthColumn(
                name="PRICE",
                start_char=16,
                end_char=24,
                value_type=FixedWidthType.NUMBER,
            ),
        ),
        artifact_id="typed-records",
    )


def test_fixed_width_conversion_produces_typed_json_and_audit() -> None:
    bundle = LongBenchV2Adapter("revision").adapt(
        official_sample(structured_context()),
        structured_representation(),
    )

    prepared = bundle.prepared_artifacts[0]
    assert prepared.spec.media_type == "application/json"
    assert prepared.spec.logical_type == (
        "structured_records;fields=NAME:string,COUNT:integer,PRICE:number"
    )
    assert json.loads(prepared.content) == [
        {"COUNT": 12, "NAME": "Alpha", "PRICE": 10.5},
        {"COUNT": 25, "NAME": "Beta", "PRICE": 7.0},
    ]
    audit = bundle.execution.transformations[0].audit
    assert audit["source_record_count"] == audit["adapted_record_count"] == 2
    assert audit["columns_preserved"]
    assert audit["values_preserved"]
    assert audit["numeric_normalization"] == "deterministic"
    assert bundle.execution.validity.setting_kind == BenchmarkSettingKind.OFFICIAL_EQUIVALENT


def test_fixed_width_conversion_rejects_unmapped_data() -> None:
    malformed = structured_context().splitlines()
    malformed[1] += " UNMAPPED"

    with pytest.raises(ValueError, match="unmapped fixed-width data"):
        LongBenchV2Adapter("revision").adapt(
            official_sample("\n".join(malformed)),
            structured_representation(),
        )


def test_fixed_width_conversion_rejects_header_mismatch() -> None:
    context = structured_context().replace("COUNT", "TOTAL", 1)

    with pytest.raises(ValueError, match="header does not match"):
        LongBenchV2Adapter("revision").adapt(
            official_sample(context),
            structured_representation(),
        )


def test_fixed_width_conversion_rejects_numeric_precision_loss() -> None:
    representation = FixedWidthStructuredContext(
        columns=(
            FixedWidthColumn(
                name="VALUE",
                start_char=0,
                end_char=22,
                value_type=FixedWidthType.NUMBER,
            ),
        )
    )
    context = f"{'VALUE':<22}\n{'0.123456789123456789':<22}"

    with pytest.raises(ValueError, match="loses precision"):
        LongBenchV2Adapter("revision").adapt(
            official_sample(context),
            representation,
        )


def test_fixed_width_conversion_preserves_declared_nullable_numeric_values() -> None:
    representation = FixedWidthStructuredContext(
        columns=(
            FixedWidthColumn(name="NAME", start_char=0, end_char=10),
            FixedWidthColumn(
                name="VALUE",
                start_char=10,
                end_char=18,
                value_type=FixedWidthType.NUMBER,
                nullable=True,
            ),
        )
    )
    context = "\n".join(
        (
            f"{'NAME':<10}{'VALUE':>8}",
            f"{'missing':<10}{'':>8}",
            f"{'present':<10}{'2.5':>8}",
        )
    )

    bundle = LongBenchV2Adapter("revision").adapt(
        official_sample(context),
        representation,
    )

    assert json.loads(bundle.prepared_artifacts[0].content) == [
        {"NAME": "missing", "VALUE": None},
        {"NAME": "present", "VALUE": 2.5},
    ]


@pytest.mark.asyncio
async def test_longbench_private_evaluator_requires_canonical_choice() -> None:
    bundle = LongBenchV2Adapter("revision").adapt(official_sample("context"))
    evaluator = bundle.private_evaluation.build_evaluator()

    correct = await evaluator.evaluate(bundle.execution.task, "B")
    verbose = await evaluator.evaluate(bundle.execution.task, "The answer is B")

    assert correct.benchmark_score == 1.0
    assert verbose.benchmark_score == 0.0
