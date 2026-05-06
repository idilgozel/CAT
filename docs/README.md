# allocations documentation

`allocations` is a small Python package for assigning CAT workers to jobs. It reads worker ability records from `.wkab` JSON files, creates an assignment matrix, solves the assignment problem, and writes allocation results to `.catal` YAML-style files.

This document covers the command-line interface, Python API, supported static files, input/output formats, solver behavior, and development workflow.

## Project Layout

```text
.
|-- .github/workflows/ci.yml       # GitHub Actions workflow
|-- examples/cat.wkab              # Static example worker ability file
|-- src/allocations/               # Package source
|-- tests/                         # Pytest suite
|-- pyproject.toml                 # Build metadata and package entry point
`-- README.md                      # Short project overview
```

## Installation

For development from a checkout:

```bash
python3 -m pip install -e .
```

If you do not install the package, run commands from the repository root with `PYTHONPATH=src`:

```bash
PYTHONPATH=src python3 -m allocations --help
```

## Quick Start

Use the bundled static example data to solve the repeated-job example from the assignment material:

```bash
PYTHONPATH=src python3 -m allocations \
  examples/cat.wkab \
  allocation.catal \
  --metric cost \
  --solver hungarian \
  --requirements 1,2,1 \
  --summary
```

Expected summary:

```text
assigned 4 worker(s); total cost penalty 3
```

Expected `.catal` output:

```yaml
GF1978:
    job: 0
    penalty: 0.0
DN1994:
    job: 1
    penalty: 0.0
LT1945:
    job: 2
    penalty: 2.0
WH1940:
    job: 1
    penalty: 1.0
```

## Core Concepts

Workers are indexed by their position in the `.wkab` file. Jobs are indexed by position in each worker's `cost`, `skill`, and `time` lists.

The assignment matrix is worker-major:

```python
matrix[worker_index][job_slot_index]
```

The value is the penalty for assigning that worker to that job slot. Lower penalties are better.

Repeated jobs are represented by expanding original jobs into job slots. For example, requirements `1,2,1` means:

```text
original job 0 -> slot 0
original job 1 -> slots 1 and 2
original job 2 -> slot 3
```

The package solves the expanded slot assignment and then maps results back to original job indexes in `.catal` output.

## Metrics

The `--metric` CLI option and `metric` API argument accept:

| Metric | Meaning | Matrix value |
| --- | --- | --- |
| `cost` | Financial cost penalty | `worker.cost[j]` |
| `time` | Time penalty | `worker.time[j]` |
| `skill` | Maximise competency by minimising negative skill | `-worker.skill[j]` |

Skill values are stored as positive competency scores in `.wkab` files. The solver is a minimiser, so skill is converted to a penalty by negating it.

## Input Format: `.wkab`

`.wkab` files are JSON. The top-level item must be a non-empty list. Each worker object must contain:

| Key | Type | Notes |
| --- | --- | --- |
| `id` | string | Unique worker identifier. |
| `forename` | string | Worker forename. |
| `surname` | string | Worker surname. |
| `cost` | list of numbers | Cost penalty per job. |
| `skill` | list of numbers | Skill score per job. |
| `time` | list of numbers | Time penalty per job. |

All workers must define the same number of jobs. For each worker, `cost`, `skill`, and `time` must also have the same length.

Example:

```json
[
  {
    "id": "GF1978",
    "forename": "garfield",
    "surname": "arbuckle",
    "cost": [0, 7, 1],
    "skill": [9, 0, 8],
    "time": [3, 9, 6]
  }
]
```

## Output Format: `.catal`

`.catal` files are YAML-style mappings. The top-level keys are worker IDs. Each assigned worker has:

| Key | Type | Notes |
| --- | --- | --- |
| `job` | integer | Original job index, not expanded slot index. |
| `penalty` | number | Penalty for this worker/job under the chosen metric. |

Unassigned workers are omitted. This can happen when there are more workers than required job slots.

Example:

```yaml
GF1978:
    job: 0
    penalty: 0.0
```

## CLI Reference

After installation:

```bash
allocations INPUT.wkab OUTPUT.catal [options]
```

From a source checkout:

```bash
PYTHONPATH=src python3 -m allocations INPUT.wkab OUTPUT.catal [options]
```

Arguments:

| Argument | Required | Description |
| --- | --- | --- |
| `INPUT.wkab` | yes | Path to the JSON worker ability file. |
| `OUTPUT.catal` | yes | Path to write the allocation file. |

Options:

| Option | Values | Default | Description |
| --- | --- | --- | --- |
| `--metric` | `cost`, `skill`, `time` | `cost` | Penalty metric to optimise. |
| `--solver` | `hungarian`, `exhaustive`, `greedy`, `greedy-reverse` | `hungarian` | Assignment solver. |
| `--requirements`, `-r` | comma-separated integers | one worker per job | Required worker count for each original job. |
| `--summary` | flag | off | Print assignment count and total penalty. |

Examples:

```bash
allocations examples/cat.wkab allocation.catal
allocations examples/cat.wkab allocation.catal --metric time
allocations examples/cat.wkab allocation.catal --solver greedy --requirements 1,2,1
```

## Python API

The package exposes its public API from `allocations`.

### High-Level Allocation

```python
from allocations import allocate_workers, read_wkab, write_catal

