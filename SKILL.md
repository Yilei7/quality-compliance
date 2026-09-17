---
name: quality-compliance
description: Establish and manage recurring quality-compliance work for a Shanghai medical-device distribution enterprise. Use when collecting initial enterprise information, running a baseline readiness diagnosis, maintaining GSP-related task and evidence records, preparing an inspection self-check, creating a CAPA draft, or running a routine compliance check. Do not use to give a final legal opinion, replace a quality responsible person, or submit reports to regulators.
---

# Quality Compliance

Use this skill as an evidence-first operating workflow. Treat every regulatory assertion as a draft until a qualified reviewer verifies the current official source and local implementation requirement.

## Product Boundary

Treat this version as a technical release candidate for controlled pilots. It supports one Shanghai medical-device distribution enterprise per runtime data directory. Read `references/product_scope.md` before deployment or customer-facing claims. Preserve `source_status` in task and alert outputs so draft regulatory content cannot be presented as verified.

## Workflow

Follow the stages in order. This MVP supports only `device_distribution` in Shanghai.

1. **Build the profile.** If `lifecycle.stage` is `onboarding`, collect enterprise name, licence number, licence approval and expiry dates, quality responsible person, cold-chain and third-party logistics conditions, and the status of each listed regulatory account. Ask for missing facts before discussing routine alerts. Use `python3 scripts/onboard.py --interactive` to persist them and generate applicable tasks.
2. **Diagnose the baseline.** Run `python3 scripts/diagnose.py`. Present blockers, verification gaps, and required evidence separately. Do not call an open task a regulatory breach merely because the baseline has not yet been verified.
3. **Confirm operational monitoring.** After a quality responsible person reviews the diagnostic result and there are no red blockers, run `python3 scripts/diagnose.py --confirm --reviewer <name>`. This records the baseline review and enables routine checks.
4. **Run routine checks.** Run `python3 scripts/check.py --red-only` for concise alerts, or omit the flag for a complete report. Use `--json` when another tool must consume the result.
5. **Close work with evidence.** Put evidence in the runtime `evidence/` directory, then run `python3 scripts/record_evidence.py <task-id> evidence/<file> --complete`.

For inspection preparation, read `references/inspection_checklist.md`. For a deficiency response, read `references/deficiency_response.md`. For a regulatory-context question, read `references/regulatory_map.md` and verify any time-sensitive or local rule against an official source.

## Response Rules

- Present conclusions as: regulatory basis, task state, evidence state, then required next action.
- Mark absent evidence as a gap even when a task is marked complete.
- Do not invent completed training, reports, registrations, inspections, or evidence files.
- Do not claim that a result guarantees regulatory compliance or inspection acceptance.
- Keep customer evidence local unless the user explicitly asks to share it.

## Data Contract

- Keep `data/company_profile.template.json` and `data/task_templates.json` as read-only packaged resources.
- Store runtime data outside the Skill package. Default to `~/.quality-compliance/`; override with `QUALITY_COMPLIANCE_HOME` or `--data-dir <path>`.
- Let the scripts initialize `company_profile.json`, `tasks.json`, and `evidence/` in the runtime directory. Do not create customer state under the Skill directory.
- Move `company_profile.json.lifecycle.stage` from `onboarding` to `operational` only after a baseline diagnostic is confirmed.
- Keep evidence paths relative to the runtime data directory and inside its `evidence/` subdirectory.

## Core JSON Interface

Use `python3 scripts/core.py --data-dir <path>` when an application or another Agent needs structured integration. Send one JSON request on standard input with `version`, `operation`, and `payload`. Supported operations are `onboard`, `diagnose`, `confirm-baseline`, `check`, and `record-evidence`. Parse only the JSON response from standard output; treat a nonzero exit code or `ok: false` as failure. Read `references/core_api.md` before building an adapter.

## Release Validation

Run `python3 scripts/validate_release.py` before packaging. Build a validated archive with `python3 scripts/build_release.py`; it writes the archive and SHA-256 checksum outside the Skill directory by default. Do not distribute a package when validation fails.
