#!/usr/bin/env python3
"""Run routine monitoring through the core engine."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import resolve_data_dir
from engine import ComplianceError, run_check


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--red-only", action="store_true", help="show only red alerts")
    parser.add_argument("--json", action="store_true", help="write a machine-readable report")
    parser.add_argument("--warning-days", type=int, default=30)
    parser.add_argument("--data-dir", type=Path, help="runtime data directory; defaults to QUALITY_COMPLIANCE_HOME or ~/.quality-compliance")
    args = parser.parse_args()
    try:
        result = run_check(resolve_data_dir(args.data_dir), args.warning_days, args.red_only)
    except ComplianceError as error:
        raise SystemExit(error.message) from error
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    alerts = result["alerts"]
    print(f"监管内容状态：{result.get('regulatory_content_status', 'unknown')}")
    if not alerts:
        print("全部正常，无预警。")
        return
    print(f"质量合规巡检：{result.get('enterprise')}（{len(alerts)} 项预警）")
    for item in alerts:
        due = f"；到期日 {item['due']}" if item["due"] else ""
        evidence = "、".join(item["evidence_files"]) if item["evidence_files"] else "未登记"
        print(f"[{item['level'].upper()}] {item['name']}：{item['reason']}{due}")
        print(f"  法规依据：{item['regulatory_basis']}")
        print(f"  参考：{item['source_ref']}")
        print(f"  来源状态：{item.get('source_status', 'unknown')}")
        print(f"  证据：{evidence}")
        print(f"  下一步：{item['next_action']}")


if __name__ == "__main__":
    main()
