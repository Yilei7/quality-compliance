#!/usr/bin/env python3
"""Build a deterministic, validated quality-compliance release archive."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INCLUDED_FILES = (ROOT / "SKILL.md", ROOT / "manifest.json")
INCLUDED_DIRECTORIES = (ROOT / "agents", ROOT / "data", ROOT / "references", ROOT / "scripts")
EXCLUDED_NAMES = {"__pycache__", ".DS_Store"}
ZIP_TIMESTAMP = (2020, 1, 1, 0, 0, 0)


def release_files() -> list[Path]:
    files = list(INCLUDED_FILES)
    for directory in INCLUDED_DIRECTORIES:
        files.extend(path for path in directory.rglob("*") if path.is_file())
    return sorted(
        (path for path in files if not any(part in EXCLUDED_NAMES for part in path.parts) and path.suffix != ".pyc"),
        key=lambda path: path.relative_to(ROOT).as_posix(),
    )


def validate() -> None:
    completed = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "validate_release.py")],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        sys.stderr.write(completed.stdout)
        sys.stderr.write(completed.stderr)
        raise SystemExit(completed.returncode)


def write_archive(archive_path: Path, files: list[Path]) -> None:
    archive_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(ROOT).as_posix()
            info = zipfile.ZipInfo(f"quality-compliance/{relative}", date_time=ZIP_TIMESTAMP)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.create_system = 3
            mode = 0o755 if path.suffix == ".py" and path.read_bytes().startswith(b"#!") else 0o644
            info.external_attr = mode << 16
            archive.writestr(info, path.read_bytes(), compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def verify_archive(archive_path: Path, files: list[Path]) -> None:
    expected = {f"quality-compliance/{path.relative_to(ROOT).as_posix()}" for path in files}
    with zipfile.ZipFile(archive_path) as archive:
        actual = set(archive.namelist())
        if actual != expected:
            raise SystemExit("Archive content differs from the validated release file set.")
        bad = [name for name in actual if Path(name).name in {"company_profile.json", "tasks.json", ".DS_Store"} or "evidence/" in name or "__pycache__/" in name]
        if bad:
            raise SystemExit(f"Archive contains forbidden runtime or generated files: {bad}")
        corrupt_member = archive.testzip()
        if corrupt_member is not None:
            raise SystemExit(f"Archive member failed CRC validation: {corrupt_member}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT.parent / "dist", help="archive output directory")
    args = parser.parse_args()
    validate()
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["package"]["version"]
    output_dir = args.output_dir.expanduser().resolve()
    archive_path = output_dir / f"quality-compliance-core-{version}.zip"
    files = release_files()
    write_archive(archive_path, files)
    verify_archive(archive_path, files)
    digest = hashlib.sha256(archive_path.read_bytes()).hexdigest()
    checksum_path = archive_path.with_suffix(".zip.sha256")
    checksum_path.write_text(f"{digest}  {archive_path.name}\n", encoding="ascii")
    print(
        json.dumps(
            {
                "ok": True,
                "release": version,
                "archive": str(archive_path),
                "checksum_file": str(checksum_path),
                "sha256": digest,
                "files": len(files),
                "bytes": archive_path.stat().st_size,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
