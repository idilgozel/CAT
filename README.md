# allocations

`allocations` assigns CAT workers to jobs using the assignment problem described in the COMP0233 pre-reading material.

The package reads worker ability files in `.wkab` JSON format, builds an assignment matrix for a chosen penalty metric, solves the assignment, and writes `.catal` YAML-style allocation files.

Full usage, API, file-format, and static example documentation is available in [docs/README.md](docs/README.md).

## Features

- `.wkab` reader with validation for worker IDs and job vectors.
- `.catal` writer and simple reader for the required output shape.
- Cost, time, and skill penalties. Skill is handled as the negated skill value, matching the specification.
- Repeated jobs through job requirements such as `1,2,1`.
- Exhaustive, greedy, reverse-greedy, and Hungarian solvers.
- A command-line interface:

```bash
allocations examples/cat.wkab allocation.catal --metric cost --solver hungarian --requirements 1,2,1 --summary
```

Without an installed console script, run the same CLI from a source checkout as:

```bash
PYTHONPATH=src python -m allocations examples/cat.wkab allocation.catal --metric cost --solver hungarian --requirements 1,2,1 --summary
```

## Python API

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

`result.job_to_workers` maps each original job index to the assigned worker indexes. `result.total_penalty` gives the total penalty for the allocation.

## Development

```bash
python3 -m pytest
python3 -m compileall src tests
```
