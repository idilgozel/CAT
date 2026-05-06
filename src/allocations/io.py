"""Read .wkab files and write .catal files."""

from __future__ import annotations

import json
from collections import OrderedDict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from allocations.matrix import AssignmentResult
from allocations.models import InvalidWorkerDataError, Worker


def read_wkab(path: str | Path) -> list[Worker]:
    """Read a .wkab JSON file into validated workers."""

    with Path(path).open(encoding="utf-8") as handle:
        data = json.load(handle)
    return workers_from_data(data)


def workers_from_data(data: Any) -> list[Worker]:
    """Validate decoded .wkab data and return workers."""

    if not isinstance(data, list):
        raise InvalidWorkerDataError("the top-level .wkab item must be a list")
    if not data:
        raise InvalidWorkerDataError("a .wkab file must contain at least one worker")

    workers: list[Worker] = []
    seen_ids: set[str] = set()
    job_count: int | None = None

    for index, item in enumerate(data):
        if not isinstance(item, Mapping):
            raise InvalidWorkerDataError(f"worker entry {index} must be a JSON object")
        worker = Worker.from_mapping(item)
        if worker.id in seen_ids:
            raise InvalidWorkerDataError(f"duplicate worker id {worker.id!r}")
        seen_ids.add(worker.id)

        if job_count is None:
            job_count = worker.job_count
        elif worker.job_count != job_count:
            raise InvalidWorkerDataError("all workers must define the same number of jobs")

        workers.append(worker)

    return workers


def catal_entries(
    workers: Sequence[Worker],
    result: AssignmentResult,
) -> "OrderedDict[str, dict[str, float | int]]":
    """Create the top-level .catal mapping for assigned workers."""

    worker_list = list(workers)
    worker_to_job = result.worker_to_job
    entries: "OrderedDict[str, dict[str, float | int]]" = OrderedDict()

    for worker_index, worker in enumerate(worker_list):
        if worker_index not in worker_to_job:
            continue
        job = worker_to_job[worker_index]
        penalty = worker.penalty_values(result.metric)[job]
        entries[worker.id] = {"job": job, "penalty": penalty}

    return entries


def write_catal(
    path: str | Path,
    workers: Sequence[Worker],
    result: AssignmentResult,
) -> None:
    """Write an allocation result to a .catal file."""

    Path(path).write_text(dumps_catal(catal_entries(workers, result)), encoding="utf-8")


def read_catal(path: str | Path) -> dict[str, dict[str, float | int]]:
    """Read a simple .catal file produced by this package."""

    return loads_catal(Path(path).read_text(encoding="utf-8"))


def dumps_catal(entries: Mapping[str, Mapping[str, float | int]]) -> str:
    """Serialise .catal entries to the required YAML-style format."""

    lines: list[str] = []
    for worker_id, values in entries.items():
        _validate_worker_id(worker_id)
        job = values["job"]
        penalty = values["penalty"]
        lines.append(f"{worker_id}:")
        lines.append(f"    job: {int(job)}")
        lines.append(f"    penalty: {_format_number(float(penalty))}")
    return "\n".join(lines) + ("\n" if lines else "")


def loads_catal(text: str) -> dict[str, dict[str, float | int]]:
    """Parse the simple .catal structure used by the assignment."""

    result: dict[str, dict[str, float | int]] = {}
    current_worker: str | None = None

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        if not raw_line.strip():
            continue
        if not raw_line.startswith(" "):
            if not raw_line.endswith(":"):
                raise ValueError(f"line {line_number}: expected a worker id followed by ':'")
            current_worker = raw_line[:-1]
            _validate_worker_id(current_worker)
            result[current_worker] = {}
            continue

        if current_worker is None:
            raise ValueError(f"line {line_number}: found field before any worker id")
        stripped = raw_line.strip()
        if ":" not in stripped:
            raise ValueError(f"line {line_number}: expected a key/value pair")
        key, value = (part.strip() for part in stripped.split(":", 1))
        if key == "job":
            result[current_worker]["job"] = int(value)
        elif key == "penalty":
            result[current_worker]["penalty"] = float(value)
        else:
            raise ValueError(f"line {line_number}: unknown .catal field {key!r}")

    for worker_id, values in result.items():
        if set(values) != {"job", "penalty"}:
            raise ValueError(f"worker {worker_id!r} must contain job and penalty fields")
    return result


def _format_number(value: float) -> str:
    if value.is_integer():
        return f"{value:.1f}"
    return repr(value)


def _validate_worker_id(worker_id: str) -> None:
    if not worker_id or ":" in worker_id or "\n" in worker_id:
        raise ValueError(f"worker id {worker_id!r} cannot be represented in .catal format")

