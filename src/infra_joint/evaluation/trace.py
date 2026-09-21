import json
from datetime import datetime
from pathlib import Path
from typing import Any, Protocol

from pydantic import Field, field_validator

from infra_joint.core.base import ContractModel


class TraceEvent(ContractModel):
    run_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    parent_id: str | None = None
    event_type: str = Field(min_length=1)
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_timezone_aware(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("trace timestamp must include a timezone")
        return value


class TraceSink(Protocol):
    def append(self, event: TraceEvent) -> None: ...


class JsonlTraceWriter:
    def __init__(self, path: Path) -> None:
        self._path = path

    def append(self, event: TraceEvent) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        line = event.model_dump_json(by_alias=True)
        with self._path.open("a", encoding="utf-8", newline="\n") as stream:
            stream.write(line)
            stream.write("\n")

    def read_all(self) -> list[dict[str, Any]]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as stream:
            return [json.loads(line) for line in stream if line.strip()]
