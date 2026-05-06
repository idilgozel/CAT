"""Core data types and validation for CAT workers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal, TypeAlias

Metric: TypeAlias = Literal["cost", "skill", "time"]
METRICS: tuple[Metric, ...] = ("cost", "skill", "time")


class AllocationError(Exception):
    """Base class for allocation package errors."""


class InvalidWorkerDataError(ValueError, AllocationError):
    """Raised when a worker record or .wkab file is malformed."""


class InfeasibleAssignmentError(ValueError, AllocationError):
    """Raised when there are more required job slots than workers."""


@dataclass(frozen=True, slots=True)
class Worker:
    """A CAT worker and their per-job penalty source vectors."""

    id: str
    forename: str
    surname: str
    cost: tuple[float, ...]
    skill: tuple[float, ...]
    time: tuple[float, ...]

    @classmethod
    def from_mapping(cls, data: Mapping[str, Any]) -> "Worker":
        """Build a worker from one JSON object in a .wkab file."""

        worker_id = _text_field(data, "id")
        forename = _text_field(data, "forename")
        surname = _text_field(data, "surname")
        cost = _number_vector(data, "cost")
        skill = _number_vector(data, "skill")
        time = _number_vector(data, "time")

        lengths = {len(cost), len(skill), len(time)}
        if len(lengths) != 1:
            raise InvalidWorkerDataError(
                f"worker {worker_id!r} has cost, skill, and time vectors with different lengths"
            )

        return cls(
            id=worker_id,
            forename=forename,
            surname=surname,
            cost=cost,
            skill=skill,
            time=time,
        )

    @property
    def job_count(self) -> int:
        """The number of job types represented by this worker."""

        return len(self.cost)

    def penalty_values(self, metric: Metric) -> tuple[float, ...]:
        """Return the penalty vector for a metric.

        Skill is stored as a competency score in .wkab files, so its penalty is
        the negated skill value.
        """

        if metric == "cost":
            return self.cost
        if metric == "time":
            return self.time
        if metric == "skill":
            return tuple(-value for value in self.skill)
        raise ValueError(f"unknown metric {metric!r}; expected one of {METRICS}")


def _text_field(data: Mapping[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value:
        raise InvalidWorkerDataError(f"worker field {key!r} must be a non-empty string")
    return value


def _number_vector(data: Mapping[str, Any], key: str) -> tuple[float, ...]:
    value = data.get(key)
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise InvalidWorkerDataError(f"worker field {key!r} must be a list of numbers")
    if not value:
        raise InvalidWorkerDataError(f"worker field {key!r} must not be empty")

    numbers: list[float] = []
    for index, item in enumerate(value):
        if isinstance(item, bool) or not isinstance(item, (int, float)):
            raise InvalidWorkerDataError(
                f"worker field {key!r} contains a non-numeric value at index {index}"
            )
        numbers.append(float(item))
    return tuple(numbers)

