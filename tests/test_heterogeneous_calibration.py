import json

import pytest

from infra_joint.heterogeneous.calibration import (
    parse_iperf_throughput_mbps,
    parse_ping_latencies,
    summarize,
)


def test_ping_parser_discards_declared_warmup_only() -> None:
    output = "\n".join(
        (
            "64 bytes from host: icmp_seq=1 ttl=64 time=101 ms",
            "64 bytes from host: icmp_seq=2 ttl=64 time=21.5 ms",
            "64 bytes from host: icmp_seq=3 ttl=64 time=22.5 ms",
        )
    )
    assert parse_ping_latencies(output, warmup_samples=1) == (21.5, 22.5)


def test_iperf_parser_reads_sender_throughput() -> None:
    output = json.dumps({"end": {"sum_sent": {"bits_per_second": 30_500_000}}})
    assert parse_iperf_throughput_mbps(output) == pytest.approx(30.5)


def test_distribution_summary_uses_nearest_rank_percentiles() -> None:
    result = summarize(tuple(float(value) for value in range(1, 101)))
    assert result.mean == pytest.approx(50.5)
    assert result.median == pytest.approx(50.5)
    assert result.p90 == 90
    assert result.p95 == 95
