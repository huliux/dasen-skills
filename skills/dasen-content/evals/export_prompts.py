#!/usr/bin/env python3
"""Export blind-eval inputs without expected outputs or assertions."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

EVALS = Path(__file__).with_name("evals.json")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--id", action="append", dest="ids", help="Export only this case ID; repeatable")
    args = parser.parse_args()

    data = json.loads(EVALS.read_text(encoding="utf-8"))
    cases = data.get("evals")
    if not isinstance(cases, list):
        parser.error("evals.json must contain an evals array")

    required = {"id", "category", "prompt", "expected_output", "assertions"}
    allowed_categories = {"should-trigger", "should-not-trigger", "output-contract"}
    ids = [case.get("id") for case in cases if isinstance(case, dict)]
    if len(ids) != len(cases) or any(not isinstance(case_id, str) or not case_id for case_id in ids):
        parser.error("every eval must be an object with a non-empty string id")
    if len(ids) != len(set(ids)):
        parser.error("eval IDs must be unique")
    for case in cases:
        missing_fields = required - set(case)
        if missing_fields:
            parser.error(f"{case['id']}: missing field(s): {', '.join(sorted(missing_fields))}")
        if case["category"] not in allowed_categories:
            parser.error(f"{case['id']}: unknown category {case['category']!r}")
        if not isinstance(case["prompt"], str) or not case["prompt"].strip():
            parser.error(f"{case['id']}: prompt must be a non-empty string")
        if not isinstance(case["assertions"], list) or not case["assertions"]:
            parser.error(f"{case['id']}: assertions must be a non-empty array")

    selected = set(args.ids or [])
    seen: set[str] = set()
    for case in cases:
        case_id = case["id"]
        if selected and case_id not in selected:
            continue
        print(json.dumps({"id": case_id, "prompt": case["prompt"]}, ensure_ascii=False))
        seen.add(case_id)

    missing = selected - seen
    if missing:
        parser.error("unknown case ID(s): " + ", ".join(sorted(missing)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
