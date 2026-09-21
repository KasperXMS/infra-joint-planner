"""Benchmark-faithful adapters and validity contracts."""

from infra_joint.benchmarks.base import (
    AdaptationBundle,
    AdaptedExecutionCase,
    BenchmarkSettingKind,
    TransformationRecord,
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
    "TransformationRecord",
    "VideoMMEAdapter",
    "VideoMMESample",
]
