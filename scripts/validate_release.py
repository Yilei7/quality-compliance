#!/usr/bin/env python3
"""Validate a quality-compliance release candidate without third-party packages."""

from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "scripts" / "core.py"
EXPECTED_DATA_FILES = {"company_profile.template.json", "task_templates.json"}
FORBIDDEN_NAMES = {"company_profile.json", "tasks.json", "evidence", "__pycache__", ".DS_Store"}
REQUIRED_TASK_FIELDS = {
    "id",
    "title",
    "module",
    "applies_to",
    "regulatory_basis",
    "source_ref",
    "schedule",
    "required_evidence",
}


class ValidationFailure(Exception):
    pass


def load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValidationFailure(f"{path.relative_to(ROOT)}: {error}") from error
    if not isinstance(value, dict):
        raise ValidationFailure(f"{path.relative_to(ROOT)} must contain a JSON object")
    return value


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationFailure(message)


def validate_manifest() -> None:
    manifest = load_json(ROOT / "manifest.json")
    package = manifest.get("package", {})
    compatibility = manifest.get("compatibility", {})
    data = manifest.get("data", {})
    scope = manifest.get("scope", {})
    regulatory = manifest.get("regulatory_content", {})
    distribution = manifest.get("distribution", {})
    require(manifest.get("manifest_version") == 1, "manifest_version must be 1")
    require(package.get("name") == "quality-compliance-core", "unexpected package name")
    require(bool(re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?", str(package.get("version", "")))), "package version is not SemVer-compatible")
    require(package.get("release_channel") == "controlled-pilot", "release channel must be controlled-pilot")
    require(package.get("public_release_ready") is False, "this candidate must not claim public release readiness")
    require(compatibility.get("api_version") == 1, "api_version must be 1")
    require(compatibility.get("profile_schema_version") == 2, "profile_schema_version must be 2")
    require(compatibility.get("task_state_schema_version") == 1, "task_state_schema_version must be 1")
    require(compatibility.get("python_requires") == ">=3.10", "python_requires must be >=3.10")
    require(compatibility.get("entrypoint") == "scripts/core.py", "entrypoint must be scripts/core.py")
    require(compatibility.get("runtime_dependencies") == [], "runtime dependencies must remain empty")
    require(data.get("runtime_location") == "external", "runtime data must remain outside the package")
    require(data.get("one_enterprise_per_runtime_directory") is True, "runtime data model must remain one enterprise per directory")
    require(scope.get("jurisdiction") == {"country": "CN", "province": "上海市"}, "unsupported jurisdiction in manifest")
    require(scope.get("entity_types") == ["device_distribution"], "unsupported entity type in manifest")
    require(regulatory.get("status") == "draft-requires-qualified-review", "regulatory status must disclose qualified-review requirement")
    require(regulatory.get("last_qualified_review_at") is None, "unreviewed candidate cannot claim a qualified review date")
    require(regulatory.get("official_source_register") == [], "unreviewed candidate cannot claim an official source register")
    require(distribution.get("license") is None, "license must remain unset until the owner makes a distribution decision")
    require(bool(distribution.get("public_release_blockers")), "public release blockers must be listed")


def parse_skill_frontmatter() -> dict[str, str]:
    content = (ROOT / "SKILL.md").read_text(encoding="utf-8")
    require(content.startswith("---\n"), "SKILL.md must begin with YAML frontmatter")
    try:
        raw, _body = content[4:].split("\n---\n", 1)
    except ValueError as error:
        raise ValidationFailure("SKILL.md frontmatter is not closed") from error
    values: dict[str, str] = {}
    for line in raw.splitlines():
        key, separator, value = line.partition(":")
        require(bool(separator) and bool(key.strip()) and bool(value.strip()), f"invalid SKILL.md frontmatter line: {line!r}")
        values[key.strip()] = value.strip()
    return values


def validate_skill_metadata() -> None:
    values = parse_skill_frontmatter()
    require(set(values) == {"name", "description"}, "SKILL.md frontmatter may contain only name and description")
    require(values["name"] == "quality-compliance", "SKILL.md name must be quality-compliance")
    require(bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", values["name"])), "SKILL.md name is invalid")
    require(len(values["name"]) <= 64, "SKILL.md name must not exceed 64 characters")
    require(1 <= len(values["description"]) <= 1024, "SKILL.md description must contain 1-1024 characters")
    require("<" not in values["description"] and ">" not in values["description"], "SKILL.md description must not contain angle brackets")
    require("references/product_scope.md" in (ROOT / "SKILL.md").read_text(encoding="utf-8"), "SKILL.md must route readers to the product boundary")


def validate_agent_metadata() -> None:
    lines = [line for line in (ROOT / "agents" / "openai.yaml").read_text(encoding="utf-8").splitlines() if line.strip()]
    require(lines and lines[0] == "interface:", "agents/openai.yaml must contain one interface mapping")
    values: dict[str, str] = {}
    for line in lines[1:]:
        require(line.startswith("  "), "interface fields must be indented by two spaces")
        key, separator, raw_value = line.strip().partition(":")
        require(bool(separator), f"invalid agents/openai.yaml line: {line!r}")
        try:
            value = json.loads(raw_value.strip())
        except json.JSONDecodeError as error:
            raise ValidationFailure(f"agents/openai.yaml values must be JSON-compatible quoted strings: {key}") from error
        require(isinstance(value, str) and bool(value), f"agents/openai.yaml field {key} must be a non-empty string")
        values[key] = value
    require(set(values) == {"display_name", "short_description", "default_prompt"}, "agents/openai.yaml has missing or unexpected interface fields")
    require("$quality-compliance" in values["default_prompt"], "default_prompt must reference $quality-compliance")


def validate_package_hygiene() -> None:
    data_files = {path.name for path in (ROOT / "data").iterdir() if path.is_file()}
    require(data_files == EXPECTED_DATA_FILES, f"data/ must contain only packaged templates, found {sorted(data_files)}")
    forbidden = []
    for path in ROOT.rglob("*"):
        if path.name in FORBIDDEN_NAMES or path.suffix == ".pyc":
            forbidden.append(str(path.relative_to(ROOT)))
    require(not forbidden, f"package contains runtime or generated data: {forbidden}")
    profile = load_json(ROOT / "data" / "company_profile.template.json")
    require(profile.get("enterprise_name") is None, "profile template must not contain an enterprise name")
    require(profile.get("schema_version") == 2, "profile template schema_version must be 2")


def validate_static_content() -> None:
    for path in ROOT.rglob("*.json"):
        load_json(path)
    for path in (ROOT / "scripts").glob("*.py"):
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except (OSError, SyntaxError) as error:
            raise ValidationFailure(f"invalid Python source {path.relative_to(ROOT)}: {error}") from error
    require((ROOT / "references" / "product_scope.md").is_file(), "product boundary reference is missing")


def validate_task_library() -> None:
    manifest = load_json(ROOT / "manifest.json")
    library = load_json(ROOT / "data" / "task_templates.json")
    regulatory = manifest["regulatory_content"]
    require(library.get("schema_version") == 1, "task library schema_version must be 1")
    require(library.get("library_version") == regulatory.get("library_version"), "task library and manifest versions differ")
    require(library.get("regulatory_content_status") == regulatory.get("status"), "task library and manifest regulatory status differ")
    require(library.get("last_qualified_review_at") == regulatory.get("last_qualified_review_at"), "task library and manifest review dates differ")
    require(library.get("official_source_register") == regulatory.get("official_source_register"), "task library and manifest source registers differ")
    require(library.get("jurisdiction") == manifest["scope"]["jurisdiction"], "task library and manifest jurisdictions differ")
    tasks = library.get("tasks")
    require(isinstance(tasks, list) and bool(tasks), "task library must contain tasks")
    task_ids = []
    for index, task in enumerate(tasks):
        require(isinstance(task, dict), f"task at index {index} must be an object")
        missing = REQUIRED_TASK_FIELDS - set(task)
        require(not missing, f"task {task.get('id', index)} is missing fields: {sorted(missing)}")
        require(bool(task["source_ref"]), f"task {task['id']} must have source_ref")
        task_ids.append(task["id"])
    require(len(task_ids) == len(set(task_ids)), "task IDs must be unique")


def run_core(data_dir: Path, request: dict[str, Any], expected_code: int = 0) -> dict[str, Any]:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(CORE), "--data-dir", str(data_dir)],
        input=json.dumps(request, ensure_ascii=False),
        text=True,
        capture_output=True,
        env=environment,
        timeout=15,
        check=False,
    )
    require(completed.returncode == expected_code, f"core exit code {completed.returncode}, expected {expected_code}; stderr={completed.stderr.strip()!r}")
    try:
        response = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ValidationFailure(f"core did not return JSON: {completed.stdout!r}") from error
    require(isinstance(response, dict), "core response must be an object")
    return response


def run_cli(script_name: str, data_dir: Path, *arguments: str) -> str:
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / script_name), "--data-dir", str(data_dir), *arguments],
        text=True,
        capture_output=True,
        env=environment,
        timeout=15,
        check=False,
    )
    require(completed.returncode == 0, f"{script_name} failed: {completed.stderr.strip()!r}")
    return completed.stdout


