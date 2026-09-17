#!/usr/bin/env python3
"""Diagnose and confirm the enterprise baseline through the core engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import resolve_data_dir
from engine import ComplianceError, confirm_baseline, diagnose_baseline


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--confirm", action="store_true", help="mark the reviewed baseline operational")
    parser.add_argument("--reviewer", help="quality reviewer confirming the diagnostic result")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--data-dir", type=Path, help="runtime data directory; defaults to QUALITY_COMPLIANCE_HOME or ~/.quality-compliance")
    args = parser.parse_args()
    data_dir = resolve_data_dir(args.data_dir)
    try:
        result = confirm_baseline(data_dir, args.reviewer) if args.confirm else diagnose_baseline(data_dir)
    except ComplianceError as error:
        raise SystemExit(error.message) from error
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    summary = result["summary"]
    print(f"基线诊断：{result.get('enterprise')}（{summary['red']} 项阻断项，{summary['yellow']} 项待核查项）")
    print(f"监管内容状态：{result.get('regulatory_content_status', 'unknown')}")
    for item in result["findings"]:
        print(f"[{item['level'].upper()}] {item['name']}：{item['reason']}")
        print(f"  下一步：{item['next_action']}")
    if args.confirm:
        print(f"Baseline confirmed by {result['reviewer']}; routine monitoring is enabled.")
    elif summary["red"]:
        print("先处理红色阻断项；处理后重新运行诊断。")
    else:
        print("质量负责人复核后，运行 diagnose.py --confirm --reviewer <name> 启用常规巡检。")


if __name__ == "__main__":
    main()
