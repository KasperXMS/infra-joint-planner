import math
import re
from collections import Counter
from typing import Any

from pydantic import Field

from infra_joint.core.action import SemanticAction
from infra_joint.core.base import ContractModel
from infra_joint.operators.artifacts import load_records, store_json
from infra_joint.operators.registry import OperatorRegistry, OperatorSpec
from infra_joint.worker.artifact_store import ArtifactStore

TOKEN_PATTERN = re.compile(r"\w+", flags=re.UNICODE)


class Bm25Arguments(ContractModel):
    query: str = Field(min_length=1)
    top_k: int = Field(gt=0)
    text_field: str = Field(default="text", min_length=1)
    output_artifact_id: str = Field(min_length=1)
    k1: float = Field(default=1.5, gt=0)
    b: float = Field(default=0.75, ge=0, le=1)


def _tokenize(text: str) -> list[str]:
    return TOKEN_PATTERN.findall(text.casefold())


def _bm25_scores(
    documents: list[list[str]], query: list[str], *, k1: float, b: float
) -> list[float]:
    if not documents:
        return []
    average_length = sum(len(document) for document in documents) / len(documents)
    average_length = average_length or 1.0
    document_frequency = Counter(token for document in documents for token in set(document))
    term_frequencies = [Counter(document) for document in documents]
    scores: list[float] = []
    for document, frequencies in zip(documents, term_frequencies, strict=True):
        score = 0.0
        for token in query:
            frequency = frequencies[token]
            if frequency == 0:
                continue
            containing = document_frequency[token]
            inverse_document_frequency = math.log(
                1 + (len(documents) - containing + 0.5) / (containing + 0.5)
            )
            denominator = frequency + k1 * (1 - b + b * len(document) / average_length)
            score += inverse_document_frequency * frequency * (k1 + 1) / denominator
        scores.append(score)
    return scores


def bm25_retrieve_spec() -> OperatorSpec:
    return OperatorSpec(
        operator_id="bm25_retrieve",
        description=(
            "Retrieve complete top-k records with deterministic local BM25. The input must be "
            "a JSON array of objects and text_field must exactly name a declared string field "
            "in its artifact content_schema. Records are returned whole: this operator never "
            "summarizes or truncates long field values, so size top_k for the target model's "
            "context contract."
        ),
        input_schema={
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
            "maxItems": 1,
        },
        argument_schema=Bm25Arguments.model_json_schema(),
        output_schema={"$ref": "ProducedArtifact"},
        capability_requirements=frozenset({"retrieval"}),
    )


def register_retrieval_operators(registry: OperatorRegistry, store: ArtifactStore) -> None:
    def bm25_retrieve(action: SemanticAction) -> dict[str, Any]:
        if len(action.inputs) != 1:
            raise ValueError("bm25_retrieve requires exactly one corpus artifact")
        arguments = Bm25Arguments.model_validate(action.arguments)
        records = load_records(store, action.inputs[0])
        texts: list[str] = []
        for record in records:
            text = record.get(arguments.text_field)
            if not isinstance(text, str):
                raise ValueError(f"document field must be text: {arguments.text_field}")
            texts.append(text)
        scores = _bm25_scores(
            [_tokenize(text) for text in texts],
            _tokenize(arguments.query),
            k1=arguments.k1,
            b=arguments.b,
        )
        ranked_indices = sorted(
            range(len(records)),
            key=lambda index: (-scores[index], index),
        )[: arguments.top_k]
        output = [{**records[index], "_bm25_score": scores[index]} for index in ranked_indices]
        return store_json(store, arguments.output_artifact_id, output).model_dump()

    registry.register(bm25_retrieve_spec(), bm25_retrieve)