workers = read_wkab("examples/cat.wkab")
result = allocate_workers(
    workers,
    metric="cost",
    requirements=[1, 2, 1],
    solver="hungarian",
)
write_catal("allocation.catal", workers, result)
```

### `Worker`

```python
from allocations import Worker

worker = Worker(
    id="GF1978",
    forename="garfield",
    surname="arbuckle",
    cost=(0.0, 7.0, 1.0),
    skill=(9.0, 0.0, 8.0),
    time=(3.0, 9.0, 6.0),
)
```

Important members:

| Member | Description |
| --- | --- |
| `Worker.from_mapping(data)` | Validate and create a worker from decoded JSON data. |
| `worker.job_count` | Number of job types represented by the worker. |
| `worker.penalty_values(metric)` | Return cost, time, or negated skill penalties. |

### `AssignmentResult`

Returned by `allocate_workers`.

| Attribute | Type | Description |
| --- | --- | --- |
| `solver` | `str` | Solver name used. |
| `metric` | `str` | Metric used. |
| `slot_assignment` | `tuple[int, ...]` | Worker index for each expanded job slot. |
| `slot_to_job` | `tuple[int, ...]` | Original job index for each expanded slot. |
| `total_penalty` | `float` | Sum of assigned penalties. |
| `job_to_workers` | `dict[int, list[int]]` | Original job index to assigned worker indexes. |
| `worker_to_job` | `dict[int, int]` | Assigned worker index to original job index. |

### Matrix Functions

```python
from allocations import assignment_matrix, expanded_jobs
```

| Function | Description |
| --- | --- |
| `expanded_jobs(job_count, requirements=None)` | Expand original jobs into slots. |
| `assignment_matrix(workers, metric="cost", requirements=None)` | Return `(matrix, slot_to_job)`. |
| `allocate_workers(workers, metric="cost", requirements=None, solver="hungarian")` | Solve and return `AssignmentResult`. |

### Solver Functions

```python
from allocations import solve, hungarian, exhaustive, greedy, greedy_reverse
```

All solvers accept a worker-major matrix and return a slot assignment list:

```python
matrix = [
    [0, 7, 1],
    [9, 0, 5],
    [3, 3, 2],
    [6, 1, 1],
]

assignment = hungarian(matrix)
assert assignment == [0, 1, 3]
```

Solver behavior:

| Solver | Optimal | Notes |
| --- | --- | --- |
| `hungarian` | yes | Efficient default for rectangular minimisation. |
| `exhaustive` | yes | Tries every assignment; useful for tests and small matrices. |
| `greedy` | no | Processes slots from first to last, choosing the lowest-penalty available worker. |
| `greedy_reverse` | no | Same greedy rule, but processes slots from last to first. |

Supporting function:

```python
from allocations import allocation_penalty

total = allocation_penalty(matrix, assignment)
```

### IO Functions

```python
from allocations import (
    read_wkab,
    read_catal,
    write_catal,
    dumps_catal,
    loads_catal,
    catal_entries,
)
```

| Function | Description |
| --- | --- |
| `read_wkab(path)` | Read and validate a `.wkab` file. |
| `write_catal(path, workers, result)` | Write an `AssignmentResult` to `.catal`. |
| `read_catal(path)` | Read a `.catal` file produced by this package. |
| `dumps_catal(entries)` | Serialise `.catal` mapping text. |
| `loads_catal(text)` | Parse simple `.catal` mapping text. |
| `catal_entries(workers, result)` | Build the worker-ID mapping used for output. |

### Exceptions

| Exception | Raised when |
| --- | --- |
| `AllocationError` | Base package exception. |
| `InvalidWorkerDataError` | `.wkab` data is malformed or inconsistent. |
| `InfeasibleAssignmentError` | Required job slots exceed available workers. |

## Static Files

The repository includes static example data in `examples/`.

| File | Purpose |
| --- | --- |
| `examples/cat.wkab` | Four-worker, three-job example from the assignment material. |

Use this file for manual CLI checks, documentation examples, and regression tests. Generated `.catal` files are intentionally not committed by default because they are command outputs; create them locally when needed.

## Validation Rules

The package validates:

- The `.wkab` top-level value is a non-empty list.
- Every worker entry is an object.
- Worker IDs, forenames, and surnames are non-empty strings.
- Worker IDs are unique.
- `cost`, `skill`, and `time` are non-empty numeric lists.
- All workers define the same number of jobs.
- Requirements are non-negative integers and match the job count.
- The total number of expanded job slots does not exceed the number of workers.
- Assignment matrices are rectangular and numeric.
- A final assignment does not reuse a worker.

## Development

Run tests:

```bash
python3 -m pytest
```

Compile source and tests:

```bash
python3 -m compileall src tests
```

Build the package:

```bash
python3 -m build
```

The GitHub Actions workflow in `.github/workflows/ci.yml` runs these checks on Python 3.10, 3.11, and 3.12 for pushes to `main` and pull requests.

## Troubleshooting

### `No module named allocations`

The package has a `src` layout. Install it first:

```bash
python3 -m pip install -e .
```

Or run from the repository root with:

```bash
PYTHONPATH=src python3 -m allocations --help
```

### `cannot assign N job slots with only W workers`

The requirements expand to more slots than there are workers. Reduce one or more requirements or add more workers to the `.wkab` input.

### Greedy output differs from Hungarian output

This is expected. `greedy` and `greedy_reverse` are heuristic solvers and are not guaranteed to find the minimum total penalty.

