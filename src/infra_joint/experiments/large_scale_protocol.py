"""Prospective matrix accounting; no Agent, scheduler or execution behavior changes."""

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from typing import Literal

Family = Literal["multihop_rag", "longbench_v2", "video_mme"]
Method = Literal["B0", "B1", "A", "B", "C", "D", "E"]
Planner = Literal["deepseek-v4-pro", "qwen3.8-max"]
Network = Literal["fast", "slow"]

FAMILIES: tuple[Family, ...] = ("multihop_rag", "longbench_v2", "video_mme")
METHODS: tuple[Method, ...] = ("B0", "B1", "A", "B", "C", "D", "E")
PLANNERS: tuple[Planner, ...] = ("deepseek-v4-pro", "qwen3.8-max")
NETWORKS: tuple[Network, ...] = ("fast", "slow")
SEED = 20261005
PHASE_ONE_CELLS = 168
GLOBAL_CAP = 420


@dataclass(frozen=True)
class SelectedTask:
    """Opaque original task identity and pre-outcome representative position."""

    family: Family
    source_task_id: str
    position: int


@dataclass(frozen=True)
class ScheduledCell:
    phase: Literal[1, 2]
    task: SelectedTask
    planner: Planner
    network: Network
    method: Method
    round_index: int

    @property
    def cell_id(self) -> str:
        # IDs never embed questions/answers/private metadata, or physical identity.
        task_id = hashlib.sha256(self.task.source_task_id.encode()).hexdigest()[:16]
        planner_id = "p1" if self.planner == PLANNERS[0] else "p2"
        return (f"phase{self.phase}-{self.task.family}-{self.task.position}-{task_id}"
                f"-{planner_id}-{self.network}-{self.method}")


@dataclass(frozen=True)
class PhaseOneGate:
    """Hash-bound admission receipt, to be populated by the remote audit, not an Agent."""

    schedule_sha256: str
    completed_cell_ids: tuple[str, ...]
    comprehensive_audit_sha256: str
    unresolved_confounders: tuple[str, ...] = ()


def validate_task_set(
    tasks: Iterable[SelectedTask], *, e_history_tasks: Iterable[tuple[Family, str]],
) -> tuple[SelectedTask, ...]:
    selected = tuple(tasks)
    if len(selected) != 18:
        raise ValueError("freeze all 18 tasks before constructing either phase")
    identities = {(task.family, task.source_task_id) for task in selected}
    if len(identities) != 18 or any(not task.source_task_id.strip() for task in selected):
        raise ValueError("18 distinct nonempty original task identities required")
    if any(task.family not in FAMILIES for task in selected):
        raise ValueError("only the three declared benchmark families are allowed")
    for family in FAMILIES:
        positions = sorted(task.position for task in selected if task.family == family)
        if positions != list(range(1, 7)):
            raise ValueError("each family requires exactly six pre-outcome positions")
    if identities.intersection(e_history_tasks):
        raise ValueError("E distillation history must be disjoint from all evaluation tasks")
    return tuple(sorted(selected, key=lambda task: (FAMILIES.index(task.family), task.position)))


def _order_key(seed: int, label: str) -> str:
    return hashlib.sha256(f"{seed}:{label}".encode()).hexdigest()


def _schedule(
    tasks: tuple[SelectedTask, ...], phase: Literal[1, 2],
    methods: tuple[Method, ...], seed: int,
) -> tuple[ScheduledCell, ...]:
    cells: list[ScheduledCell] = []
    # Each four-cell block balances P×H exactly, instead of processing one provider
    # or network for a whole task/method. Rotate Latin assignments across rounds:
    # every task/P/H sees every method once, without contiguous method-only sweeps.
    pairs: tuple[tuple[Planner, Network], ...] = (
        (PLANNERS[0], "fast"), (PLANNERS[1], "slow"),
        (PLANNERS[0], "slow"), (PLANNERS[1], "fast"),
    )
    for round_index in range(len(methods)):
        task_order = sorted(tasks, key=lambda task: _order_key(
            seed, f"{phase}:{round_index}:{task.family}:{task.position}"))
        for task in task_order:
            offset = (FAMILIES.index(task.family) * 6 + task.position - 1) % len(methods)
            pair_order = pairs if (round_index + task.position) % 2 == 0 else pairs[::-1]
            for planner, network in pair_order:
                pair_index = pairs.index((planner, network))
                method = methods[(round_index + offset + pair_index) % len(methods)]
                cells.append(ScheduledCell(phase, task, planner, network, method, round_index))
    if len({cell.cell_id for cell in cells}) != len(cells):
        raise ValueError("cell identity collision")
    return tuple(cells)


def phase_one_schedule(
    tasks: Iterable[SelectedTask], *, e_history_tasks: Iterable[tuple[Family, str]],
    seed: int = SEED,
) -> tuple[ScheduledCell, ...]:
    selected = validate_task_set(tasks, e_history_tasks=e_history_tasks)
    return _schedule(tuple(task for task in selected if task.position <= 2), 1, METHODS, seed)


def schedule_sha256(cells: Iterable[ScheduledCell]) -> str:
    rows = [{"cell_id": cell.cell_id, **asdict(cell)} for cell in cells]
    payload = json.dumps(rows, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def phase_two_schedule(
    tasks: Iterable[SelectedTask], *, methods: Iterable[Method], gate: PhaseOneGate,
    e_history_tasks: Iterable[tuple[Family, str]], pruning_manifest_sha256: str,
    seed: int = SEED,
    prior_substantive_cells: int = 0,
) -> tuple[ScheduledCell, ...]:
    history = tuple(e_history_tasks)
    selected = validate_task_set(tasks, e_history_tasks=history)
    expected = phase_one_schedule(selected, e_history_tasks=history, seed=seed)
    if (gate.schedule_sha256 != schedule_sha256(expected)
            or len(gate.completed_cell_ids) != PHASE_ONE_CELLS
            or set(gate.completed_cell_ids) != {cell.cell_id for cell in expected}):
        raise ValueError("Phase II requires all 168 exact Phase I cell admissions")
    if gate.unresolved_confounders:
        raise ValueError("unresolved implementation confounders prohibit Phase II")
    for digest in (gate.comprehensive_audit_sha256, pruning_manifest_sha256):
        if re.fullmatch(r"[0-9a-f]{64}", digest) is None:
            raise ValueError("Phase II requires frozen comprehensive audit and pruning hashes")
    survivors = tuple(methods)
    if not survivors or len(set(survivors)) != len(survivors):
        raise ValueError("unique preregistered surviving methods required")
    if any(method not in METHODS for method in survivors):
        raise ValueError("new methods cannot enter Phase II")
    if type(prior_substantive_cells) is not int or prior_substantive_cells < 0:
        raise ValueError("prior substantive cells must be a nonnegative integer")
    if prior_substantive_cells + PHASE_ONE_CELLS + 48 * len(survivors) > GLOBAL_CAP:
        raise ValueError("complete Phase II expansion exceeds 420 substantive cells")
    return _schedule(tuple(task for task in selected if task.position > 2), 2, survivors, seed)
