"""Command-line interface for the allocations package."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Sequence

from allocations.io import read_wkab, write_catal
from allocations.matrix import allocate_workers
from allocations.models import AllocationError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="allocations",
        description="Assign CAT workers from a .wkab file and write a .catal allocation.",
    )
    parser.add_argument("input", type=Path, help="Path to the input .wkab JSON file.")
    parser.add_argument("output", type=Path, help="Path to write the output .catal file.")
    parser.add_argument(
        "--metric",
        choices=("cost", "skill", "time"),
        default="cost",
        help="Penalty metric to optimise. Skill uses the negated skill score.",
    )
    parser.add_argument(
        "--solver",
        choices=("hungarian", "exhaustive", "greedy", "greedy-reverse"),
        default="hungarian",
        help="Solver to use.",
    )
    parser.add_argument(
        "--requirements",
        "-r",
        type=_parse_requirements,
        help="Comma-separated non-negative counts for each original job, e.g. 1,2,1.",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print the total penalty and number of assigned workers.",
    )

    args = parser.parse_args(argv)

    try:
        workers = read_wkab(args.input)
        result = allocate_workers(
            workers,
            metric=args.metric,
            requirements=args.requirements,
            solver=args.solver,
        )
        write_catal(args.output, workers, result)
    except (AllocationError, OSError, ValueError) as exc:
        parser.exit(2, f"allocations: error: {exc}\n")

    if args.summary:
        print(
            f"assigned {len(result.slot_assignment)} worker(s); "
            f"total {args.metric} penalty {result.total_penalty:g}"
        )
    return 0


def _parse_requirements(value: str) -> tuple[int, ...]:
    if not value.strip():
        raise argparse.ArgumentTypeError("requirements must not be empty")

    requirements: list[int] = []
    for index, raw_item in enumerate(value.split(",")):
        item = raw_item.strip()
        if not item:
            raise argparse.ArgumentTypeError(
                f"requirement {index} is empty; use comma-separated integers"
            )
        try:
            count = int(item)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"requirement {index} must be an integer"
            ) from exc
        if count < 0:
            raise argparse.ArgumentTypeError(
                f"requirement {index} must be non-negative"
            )
        requirements.append(count)

    return tuple(requirements)