def validate_core_workflow() -> None:
    with tempfile.TemporaryDirectory(prefix="quality-compliance-release-") as raw_data_dir:
        data_dir = Path(raw_data_dir)
        onboard_request = {
            "version": 1,
            "operation": "onboard",
            "payload": {
                "enterprise_name": "发布校验虚拟企业",
                "licence": {"number": "VALIDATION-ONLY", "approval_date": "2026-01-01", "expiry_date": "2099-12-31"},
                "quality_responsible_person": {"name": "发布校验人员", "contact": None},
                "operating_conditions": {"cold_chain": False, "third_party_logistics": False},
                "regulatory_accounts": {
                    "shanghai_traceability_reporting": {"registered": True, "last_verified": "2026-08-09"},
                    "national_device_adverse_event": {"registered": None, "last_verified": None},
                },
            },
        }
        onboard_response = run_core(data_dir, onboard_request)
        require(onboard_response.get("ok") is True, "onboard smoke test failed")
        require(onboard_response["result"].get("regulatory_content_status") == "draft-requires-qualified-review", "onboard omitted regulatory status")
        task_state = load_json(data_dir / "tasks.json")
        require(all(task.get("source_status") == "draft-requires-qualified-review" for task in task_state["tasks"]), "generated task state omitted source_status")

        diagnosis = run_core(data_dir, {"version": 1, "operation": "diagnose", "payload": {}})
        require(diagnosis.get("ok") is True and diagnosis["result"]["summary"]["red"] == 0, "diagnose smoke test failed")
        confirmation = run_core(data_dir, {"version": 1, "operation": "confirm-baseline", "payload": {"reviewer": "发布校验人员"}})
        require(confirmation.get("ok") is True and confirmation["result"]["diagnosis_stage"] == "operational", "baseline confirmation smoke test failed")
        check = run_core(data_dir, {"version": 1, "operation": "check", "payload": {"warning_days": 30, "red_only": False}})
        require(check.get("ok") is True and bool(check["result"]["alerts"]), "routine check smoke test failed")
        require(check["result"].get("regulatory_content_status") == "draft-requires-qualified-review", "check omitted regulatory status")
        require(all(item.get("source_status") == "draft-requires-qualified-review" for item in check["result"]["alerts"]), "an alert omitted source_status")

        diagnosis_cli = json.loads(run_cli("diagnose.py", data_dir, "--json"))
        require(diagnosis_cli.get("regulatory_content_status") == "draft-requires-qualified-review", "diagnose CLI omitted regulatory status")
        check_cli = json.loads(run_cli("check.py", data_dir, "--json"))
        require(check_cli.get("regulatory_content_status") == "draft-requires-qualified-review", "check CLI JSON omitted regulatory status")
        check_text = run_cli("check.py", data_dir)
        require("监管内容状态：draft-requires-qualified-review" in check_text, "check CLI text omitted regulatory status")
        require("来源状态：draft-requires-qualified-review" in check_text, "check CLI text omitted alert source status")

        evidence_path = data_dir / "evidence" / "release-validation.txt"
        evidence_path.write_text("Synthetic release-validation evidence.\n", encoding="utf-8")
        evidence = run_core(
            data_dir,
            {
                "version": 1,
                "operation": "record-evidence",
                "payload": {"task_id": "annual-training", "evidence_path": "evidence/release-validation.txt", "complete": True},
            },
        )
        require(evidence.get("ok") is True and evidence["result"]["task"]["status"] == "completed", "record-evidence smoke test failed")

        unknown = run_core(data_dir, {"version": 1, "operation": "not-an-operation", "payload": {}}, expected_code=2)
        require(unknown.get("ok") is False and unknown.get("error", {}).get("code") == "unknown_operation", "unknown-operation boundary failed")
        unsupported = run_core(data_dir, {"version": 999, "operation": "diagnose", "payload": {}}, expected_code=2)
        require(unsupported.get("ok") is False and unsupported.get("error", {}).get("code") == "unsupported_version", "version boundary failed")

    forbidden_runtime = ROOT / ".release-validation-runtime"
    require(not forbidden_runtime.exists(), "reserved release-validation path already exists inside package")
    boundary = run_core(forbidden_runtime, {"version": 1, "operation": "diagnose", "payload": {}}, expected_code=3)
    require(boundary.get("ok") is False and boundary.get("error", {}).get("code") == "data_error", "package/runtime isolation boundary failed")
    require(not forbidden_runtime.exists(), "core created runtime data inside the package")


def main() -> None:
    checks: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    validators: list[tuple[str, Callable[[], None]]] = [
        ("manifest", validate_manifest),
        ("skill-metadata", validate_skill_metadata),
        ("agent-metadata", validate_agent_metadata),
        ("package-hygiene", validate_package_hygiene),
        ("static-content", validate_static_content),
        ("task-library", validate_task_library),
        ("core-workflow", validate_core_workflow),
    ]
    for name, validator in validators:
        try:
            validator()
        except Exception as error:
            checks.append({"name": name, "ok": False})
            errors.append({"check": name, "message": str(error)})
        else:
            checks.append({"name": name, "ok": True})

    version = None
    try:
        version = load_json(ROOT / "manifest.json").get("package", {}).get("version")
    except Exception:
        pass
    result = {"ok": not errors, "release": version, "checks": checks, "errors": errors}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if not errors else 1)


if __name__ == "__main__":
    main()
