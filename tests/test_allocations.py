from pathlib import Path

import pytest

from allocations import (
    InfeasibleAssignmentError,
    allocate_workers,
    allocation_penalty,
    assignment_matrix,
    exhaustive,
    expanded_jobs,
    greedy,
    hungarian,
    loads_catal,
    read_wkab,
    write_catal,
)


EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "cat.wkab"


def test_read_wkab_and_build_cost_matrix():
    workers = read_wkab(EXAMPLE)

    matrix, slots = assignment_matrix(workers, metric="cost")

    assert [worker.id for worker in workers] == ["GF1978", "DN1994", "LT1945", "WH1940"]
    assert slots == (0, 1, 2)
    assert matrix == [
        [0.0, 7.0, 1.0],
        [9.0, 0.0, 5.0],
        [3.0, 3.0, 2.0],
        [6.0, 1.0, 1.0],
    ]


def test_skill_metric_uses_negated_skill_values():
    workers = read_wkab(EXAMPLE)

    matrix, _ = assignment_matrix(workers, metric="skill")

    assert matrix[0] == [-9.0, -0.0, -8.0]
    assert matrix[1] == [-3.0, -9.0, -5.0]


def test_solvers_find_expected_example_allocation():
    matrix = [
        [0, 7, 1],
        [9, 0, 5],
        [3, 3, 2],
        [6, 1, 1],
    ]

    assert greedy(matrix) == [0, 1, 3]
    assert exhaustive(matrix) == [0, 1, 3]
    assert hungarian(matrix) == [0, 1, 3]
    assert allocation_penalty(matrix, [0, 1, 3]) == 1.0


def test_repeated_jobs_map_back_to_original_job_indexes():
    workers = read_wkab(EXAMPLE)

    result = allocate_workers(
        workers,
        metric="cost",
        requirements=[1, 2, 1],
        solver="hungarian",
    )

    assert result.slot_to_job == (0, 1, 1, 2)
    assert result.slot_assignment == (0, 1, 3, 2)
    assert result.job_to_workers == {0: [0], 1: [1, 3], 2: [2]}
    assert result.total_penalty == 3.0


def test_too_many_jobs_is_infeasible():
    workers = read_wkab(EXAMPLE)

    with pytest.raises(InfeasibleAssignmentError):
        allocate_workers(workers, requirements=[2, 2, 1])


def test_expanded_jobs_allows_zero_requirement():
    assert expanded_jobs(3, requirements=[1, 0, 2]) == (0, 2, 2)


def test_write_and_read_catal_file(tmp_path):
    workers = read_wkab(EXAMPLE)
    result = allocate_workers(workers, requirements=[1, 2, 1])
    output = tmp_path / "allocation.catal"

    write_catal(output, workers, result)

    assert output.read_text(encoding="utf-8") == (
        "GF1978:\n"
        "    job: 0\n"
        "    penalty: 0.0\n"
        "DN1994:\n"
        "    job: 1\n"
        "    penalty: 0.0\n"
        "LT1945:\n"
        "    job: 2\n"
        "    penalty: 2.0\n"
        "WH1940:\n"
        "    job: 1\n"
        "    penalty: 1.0\n"
    )
    assert loads_catal(output.read_text(encoding="utf-8")) == {
        "GF1978": {"job": 0, "penalty": 0.0},
        "DN1994": {"job": 1, "penalty": 0.0},
        "LT1945": {"job": 2, "penalty": 2.0},
        "WH1940": {"job": 1, "penalty": 1.0},
    }

