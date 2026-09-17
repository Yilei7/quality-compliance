# Public release checklist

## Scope and content

- [ ] README states the supported scope and unsupported use cases.
- [ ] All runtime/customer data is excluded from the repository.
- [ ] No secrets, credentials, screenshots, or proprietary standards text remain.
- [ ] Every task has a stable `source_ref` and a visible `source_status`.
- [ ] The official source register is complete for the claims being published.
- [ ] A qualified reviewer has recorded review dates and unresolved interpretations.

## Legal and operational readiness

- [ ] Code, documentation, and third-party content licences are decided.
- [ ] `LICENSE`, `NOTICE`, and attribution files are present.
- [ ] Privacy, security, backup, access-control, and incident-response expectations are documented.
- [ ] Support scope, compatibility policy, and regulatory-content update process are documented.
- [ ] The disclaimer is visible in README and release notes.

## Technical validation

- [ ] Remove `.DS_Store`, `__pycache__`, `.pyc`, runtime JSON, and `evidence/` before packaging.
- [ ] `python3 scripts/validate_release.py` passes.
- [ ] `python3 scripts/build_release.py --output-dir dist` passes.
- [ ] The generated archive contains only the intended package files.
- [ ] A clean Python 3.10+ environment can run the onboarding, diagnosis, confirmation, check, and evidence smoke path.
- [ ] GitHub Actions runs release validation on every pull request.

## Publication

- [ ] Repository name and description are clear about the Shanghai distribution scope.
- [ ] Default branch protection and pull-request review are enabled.
- [ ] First tag is a pre-release such as `v0.1.0-alpha.1`.
- [ ] Release notes list known limitations and the regulatory content status.
- [ ] ZIP and SHA-256 checksum are attached to the GitHub release.

