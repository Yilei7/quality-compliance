# quality-compliance

面向中国上海市医疗器械经营企业的质量检视工作流与参考实现。

This project is a local-first, evidence-oriented workflow for one Shanghai medical-device distribution enterprise per runtime data directory. It supports:

- enterprise onboarding and licence/profile capture;
- baseline readiness diagnosis;
- qualified-review confirmation before routine monitoring;
- recurring checks and deadline alerts;
- evidence association and task closure;
- a small JSON stdin/stdout API for adapters and agents.

## Scope

Current support is deliberately narrow: `CN / 上海市 / device_distribution`.

This repository is a technical reference implementation. It does not provide legal advice, certify compliance, guarantee inspection acceptance, submit regulatory reports, or replace the named quality responsible person.

Regulatory content is released as `draft-requires-qualified-review` until each item has an official source, effective-date check, qualified reviewer, and review date.

## Quick start

Requirements: Python 3.10 or newer; no third-party Python dependencies.

```bash
python3 scripts/onboard.py --interactive --data-dir ~/.quality-compliance
python3 scripts/diagnose.py --data-dir ~/.quality-compliance
python3 scripts/diagnose.py --confirm --reviewer "质量负责人" --data-dir ~/.quality-compliance
python3 scripts/check.py --red-only --data-dir ~/.quality-compliance
```

For machine integration, read [`references/core_api.md`](references/core_api.md) and send one JSON request to:

```bash
python3 scripts/core.py --data-dir ~/.quality-compliance
```

Runtime data belongs outside this repository. Do not commit `company_profile.json`, `tasks.json`, or the `evidence/` directory.

## Release status

The first public release should remain an alpha/controlled-pilot release. Before changing that status, complete the regulatory source review, privacy/security review, licence decision, and support/incident process described in [`RELEASE_CHECKLIST.md`](RELEASE_CHECKLIST.md).

## Related projects

This project complements general ISO 13485 templates, global regulatory knowledge bases, and full eQMS platforms. It is intentionally focused on the operational inspection workflow for Shanghai medical-device distributors.

## Contributing

See [`CONTRIBUTING.md`](CONTRIBUTING.md). Regulatory corrections must include an official source and review context; do not submit customer records or proprietary standards text.

