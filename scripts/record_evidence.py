#!/usr/bin/env python3
"""Record task evidence through the core engine."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import resolve_data_dir
from engine import ComplianceError, record_evidence


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id")
    parser.add_argument("evidence_path", help="path relative to runtime data directory; must be inside evidence/")
    parser.add_argument("--complete", action="store_true", help="mark the task completed after recording evidence")
    parser.add_argument("--data-dir", type=Path, help="runtime data directory; defaults to QUALITY_COMPLIANCE_HOME or ~/.quality-compliance")
    args = parser.parse_args()
    try:
        result = record_evidence(resolve_data_dir(args.data_dir), args.task_id, args.evidence_path, args.complete)
    except ComplianceError as error:
        raise SystemExit(error.message) from error
    task = result["task"]
    print(f"Recorded evidence for {task['task_id']}." + (" Task marked completed." if args.complete else ""))


if __name__ == "__main__":
    main()
