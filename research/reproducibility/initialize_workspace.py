"""Initialize the approved research folders without touching production files."""

from __future__ import annotations

import argparse
from pathlib import Path


WORKSPACE_DIRECTORIES = (
    "protocols",
    "literature",
    "datasets",
    "annotation",
    "baselines",
    "ablations",
    "metrics",
    "statistics",
    "xgboost_analysis",
    "user_study",
    "experiments",
    "results",
    "figures",
    "tests",
    "reproducibility",
)


def initialize_workspace(research_root: Path) -> list[Path]:
    """Create only research subdirectories and return their resolved paths."""
    root = research_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    created: list[Path] = []
    for relative_path in WORKSPACE_DIRECTORIES:
        destination = (root / relative_path).resolve()
        destination.relative_to(root)
        destination.mkdir(exist_ok=True)
        created.append(destination)
    return created


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[1]
    )
    args = parser.parse_args()
    for directory in initialize_workspace(args.root):
        print(directory)


if __name__ == "__main__":
    main()
