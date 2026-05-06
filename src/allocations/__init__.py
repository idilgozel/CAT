"""Tools for assigning workers to jobs."""

from allocations.io import (
    catal_entries,
    dumps_catal,
    loads_catal,
    read_catal,
    read_wkab,
    write_catal,
)
from allocations.matrix import (
    AssignmentResult,
    allocate_workers,
    assignment_matrix,
    expanded_jobs,
)
from allocations.models import (
    AllocationError,
    InfeasibleAssignmentError,
    InvalidWorkerDataError,
    Metric,
    Worker,
)
from allocations.solvers import (
    allocation_penalty,
    exhaustive,
    greedy,
    greedy_reverse,
    hungarian,
    solve,
)

__all__ = [
    "AllocationError",
    "AssignmentResult",
    "InfeasibleAssignmentError",
    "InvalidWorkerDataError",
    "Metric",
    "Worker",
    "allocate_workers",
    "allocation_penalty",
    "assignment_matrix",
    "catal_entries",
    "dumps_catal",
    "expanded_jobs",
    "exhaustive",
    "greedy",
    "greedy_reverse",
    "hungarian",
    "loads_catal",
    "read_catal",
    "read_wkab",
    "solve",
    "write_catal",
]

