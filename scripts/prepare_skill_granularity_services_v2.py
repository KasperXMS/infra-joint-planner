"""Render three isolated Ollama 0.34.0 single-slot services from the v1 owner."""

from pathlib import Path

SOURCE = Path(__file__).with_name("skill_granularity_service_v1.py")
BASE = "/home/super/xiaoming/skill-granularity-pilot-v2/run-001"
EDGE = "/mnt/ssd/skill-granularity-pilot-v2/run-001"


def render(slot: int) -> str:
    assert slot in range(3)
    source = SOURCE.read_text(encoding="utf-8")
    source = source.replace(
        "/home/super/xiaoming/skill-granularity-pilot-v1/run-001",
        f"{BASE}/replica-{slot}",
    )
    source = source.replace(
        "/mnt/ssd/skill-granularity-pilot-v1/run-001/planner-service-001",
        f"{EDGE}/planner-replica-{slot}",
    )
    # One real runner slot per service: Ollama 0.34.0 overrides parallel=3
    # for the qwen35 architecture. Separate processes provide independent slots.
    source = source.replace("127.0.0.1:11450", f"127.0.0.1:{11460 + 10 * slot}")
    source = source.replace("127.0.0.1:11451", f"127.0.0.1:{11461 + 10 * slot}")
    source = source.replace("127.0.0.1:11452", f"127.0.0.1:{11462 + 10 * slot}")
    source = source.replace("11450", str(11460 + 10 * slot))
    source = source.replace("11451", str(11461 + 10 * slot))
    source = source.replace("11452", str(11462 + 10 * slot))
    source = source.replace(
        "assert mem['MemAvailable']>=16*1024**2",
        "assert mem['MemAvailable']>=8*1024**2",
    )
    source = source.replace(
        "for port in (11451, 11452):",
        f"for port in ({11461 + 10 * slot}, {11462 + 10 * slot}):",
    )
    return source


if __name__ == "__main__":
    for index in range(3):
        path = SOURCE.with_name(f"skill_granularity_service_v2_slot{index}.py")
        path.write_text(render(index), encoding="utf-8")
        print(path)
