"""Agent-independent quality-compliance domain operations."""

from __future__ import annotations

from copy import deepcopy
from datetime import date
from pathlib import Path
from typing import Any

from common import (
    PROFILE_TEMPLATE,
    TASK_TEMPLATE_LIBRARY,
    get_path,
    initialize_data_dir,
    is_inside_evidence,
    iso_now,
    load_json,
    next_due,
    parse_date,
    write_json,
)


class ComplianceError(Exception):
    def __init__(self, code: str, message: str, details: list[dict[str, Any]] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.details = details or []


def _is_placeholder(value: object) -> bool:
    return not value or "示例" in str(value) or "待填写" in str(value) or "XXXX" in str(value)


def _task_is_applicable(template: dict[str, Any], profile: dict[str, Any]) -> bool:
    if profile.get("entity_type") not in template.get("applies_to", []):
        return False
    return all(get_path(profile, path) == expected for path, expected in template.get("requires", {}).items())


def generate_task_document(profile: dict[str, Any]) -> dict[str, Any]:
    if profile.get("entity_type") != "device_distribution" or profile.get("province") != "上海市":
        raise ComplianceError("unsupported_profile", "This MVP supports only Shanghai device_distribution profiles.")
    templates = load_json(TASK_TEMPLATE_LIBRARY)
    tasks = []
    try:
        for template in templates.get("tasks", []):
            if not _task_is_applicable(template, profile):
                continue
            tasks.append(
                {
                    "task_id": template["id"],
                    "title": template["title"],
                    "module": template["module"],
                    "status": "open",
                    "next_due": next_due(template["schedule"], profile).isoformat(),
                    "last_completed": None,
                    "evidence_files": [],
                    "required_evidence": template["required_evidence"],
                    "regulatory_basis": template["regulatory_basis"],
                    "source_ref": template["source_ref"],
                    "source_status": template.get("source_status", templates.get("regulatory_content_status")),
                }
            )
    except (KeyError, TypeError, ValueError) as error:
        raise ComplianceError("invalid_profile", str(error)) from error
    return {
        "schema_version": 1,
        "generated_at": iso_now(),
        "profile_name": profile.get("enterprise_name"),
        "template_library_version": templates.get("library_version"),
        "regulatory_content_status": templates.get("regulatory_content_status"),
        "last_qualified_review_at": templates.get("last_qualified_review_at"),
        "tasks": tasks,
    }


def initialize_tasks(data_dir: Path, force: bool = False) -> dict[str, Any]:
    data_dir = initialize_data_dir(data_dir)
    profile = load_json(data_dir / "company_profile.json")
    tasks_path = data_dir / "tasks.json"
    existing = load_json(tasks_path)
    if existing.get("tasks") and not force:
        raise ComplianceError("state_exists", "Task state already exists; preserve history or explicitly force replacement.")
    task_document = generate_task_document(profile)
    write_json(tasks_path, task_document)
    return task_document


def _required_string(payload: dict[str, Any], key: str, pointer: str, issues: list[dict[str, str]]) -> str | None:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        issues.append({"path": pointer, "message": "must be a non-empty string"})
        return None
    return value.strip()


def onboard(data_dir: Path, payload: dict[str, Any]) -> dict[str, Any]:
    data_dir = initialize_data_dir(data_dir)
    if not isinstance(payload, dict):
        raise ComplianceError("validation_error", "payload must be a JSON object")
    existing_profile = load_json(data_dir / "company_profile.json")
    existing_tasks = load_json(data_dir / "tasks.json")
    has_state = bool(existing_profile.get("enterprise_name") or existing_tasks.get("tasks"))
    if has_state and payload.get("confirm_reset") is not True:
        raise ComplianceError(
            "reset_confirmation_required",
            "Onboarding would replace existing enterprise task state; set confirm_reset to true only after preserving required history.",
        )

    issues: list[dict[str, str]] = []
    enterprise_name = _required_string(payload, "enterprise_name", "/enterprise_name", issues)
    licence_payload = payload.get("licence")
    if not isinstance(licence_payload, dict):
        issues.append({"path": "/licence", "message": "must be an object"})
        licence_payload = {}
    licence_number = _required_string(licence_payload, "number", "/licence/number", issues)
    approval_date = _required_string(licence_payload, "approval_date", "/licence/approval_date", issues)
    expiry_date = _required_string(licence_payload, "expiry_date", "/licence/expiry_date", issues)
    parsed_approval = parsed_expiry = None
    for value, label, pointer in (
        (approval_date, "licence.approval_date", "/licence/approval_date"),
        (expiry_date, "licence.expiry_date", "/licence/expiry_date"),
    ):
        if value:
            try:
                parsed = parse_date(value, label)
                if pointer.endswith("approval_date"):
                    parsed_approval = parsed
                else:
                    parsed_expiry = parsed
            except ValueError:
                issues.append({"path": pointer, "message": "must use YYYY-MM-DD"})
    if parsed_approval and parsed_expiry and parsed_expiry <= parsed_approval:
        issues.append({"path": "/licence/expiry_date", "message": "must be later than approval_date"})

    responsible_payload = payload.get("quality_responsible_person")
    if not isinstance(responsible_payload, dict):
        issues.append({"path": "/quality_responsible_person", "message": "must be an object"})
        responsible_payload = {}
    responsible_name = _required_string(responsible_payload, "name", "/quality_responsible_person/name", issues)
    contact = responsible_payload.get("contact")
    if contact is not None and not isinstance(contact, str):
        issues.append({"path": "/quality_responsible_person/contact", "message": "must be a string or null"})

    conditions_payload = payload.get("operating_conditions", {})
    if not isinstance(conditions_payload, dict):
        issues.append({"path": "/operating_conditions", "message": "must be an object"})
        conditions_payload = {}
    conditions: dict[str, bool] = {}
    for key in ("cold_chain", "third_party_logistics"):
        value = conditions_payload.get(key, False)
        if type(value) is not bool:
            issues.append({"path": f"/operating_conditions/{key}", "message": "must be a boolean"})
        else:
            conditions[key] = value

    account_payload = payload.get("regulatory_accounts", {})
    if not isinstance(account_payload, dict):
        issues.append({"path": "/regulatory_accounts", "message": "must be an object keyed by account id"})
        account_payload = {}
    profile = deepcopy(load_json(PROFILE_TEMPLATE))
    accounts = []
    known_ids = {account["id"] for account in profile.get("regulatory_accounts", [])}
    for unknown_id in set(account_payload) - known_ids:
        issues.append({"path": f"/regulatory_accounts/{unknown_id}", "message": "unknown regulatory account id"})
    for account in profile.get("regulatory_accounts", []):
        submitted = account_payload.get(account["id"], {})
        if not isinstance(submitted, dict):
            issues.append({"path": f"/regulatory_accounts/{account['id']}", "message": "must be an object"})
            submitted = {}
        registered = submitted.get("registered")
        if registered is not None and type(registered) is not bool:
            issues.append({"path": f"/regulatory_accounts/{account['id']}/registered", "message": "must be true, false, or null"})
        last_verified = submitted.get("last_verified")
        if last_verified is not None:
            if not isinstance(last_verified, str):
                issues.append({"path": f"/regulatory_accounts/{account['id']}/last_verified", "message": "must be YYYY-MM-DD or null"})
            else:
                try:
                    parse_date(last_verified, f"regulatory_accounts.{account['id']}.last_verified")
                except ValueError:
                    issues.append({"path": f"/regulatory_accounts/{account['id']}/last_verified", "message": "must use YYYY-MM-DD"})
        account["registered"] = registered
        account["last_verified"] = last_verified
        accounts.append(account)
    if issues:
        raise ComplianceError("validation_error", "Onboarding data is invalid.", issues)

    profile["enterprise_name"] = enterprise_name
    profile["licence"] = {"number": licence_number, "approval_date": approval_date, "expiry_date": expiry_date}
    profile["quality_responsible_person"] = {"name": responsible_name, "contact": contact}
    profile["operating_conditions"] = conditions
    profile["regulatory_accounts"] = accounts
    profile["lifecycle"] = {
        "stage": "onboarding",
        "baseline_diagnosed_at": None,
        "baseline_reviewer": None,
        "updated_at": iso_now(),
    }
    task_document = generate_task_document(profile)
    write_json(data_dir / "company_profile.json", profile)
    write_json(data_dir / "tasks.json", task_document)
    return {
        "profile": profile,
        "tasks_generated": len(task_document["tasks"]),
        "regulatory_content_status": task_document.get("regulatory_content_status"),
    }


def diagnose_findings(profile: dict[str, Any], task_doc: dict[str, Any], data_dir: Path) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    required = {
        "企业名称": profile.get("enterprise_name"),
        "许可证编号": profile.get("licence", {}).get("number"),
        "许可证获批日期": profile.get("licence", {}).get("approval_date"),
        "许可证有效期": profile.get("licence", {}).get("expiry_date"),
        "质量负责人": profile.get("quality_responsible_person", {}).get("name"),
    }
    for label, value in required.items():
        if _is_placeholder(value):
            findings.append({"level": "red", "kind": "profile", "name": label, "reason": "初始建档信息缺失或仍为示例值", "next_action": "补充并由质量负责人确认"})
    try:
        approval = parse_date(profile.get("licence", {}).get("approval_date"), "licence.approval_date")
        expiry = parse_date(profile.get("licence", {}).get("expiry_date"), "licence.expiry_date")
        if expiry <= approval:
            findings.append({"level": "red", "kind": "profile", "name": "许可证日期", "reason": "有效期不得早于或等于获批日期", "next_action": "核对许可证原件并更正日期"})
    except ValueError:
        pass
    for account in profile.get("regulatory_accounts", []):
        if not account.get("required"):
            continue
        if account.get("registered") is False:
            findings.append({"level": "red", "kind": "account", "name": account["name"], "reason": "必需账号标记为未注册", "next_action": "核实适用性，完成注册或记录不适用依据"})
        elif account.get("registered") is None:
            findings.append({"level": "yellow", "kind": "account", "name": account["name"], "reason": "必需账号状态未确认", "next_action": "核实可登录状态并归档截图"})
    for task in task_doc.get("tasks", []):
        paths = task.get("evidence_files", [])
        missing = [path for path in paths if not is_inside_evidence(path, data_dir) or not (data_dir / path).is_file()]
        if task.get("status") == "completed" and paths and not missing:
            continue
        reason = "已标记完成，但证据文件缺失或路径无效" if task.get("status") == "completed" else "尚未完成基线证据核查"
        findings.append({"level": "yellow", "kind": "baseline", "name": task["title"], "reason": reason, "next_action": "核查现有记录；存在时归档证据，不存在时纳入整改计划"})
    return findings


def diagnose_baseline(data_dir: Path) -> dict[str, Any]:
    data_dir = initialize_data_dir(data_dir)
    profile = load_json(data_dir / "company_profile.json")
    task_doc = load_json(data_dir / "tasks.json")
    findings = diagnose_findings(profile, task_doc, data_dir)
    return {
        "enterprise": profile.get("enterprise_name"),
        "diagnosis_stage": profile.get("lifecycle", {}).get("stage"),
        "summary": {
            "red": sum(item["level"] == "red" for item in findings),
            "yellow": sum(item["level"] == "yellow" for item in findings),
        },
        "regulatory_content_status": task_doc.get("regulatory_content_status"),
        "findings": findings,
    }


def confirm_baseline(data_dir: Path, reviewer: object) -> dict[str, Any]:
    if not isinstance(reviewer, str) or not reviewer.strip():
        raise ComplianceError("validation_error", "reviewer must be a non-empty string", [{"path": "/reviewer", "message": "must be a non-empty string"}])
    data_dir = initialize_data_dir(data_dir)
    diagnosis = diagnose_baseline(data_dir)
    if diagnosis["summary"]["red"]:
        raise ComplianceError("baseline_blocked", "Baseline cannot be confirmed while red blockers remain.", diagnosis["findings"])
    profile_path = data_dir / "company_profile.json"
    profile = load_json(profile_path)
    profile["lifecycle"] = {
        "stage": "operational",
        "baseline_diagnosed_at": iso_now(),
        "baseline_reviewer": reviewer.strip(),
    }
    write_json(profile_path, profile)
    diagnosis["diagnosis_stage"] = "operational"
    diagnosis["reviewer"] = reviewer.strip()
    return diagnosis


def _task_alert(task: dict[str, Any], today: date, warning_days: int, data_dir: Path) -> tuple[str, str] | None:
    evidence_paths = task.get("evidence_files", [])
    missing = [path for path in evidence_paths if not is_inside_evidence(path, data_dir) or not (data_dir / path).is_file()]
    if task.get("status") == "completed":
        return ("yellow", "标记完成，但证据文件缺失或路径无效") if not evidence_paths or missing else None
    try:
        due = date.fromisoformat(task["next_due"])
    except (KeyError, TypeError, ValueError) as error:
        raise ComplianceError("invalid_task_state", f"Invalid due date for task {task.get('task_id')}.") from error
    if due < today:
        return "red", f"已逾期 {abs((due - today).days)} 天"
    if (due - today).days <= warning_days:
        return "yellow", f"{(due - today).days} 天内到期"
    return None


def run_check(data_dir: Path, warning_days: object = 30, red_only: object = False) -> dict[str, Any]:
    if type(warning_days) is not int or warning_days < 0:
        raise ComplianceError("validation_error", "warning_days must be a non-negative integer")
    if type(red_only) is not bool:
        raise ComplianceError("validation_error", "red_only must be a boolean")
    data_dir = initialize_data_dir(data_dir)
    profile = load_json(data_dir / "company_profile.json")
    if profile.get("lifecycle", {}).get("stage") != "operational":
        raise ComplianceError("baseline_required", "Complete onboarding and confirm the baseline before routine monitoring.")
    task_doc = load_json(data_dir / "tasks.json")
    today = date.today()
    alerts = []
    for task in task_doc.get("tasks", []):
        result = _task_alert(task, today, warning_days, data_dir)
        if not result:
            continue
        level, reason = result
        alerts.append(
            {
                "level": level,
                "kind": "task",
                "name": task["title"],
                "reason": reason,
                "due": task["next_due"],
                "regulatory_basis": task["regulatory_basis"],
                "source_ref": task["source_ref"],
                "source_status": task.get("source_status", task_doc.get("regulatory_content_status")),
                "evidence_files": task.get("evidence_files", []),
                "next_action": "补充证据并由质量负责人复核" if task.get("status") == "completed" else "完成任务、归档证据并由质量负责人复核",
            }
        )
    for account in profile.get("regulatory_accounts", []):
        if not account.get("required") or account.get("registered") is True:
            continue
        registered = account.get("registered")
        alerts.append(
            {
                "level": "red" if registered is False else "yellow",
                "kind": "account",
                "name": account["name"],
                "reason": "强制账号未注册" if registered is False else "强制账号状态未确认",
                "due": None,
                "regulatory_basis": "账号要求及适用性须以现行国家和属地监管要求复核。",
                "source_ref": "references/regulatory_map.md#国家局省级监管系统账号清单",
                "source_status": task_doc.get("regulatory_content_status"),
                "evidence_files": [],
                "next_action": "核实适用性、完成注册或状态确认，并归档登录/注册证据",
            }
        )
    alerts.sort(key=lambda item: (0 if item["level"] == "red" else 1, item["due"] or ""))
    if red_only:
        alerts = [item for item in alerts if item["level"] == "red"]
    return {
        "enterprise": profile.get("enterprise_name"),
        "checked_at": iso_now(),
        "summary": {
            "red": sum(item["level"] == "red" for item in alerts),
            "yellow": sum(item["level"] == "yellow" for item in alerts),
        },
        "regulatory_content_status": task_doc.get("regulatory_content_status"),
        "alerts": alerts,
    }


def record_evidence(data_dir: Path, task_id: object, evidence_path: object, complete: object = False) -> dict[str, Any]:
    if not isinstance(task_id, str) or not task_id.strip():
        raise ComplianceError("validation_error", "task_id must be a non-empty string")
    if not isinstance(evidence_path, str) or not evidence_path.strip():
        raise ComplianceError("validation_error", "evidence_path must be a non-empty string")
    if type(complete) is not bool:
        raise ComplianceError("validation_error", "complete must be a boolean")
    data_dir = initialize_data_dir(data_dir)
    if not is_inside_evidence(evidence_path, data_dir):
        raise ComplianceError("invalid_evidence_path", "Evidence path must be relative to the runtime data directory and inside evidence/.")
    if not (data_dir / evidence_path).is_file():
        raise ComplianceError("evidence_not_found", f"Evidence file does not exist: {evidence_path}")
    tasks_path = data_dir / "tasks.json"
    task_doc = load_json(tasks_path)
    task = next((item for item in task_doc.get("tasks", []) if item["task_id"] == task_id), None)
    if task is None:
        raise ComplianceError("task_not_found", f"Unknown task id: {task_id}")
    evidence_files = task.setdefault("evidence_files", [])
    if evidence_path not in evidence_files:
        evidence_files.append(evidence_path)
    if complete:
        task["status"] = "completed"
        task["last_completed"] = date.today().isoformat()
    task_doc["updated_at"] = iso_now()
    write_json(tasks_path, task_doc)
    return {"task": task}
