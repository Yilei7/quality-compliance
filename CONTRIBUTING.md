# Contributing

Thank you for helping improve this project.

## Code and workflow changes

1. Open an issue describing the problem and the intended behavior.
2. Keep changes within the documented scope unless the issue explicitly expands it.
3. Add or update deterministic tests and run `python3 scripts/validate_release.py`.
4. Do not write runtime data into the package directory.
5. Do not add credentials, customer records, personal information, screenshots, or copied proprietary standards text.

## Regulatory content changes

Every regulatory correction or new task should include:

- the official source URL;
- document number or title;
- publication/effective date when available;
- jurisdiction and applicable entity type;
- the exact task or statement being changed;
- reviewer name/role and review date;
- a note explaining any unresolved interpretation.

Until qualified review is complete, keep `source_status` as `draft-requires-qualified-review`.

## Pull requests

Use a small, focused pull request. Explain user impact, scope, validation performed, and any regulatory or licensing implications. Maintainers may request review from a qualified quality or regulatory professional before merging content changes.

