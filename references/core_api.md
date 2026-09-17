# Core JSON API

Run `python3 scripts/core.py --data-dir <path>`. Send exactly one JSON object on standard input and parse exactly one JSON object from standard output. Keep the data directory in trusted process configuration; never accept it directly from an untrusted web request.

## Envelope

Request:

```json
{"version": 1, "operation": "diagnose", "payload": {}}
```

Success:

```json
{"ok": true, "version": 1, "operation": "diagnose", "result": {}}
```

Failure exits nonzero and returns:

```json
{"ok": false, "version": 1, "operation": "diagnose", "error": {"code": "validation_error", "message": "...", "details": []}}
```

## Regulatory content provenance

Generated task state and routine alerts include `source_status`. This release uses `draft-requires-qualified-review`; adapters must keep that value visible and must not translate it into a verified or official status. Diagnostic and check results also expose `regulatory_content_status` at result level.

## Operations

### onboard

Creates the profile and applicable task state. `regulatory_accounts` is keyed by the stable account IDs in `company_profile.template.json`. Set `confirm_reset` only when replacing existing state after preserving required history.

```json
{
  "version": 1,
  "operation": "onboard",
  "payload": {
    "enterprise_name": "上海某医疗器械有限公司",
    "licence": {
      "number": "许可证编号",
      "approval_date": "2026-01-01",
      "expiry_date": "2031-12-31"
    },
    "quality_responsible_person": {"name": "质量负责人", "contact": null},
    "operating_conditions": {"cold_chain": false, "third_party_logistics": false},
    "regulatory_accounts": {
      "shanghai_traceability_reporting": {"registered": true, "last_verified": "2026-08-08"},
      "national_device_adverse_event": {"registered": null, "last_verified": null}
    }
  }
}
```

### diagnose

Returns red blockers, yellow verification gaps, and summary counts.

```json
{"version": 1, "operation": "diagnose", "payload": {}}
```

### confirm-baseline

Requires no red blockers. Yellow gaps remain visible and may enter the remediation plan.

```json
{"version": 1, "operation": "confirm-baseline", "payload": {"reviewer": "质量负责人"}}
```

### check

Requires an operational baseline. `warning_days` must be a non-negative integer.

```json
{"version": 1, "operation": "check", "payload": {"warning_days": 30, "red_only": false}}
```

### record-evidence

The file must already exist below the runtime `evidence/` directory.

```json
{"version": 1, "operation": "record-evidence", "payload": {"task_id": "annual-training", "evidence_path": "evidence/training.pdf", "complete": true}}
```
