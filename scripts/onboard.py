#!/usr/bin/env python3
"""Interactively collect the enterprise profile through the core engine."""

from __future__ import annotations

import argparse
from pathlib import Path

from common import initialize_data_dir, load_json, parse_date, resolve_data_dir
from engine import ComplianceError, onboard


def prompt(label: str, current: str | None, required: bool = True) -> str:
    suffix = f" [{current}]" if current else ""
    while True:
        value = input(f"{label}{suffix}: ").strip() or (current or "")
        if value or not required:
            return value
        print("This field is required.")


def prompt_date(label: str, current: str | None) -> str:
    while True:
        value = prompt(label + " (YYYY-MM-DD)", current)
        try:
            parse_date(value, label)
            return value
        except ValueError as error:
            print(error)


def prompt_bool(label: str, current: bool) -> bool:
    default = "y" if current else "n"
    while True:
        value = input(f"{label} [y/n, default {default}]: ").strip().lower() or default
        if value in {"y", "yes", "是"}:
            return True
        if value in {"n", "no", "否"}:
            return False
        print("Enter y or n.")


def prompt_registration(label: str, current: bool | None) -> bool | None:
    default = {True: "registered", False: "unregistered", None: "unknown"}[current]
    while True:
        value = input(f"{label} [registered/unregistered/unknown, default {default}]: ").strip().lower() or default
        if value == "registered":
            return True
        if value == "unregistered":
            return False
        if value == "unknown":
            return None
        print("Enter registered, unregistered, or unknown.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="runtime data directory; defaults to QUALITY_COMPLIANCE_HOME or ~/.quality-compliance")
    parser.add_argument("--interactive", action="store_true", help="prompt for each onboarding field")
    parser.add_argument("--confirm-reset", action="store_true", help="replace existing enterprise task state after preserving required history")
    args = parser.parse_args()
    if not args.interactive:
        raise SystemExit("Use --interactive to collect the profile.")

    data_dir = initialize_data_dir(resolve_data_dir(args.data_dir))
    profile = load_json(data_dir / "company_profile.json")
    licence = profile.get("licence", {})
    responsible = profile.get("quality_responsible_person", {})
    conditions = profile.get("operating_conditions", {})
    print("Quality-compliance onboarding: Shanghai medical-device distributor")
    accounts = {}
    payload = {
        "enterprise_name": prompt("Enterprise name", profile.get("enterprise_name")),
        "licence": {
            "number": prompt("Medical-device licence number", licence.get("number")),
            "approval_date": prompt_date("Licence approval date", licence.get("approval_date")),
            "expiry_date": prompt_date("Licence expiry date", licence.get("expiry_date")),
        },
        "quality_responsible_person": {
            "name": prompt("Quality responsible person", responsible.get("name")),
            "contact": prompt("Quality responsible person contact", responsible.get("contact"), required=False),
        },
        "operating_conditions": {
            "cold_chain": prompt_bool("Does the enterprise operate cold-chain products?", bool(conditions.get("cold_chain"))),
            "third_party_logistics": prompt_bool("Does the enterprise use third-party logistics?", bool(conditions.get("third_party_logistics"))),
        },
        "regulatory_accounts": accounts,
        "confirm_reset": args.confirm_reset,
    }
    for account in profile.get("regulatory_accounts", []):
        accounts[account["id"]] = {
            "registered": prompt_registration(f"Account status: {account['name']}", account.get("registered")),
            "last_verified": account.get("last_verified"),
        }
    try:
        result = onboard(data_dir, payload)
    except ComplianceError as error:
        raise SystemExit(error.message) from error
    print(f"Profile saved and {result['tasks_generated']} tasks generated. Next: run diagnose.py.")
    print(f"Regulatory content status: {result.get('regulatory_content_status', 'unknown')}.")


if __name__ == "__main__":
    main()
