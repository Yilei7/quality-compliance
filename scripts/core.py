#!/usr/bin/env python3
"""JSON transport for the agent-independent quality-compliance engine."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from common import initialize_data_dir, resolve_data_dir
from engine import ComplianceError, confirm_baseline, diagnose_baseline, onboard, record_evidence, run_check


def dispatch(data_dir: Path, operation: str, payload: dict[str, Any]) -> dict[str, Any]:
    if operation == "onboard":
        return onboard(data_dir, payload)
    if operation == "diagnose":
        return diagnose_baseline(data_dir)
    if operation == "confirm-baseline":
        return confirm_baseline(data_dir, payload.get("reviewer"))
    if operation == "check":
        return run_check(data_dir, payload.get("warning_days", 30), payload.get("red_only", False))
    if operation == "record-evidence":
        return record_evidence(data_dir, payload.get("task_id"), payload.get("evidence_path"), payload.get("complete", False))
    raise ComplianceError("unknown_operation", f"Unknown operation: {operation}")


def write_response(content: dict[str, Any]) -> None:
    json.dump(content, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="runtime data directory; defaults to QUALITY_COMPLIANCE_HOME or ~/.quality-compliance")
    args = parser.parse_args()
    operation: object = None
    try:
        request = json.load(sys.stdin)
        if not isinstance(request, dict):
            raise ComplianceError("invalid_request", "Request must be a JSON object.")
        operation = request.get("operation")
        if request.get("version") != 1:
            raise ComplianceError("unsupported_version", "Request version must be 1.")
        if not isinstance(operation, str) or not operation:
            raise ComplianceError("invalid_request", "operation must be a non-empty string.")
        payload = request.get("payload", {})
        if not isinstance(payload, dict):
            raise ComplianceError("invalid_request", "payload must be a JSON object.")
        data_dir = initialize_data_dir(resolve_data_dir(args.data_dir))
        result = dispatch(data_dir, operation, payload)
        write_response({"ok": True, "version": 1, "operation": operation, "result": result})
    except json.JSONDecodeError as error:
        write_response({"ok": False, "version": 1, "operation": operation, "error": {"code": "invalid_json", "message": str(error), "details": []}})
        raise SystemExit(2) from error
    except ComplianceError as error:
        write_response({"ok": False, "version": 1, "operation": operation, "error": {"code": error.code, "message": error.message, "details": error.details}})
        raise SystemExit(2) from error
    except OSError as error:
        write_response({"ok": False, "version": 1, "operation": operation, "error": {"code": "io_error", "message": str(error), "details": []}})
        raise SystemExit(3) from error
    except SystemExit as error:
        write_response({"ok": False, "version": 1, "operation": operation, "error": {"code": "data_error", "message": str(error), "details": []}})
        raise SystemExit(3) from error
    except Exception as error:
        write_response({"ok": False, "version": 1, "operation": operation, "error": {"code": "internal_error", "message": "The core engine could not complete the operation.", "details": []}})
        raise SystemExit(3) from error


if __name__ == "__main__":
    main()
