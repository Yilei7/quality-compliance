#!/usr/bin/env python3
"""Regenerate task state from an onboarded enterprise profile."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import resolve_data_dir
from engine import ComplianceError, initialize_tasks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="runtime data directory; defaults to QUALITY_COMPLIANCE_HOME or ~/.quality-compliance")
    parser.add_argument("--force", action="store_true", help="replace task state even when it already contains tasks")
    args = parser.parse_args()
    try:
        task_document = initialize_tasks(resolve_data_dir(args.data_dir), force=args.force)
    except ComplianceError as error:
        raise SystemExit(error.message) from error
    print(f"Generated {len(task_document['tasks'])} applicable tasks for {task_document.get('profile_name')}.")


if __name__ == "__main__":
    main()
