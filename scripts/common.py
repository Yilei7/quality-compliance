"""Shared helpers for the local quality-compliance MVP."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
STATIC_DATA_DIR = ROOT / "data"
PROFILE_TEMPLATE = STATIC_DATA_DIR / "company_profile.template.json"
TASK_TEMPLATE_LIBRARY = STATIC_DATA_DIR / "task_templates.json"
DEFAULT_DATA_DIR = Path.home() / ".quality-compliance"


def load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError as error:
        raise SystemExit(f"Missing required file: {path}") from error
    except json.JSONDecodeError as error:
        raise SystemExit(f"Invalid JSON in {path}: {error}") from error


def write_json(path: Path, content: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(path.parent, 0o700)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            json.dump(content, handle, ensure_ascii=False, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temporary_name, 0o600)
        os.replace(temporary_name, path)
        os.chmod(path, 0o600)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def resolve_data_dir(value: Path | None = None) -> Path:
    configured = value or (Path(os.environ["QUALITY_COMPLIANCE_HOME"]) if os.environ.get("QUALITY_COMPLIANCE_HOME") else None)
    data_dir = (configured or DEFAULT_DATA_DIR).expanduser().resolve()
    try:
        data_dir.relative_to(ROOT.resolve())
    except ValueError:
        return data_dir
    raise SystemExit("Runtime data directory must be outside the installed skill package.")


def initialize_data_dir(data_dir: Path) -> Path:
    data_dir = resolve_data_dir(data_dir)
    data_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    evidence_dir = data_dir / "evidence"
    evidence_dir.mkdir(exist_ok=True, mode=0o700)
    os.chmod(data_dir, 0o700)
    os.chmod(evidence_dir, 0o700)
    profile_path = data_dir / "company_profile.json"
    if not profile_path.exists():
        write_json(profile_path, load_json(PROFILE_TEMPLATE))
    else:
        profile = load_json(profile_path)
        if int(profile.get("schema_version", 1)) < 2:
            account_ids = {item["name"]: item["id"] for item in load_json(PROFILE_TEMPLATE).get("regulatory_accounts", [])}
            for account in profile.get("regulatory_accounts", []):
                if account.get("name") in account_ids:
                    account["id"] = account_ids[account["name"]]
            profile["schema_version"] = 2
            write_json(profile_path, profile)
    tasks_path = data_dir / "tasks.json"
    task_library = load_json(TASK_TEMPLATE_LIBRARY)
    if not tasks_path.exists():
        write_json(
            tasks_path,
            {
                "schema_version": 1,
                "generated_at": None,
                "profile_name": None,
                "template_library_version": None,
                "regulatory_content_status": task_library.get("regulatory_content_status"),
                "last_qualified_review_at": task_library.get("last_qualified_review_at"),
                "tasks": [],
            },
        )
    else:
        task_document = load_json(tasks_path)
        changed = False
        for key in ("regulatory_content_status", "last_qualified_review_at"):
            if key not in task_document:
                task_document[key] = task_library.get(key)
                changed = True
        source_status = task_document.get("regulatory_content_status")
        for task in task_document.get("tasks", []):
            if "source_status" not in task:
                task["source_status"] = source_status
                changed = True
        if changed:
            write_json(tasks_path, task_document)
    os.chmod(profile_path, 0o600)
    os.chmod(tasks_path, 0o600)
    return data_dir


def get_path(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def parse_date(value: str | None, label: str) -> date:
    if not value:
        raise ValueError(f"{label} is required")
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise ValueError(f"{label} must be YYYY-MM-DD, got {value!r}") from error


def next_due(schedule: dict[str, Any], profile: dict[str, Any], today: date | None = None) -> date:
    today = today or date.today()
    kind = schedule["type"]
    if kind == "profile_date_minus_days":
        anchor = parse_date(get_path(profile, schedule["path"]), schedule["path"])
        return anchor - timedelta(days=int(schedule["days"]))
    if kind == "annual":
        candidate = date(today.year, int(schedule["month"]), int(schedule["day"]))
        return candidate if candidate >= today else date(today.year + 1, int(schedule["month"]), int(schedule["day"]))
    if kind == "monthly":
        day = int(schedule["day"])
        candidate = date(today.year, today.month, day)
        if candidate >= today:
            return candidate
        year, month = (today.year + 1, 1) if today.month == 12 else (today.year, today.month + 1)
        return date(year, month, day)
    raise ValueError(f"Unsupported schedule type: {kind}")


def is_inside_evidence(relative_path: str, data_dir: Path) -> bool:
    evidence_dir = data_dir / "evidence"
    candidate = (data_dir / relative_path).resolve()
    try:
        candidate.relative_to(evidence_dir.resolve())
    except ValueError:
        return False
    return True


def iso_now() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()
