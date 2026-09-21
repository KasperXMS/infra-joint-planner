"""Benchmark-faithful adapters and validity contracts."""

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    BenchmarkSettingKind,
    TransformationRecord,
)
from infra_joint.benchmarks.longbench_v2 import LongBenchV2Adapter, LongBenchV2Sample
from infra_joint.benchmarks.multihop_rag import (
    CandidateSelectionRecord,
    FixedCandidate,
    FixedCandidateSetting,
    FullCorpusSetting,
    MultiHopCorpusDocument,
    MultiHopRAGAdapter,
    MultiHopRAGSample,
)
from infra_joint.benchmarks.video_mme import (
    FixedIntervalSegmentation,
    VideoMMEAdapter,
    VideoMMESample,
)

__all__ = [
    "AdaptationBundle",
    "AdaptedExecutionCase",
    "BenchmarkSettingKind",
    "FixedIntervalSegmentation",
    "CandidateSelectionRecord",
    "FixedCandidate",
    "FixedCandidateSetting",
    "FullCorpusSetting",
    "LongBenchV2Adapter",
    "LongBenchV2Sample",
    "MultiHopCorpusDocument",
    "MultiHopRAGAdapter",
    "MultiHopRAGSample",
    "TransformationRecord",
    "VideoMMEAdapter",
    "VideoMMESample",
]
