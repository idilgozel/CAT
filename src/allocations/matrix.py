"""Build assignment matrices from worker data."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from allocations.models import InfeasibleAssignmentError, InvalidWorkerDataError, Metric, Worker
from allocations.solvers import allocation_penalty, solve


@dataclass(frozen=True, slots=True)
class AssignmentResult:
    """The result of assigning workers to expanded job slots."""

    solver: str
    metric: Metric
    slot_assignment: tuple[int, ...]
    slot_to_job: tuple[int, ...]
    total_penalty: float

    @property
    def job_to_workers(self) -> dict[int, list[int]]:
        """Map original job indexes to the assigned worker indexes."""

        allocation: dict[int, list[int]] = {}
        for slot, worker in enumerate(self.slot_assignment):
            job = self.slot_to_job[slot]
            allocation.setdefault(job, []).append(worker)
        return allocation

    @property
    def worker_to_job(self) -> dict[int, int]:
        """Map assigned worker indexes to original job indexes."""

        return {
            worker: self.slot_to_job[slot]
            for slot, worker in enumerate(self.slot_assignment)
        }


def allocate_workers(
    workers: Sequence[Worker],
    *,
    metric: Metric = "cost",
    requirements: Sequence[int] | None = None,
    solver: str = "hungarian",
) -> AssignmentResult:
    """Assign workers to jobs and return a structured result."""

    matrix, slot_to_job = assignment_matrix(workers, metric=metric, requirements=requirements)
    if len(matrix) < len(slot_to_job):
        raise InfeasibleAssignmentError(
            f"cannot assign {len(slot_to_job)} job slots with only {len(matrix)} workers"
        )

    slot_assignment = solve(matrix, solver=solver)
    total = allocation_penalty(matrix, slot_assignment)
    return AssignmentResult(
        solver=solver,
        metric=metric,
        slot_assignment=tuple(slot_assignment),
        slot_to_job=slot_to_job,
        total_penalty=total,
    )


def assignment_matrix(
    workers: Sequence[Worker],
    *,
    metric: Metric = "cost",
    requirements: Sequence[int] | None = None,
) -> tuple[list[list[float]], tuple[int, ...]]:
    """Create a worker-major assignment matrix and expanded job-slot map."""

    worker_list = list(workers)
    if not worker_list:
        raise InvalidWorkerDataError("at least one worker is required")

    job_count = _validate_workers(worker_list)
    slot_to_job = expanded_jobs(job_count, requirements=requirements)

    matrix = [
        [worker.penalty_values(metric)[job] for job in slot_to_job]
        for worker in worker_list
    ]
    return matrix, slot_to_job


def expanded_jobs(job_count: int, *, requirements: Sequence[int] | None = None) -> tuple[int, ...]:
    """Expand original job indexes according to per-job requirements."""

    if job_count < 0:
        raise ValueError("job_count must be non-negative")

    if requirements is None:
        requirement_values = (1,) * job_count
    else:
        requirement_values = tuple(requirements)
        if len(requirement_values) != job_count:
            raise ValueError(
                f"requirements length {len(requirement_values)} does not match job count {job_count}"
            )

    slots: list[int] = []
    for job, count in enumerate(requirement_values):
        if isinstance(count, bool) or not isinstance(count, int):
            raise ValueError(f"requirement for job {job} must be an integer")
        if count < 0:
            raise ValueError(f"requirement for job {job} must be non-negative")
        slots.extend([job] * count)
    return tuple(slots)


def _validate_workers(workers: Sequence[Worker]) -> int:
    job_count = workers[0].job_count
    for worker in workers:
        if worker.job_count != job_count:
            raise InvalidWorkerDataError(
                "all workers must have cost, skill, and time vectors with the same length"
            )
    return job_count

