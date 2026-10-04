from collections import Counter
from dataclasses import replace

import pytest

from infra_joint.experiments.large_scale_protocol import (
    FAMILIES,
    METHODS,
    PhaseOneGate,
    SelectedTask,
    phase_one_schedule,
    phase_two_schedule,
    schedule_sha256,
    validate_task_set,
)


def tasks() -> tuple[SelectedTask, ...]:
    # Synthetic IDs test the accounting, not an actual frozen benchmark selection.
    return tuple(SelectedTask(family, f"synthetic-{family}-{position}", position)
                 for family in FAMILIES for position in range(1, 7))


def test_exact_factorization_unique_cells_and_deterministic_seed() -> None:
    schedule = phase_one_schedule(tasks(), e_history_tasks=())
    assert len(schedule) == len({cell.cell_id for cell in schedule}) == 168
    assert Counter(cell.method for cell in schedule) == dict.fromkeys(METHODS, 24)
    assert sorted(Counter(cell.planner for cell in schedule).values()) == [84, 84]
    assert sorted(Counter(cell.network for cell in schedule).values()) == [84, 84]
    assert set(Counter((cell.task, cell.planner, cell.network)
                       for cell in schedule).values()) == {7}
    assert schedule_sha256(schedule) == schedule_sha256(
        phase_one_schedule(reversed(tasks()), e_history_tasks=()))
    assert schedule_sha256(schedule) != schedule_sha256(
        phase_one_schedule(tasks(), e_history_tasks=(), seed=4))


def test_each_block_balances_planner_network_and_rotates_methods() -> None:
    schedule = phase_one_schedule(tasks(), e_history_tasks=())
    for offset in range(0, len(schedule), 4):
        block = schedule[offset:offset + 4]
        assert len({cell.task for cell in block}) == 1
        assert len({(cell.planner, cell.network) for cell in block}) == 4
        assert len({cell.method for cell in block}) == 4
        assert block[0].planner != block[1].planner
        assert block[0].network != block[1].network


@pytest.mark.parametrize("bad", [tasks()[:-1], tasks() + (tasks()[0],),
                                 (tasks()[0],) * 18])
def test_partial_or_duplicate_task_freeze_rejected(bad: tuple[SelectedTask, ...]) -> None:
    with pytest.raises(ValueError):
        phase_one_schedule(bad, e_history_tasks=())


def test_history_independence_includes_phase_two_not_just_screening() -> None:
    heldout = tasks()[-1]
    with pytest.raises(ValueError, match="disjoint"):
        phase_one_schedule(tasks(), e_history_tasks=((heldout.family, heldout.source_task_id),))
    assert validate_task_set(tasks(), e_history_tasks=(("video_mme", "other-task"),)) == tasks()


def gate() -> PhaseOneGate:
    schedule = phase_one_schedule(tasks(), e_history_tasks=())
    return PhaseOneGate(schedule_sha256(schedule), tuple(cell.cell_id for cell in schedule),
                        "1" * 64)


@pytest.mark.parametrize(("survivors", "total"), [
    (("B0", "B1", "A"), 312), (("B0", "B1", "A", "B"), 360),
    (("B0", "B1", "A", "B", "E"), 408),
])
def test_phase_two_remaining_tasks_and_total_cap(survivors: tuple, total: int) -> None:
    schedule = phase_two_schedule(tasks(), methods=survivors, gate=gate(),
                                  e_history_tasks=(), pruning_manifest_sha256="2" * 64)
    assert len(schedule) + 168 == total
    assert all(cell.phase == 2 and cell.task.position > 2 for cell in schedule)
    assert len({cell.cell_id for cell in schedule}) == len(schedule)


@pytest.mark.parametrize("invalid", [
    replace(gate(), completed_cell_ids=gate().completed_cell_ids[:-1]),
    replace(gate(), completed_cell_ids=(gate().completed_cell_ids[0],) * 168),
    replace(gate(), schedule_sha256="0" * 64),
    replace(gate(), comprehensive_audit_sha256="unknown"),
    replace(gate(), unresolved_confounders=("privacy",)),
])
def test_phase_two_cannot_bypass_audit_gate(invalid: PhaseOneGate) -> None:
    with pytest.raises(ValueError):
        phase_two_schedule(tasks(), methods=("B0", "B1", "A"), gate=invalid,
                           e_history_tasks=(), pruning_manifest_sha256="2" * 64)


def test_six_full_expansions_exceed_cap_and_duplicate_methods_rejected() -> None:
    for survivors in (METHODS[:6], ("B0", "B0")):
        with pytest.raises(ValueError):
            phase_two_schedule(tasks(), methods=survivors, gate=gate(),
                               e_history_tasks=(), pruning_manifest_sha256="2" * 64)
