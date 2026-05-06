"""Assignment problem solvers."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from itertools import permutations
from math import inf

from allocations.models import InfeasibleAssignmentError

Matrix = Sequence[Sequence[float]]
SlotAssignment = list[int]

_EPSILON = 1e-12


def solve(matrix: Matrix, solver: str = "hungarian") -> SlotAssignment:
    """Solve an assignment matrix using a named solver.

    The input matrix is worker-major: ``matrix[worker][job_slot]`` is the
    penalty for assigning that worker to that job slot. The return value is a
    list indexed by job slot whose values are worker indexes.
    """

    if solver == "exhaustive":
        return exhaustive(matrix)
    if solver == "greedy":
        return greedy(matrix)
    if solver == "greedy-reverse":
        return greedy_reverse(matrix)
    if solver == "hungarian":
        return hungarian(matrix)
    raise ValueError(
        "unknown solver "
        f"{solver!r}; expected one of 'exhaustive', 'greedy', 'greedy-reverse', 'hungarian'"
    )


def exhaustive(matrix: Matrix) -> SlotAssignment:
    """Try every possible worker-to-slot assignment and return the best one."""

    rows = _coerce_matrix(matrix)
    worker_count, slot_count = _shape(rows)
    _ensure_feasible(worker_count, slot_count)

    if slot_count == 0:
        return []

    best_assignment: tuple[int, ...] | None = None
    best_penalty = inf
    for assignment in permutations(range(worker_count), slot_count):
        penalty = sum(rows[worker][slot] for slot, worker in enumerate(assignment))
        if (
            penalty < best_penalty - _EPSILON
            or abs(penalty - best_penalty) <= _EPSILON
            and (best_assignment is None or assignment < best_assignment)
        ):
            best_penalty = penalty
            best_assignment = assignment

    if best_assignment is None:
        return []
    return list(best_assignment)


def greedy(matrix: Matrix, *, reverse: bool = False) -> SlotAssignment:
    """Assign each slot to the lowest-penalty unassigned worker.

    Ties are resolved by choosing the smallest worker index, matching the
    greedy solver described in the assignment material.
    """

    rows = _coerce_matrix(matrix)
    worker_count, slot_count = _shape(rows)
    _ensure_feasible(worker_count, slot_count)

    assignment = [-1] * slot_count
    available_workers = set(range(worker_count))
    slot_order = range(slot_count - 1, -1, -1) if reverse else range(slot_count)

    for slot in slot_order:
        worker = min(available_workers, key=lambda candidate: (rows[candidate][slot], candidate))
        assignment[slot] = worker
        available_workers.remove(worker)

    return assignment


def greedy_reverse(matrix: Matrix) -> SlotAssignment:
    """Run the greedy solver from the final slot to the first slot."""

    return greedy(matrix, reverse=True)


def hungarian(matrix: Matrix) -> SlotAssignment:
    """Return an optimal assignment using the Hungarian algorithm.

    The implementation solves rectangular minimisation problems where the
    number of job slots is no greater than the number of workers.
    """

    rows = _coerce_matrix(matrix)
    worker_count, slot_count = _shape(rows)
    _ensure_feasible(worker_count, slot_count)

    if slot_count == 0:
        return []

    # The standard rectangular implementation assigns each row to a column.
    # Our public matrix is worker-major, so transpose to slot-major costs.
    costs = [[rows[worker][slot] for worker in range(worker_count)] for slot in range(slot_count)]
    return _hungarian_rows_to_columns(costs)


def allocation_penalty(matrix: Matrix, assignment: Sequence[int]) -> float:
    """Calculate the total penalty for an assignment."""

    rows = _coerce_matrix(matrix)
    worker_count, slot_count = _shape(rows)
    if len(assignment) != slot_count:
        raise ValueError(
            f"assignment length {len(assignment)} does not match job slot count {slot_count}"
        )

    seen_workers: set[int] = set()
    total = 0.0
    for slot, worker in enumerate(assignment):
        if not isinstance(worker, int):
            raise ValueError(f"worker index for slot {slot} must be an integer")
        if not 0 <= worker < worker_count:
            raise ValueError(f"worker index {worker} for slot {slot} is out of range")
        if worker in seen_workers:
            raise ValueError(f"worker index {worker} is assigned more than once")
        seen_workers.add(worker)
        total += rows[worker][slot]
    return total


def _hungarian_rows_to_columns(costs: Sequence[Sequence[float]]) -> SlotAssignment:
    row_count = len(costs)
    column_count = len(costs[0]) if row_count else 0

    potentials_rows = [0.0] * (row_count + 1)
    potentials_columns = [0.0] * (column_count + 1)
    matching = [0] * (column_count + 1)
    previous_column = [0] * (column_count + 1)

    for row in range(1, row_count + 1):
        matching[0] = row
        current_column = 0
        min_values = [inf] * (column_count + 1)
        used = [False] * (column_count + 1)

        while True:
            used[current_column] = True
            matched_row = matching[current_column]
            delta = inf
            next_column = 0

            for column in range(1, column_count + 1):
                if used[column]:
                    continue
                current = (
                    costs[matched_row - 1][column - 1]
                    - potentials_rows[matched_row]
                    - potentials_columns[column]
                )
                if current < min_values[column] - _EPSILON:
                    min_values[column] = current
                    previous_column[column] = current_column
                if min_values[column] < delta - _EPSILON:
                    delta = min_values[column]
                    next_column = column

            for column in range(0, column_count + 1):
                if used[column]:
                    potentials_rows[matching[column]] += delta
                    potentials_columns[column] -= delta
                else:
                    min_values[column] -= delta

            current_column = next_column
            if matching[current_column] == 0:
                break

        while True:
            prior_column = previous_column[current_column]
            matching[current_column] = matching[prior_column]
            current_column = prior_column
            if current_column == 0:
                break

    assignment = [-1] * row_count
    for column in range(1, column_count + 1):
        row = matching[column]
        if row:
            assignment[row - 1] = column - 1

    if any(worker < 0 for worker in assignment):
        raise RuntimeError("Hungarian solver failed to assign every job slot")
    return assignment


def _coerce_matrix(matrix: Matrix) -> list[list[float]]:
    rows: list[list[float]] = []
    expected_width: int | None = None
    for row_index, row in enumerate(matrix):
        values = list(row)
        if expected_width is None:
            expected_width = len(values)
        elif len(values) != expected_width:
            raise ValueError("assignment matrix rows must all have the same length")

        numeric_values: list[float] = []
        for column_index, value in enumerate(values):
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(
                    "assignment matrix contains a non-numeric value at "
                    f"row {row_index}, column {column_index}"
                )
            numeric_values.append(float(value))
        rows.append(numeric_values)
    return rows


def _shape(rows: Sequence[Sequence[float]]) -> tuple[int, int]:
    if not rows:
        return 0, 0
    return len(rows), len(rows[0])


def _ensure_feasible(worker_count: int, slot_count: int) -> None:
    if worker_count < slot_count:
        raise InfeasibleAssignmentError(
            f"cannot assign {slot_count} job slots with only {worker_count} workers"
        )

