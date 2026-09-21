import json
from datetime import datetime
from pathlib import Path
from typing import Any

from pydantic import Field

from infra_joint.core.base import ContractModel


class TraceEvent(ContractModel):
    run_id: str = Field(min_length=1)
    step_id: str = Field(min_length=1)
    parent_id: str | None = None
    event_type: str = Field(min_length=1)
    timestamp: datetime
    payload: dict[str, Any] = Field(default_factory=dict)


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
