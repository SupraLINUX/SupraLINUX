#!/usr/bin/env python3
import json

def blocks(run_status, jobs):
    if run_status == "completed":
        return False
    if run_status == "queued":
        return True
    if not jobs:
        return True
    return any(job.get("status") != "completed" for job in jobs)

cases = [
    ("completed", [{"status": "completed", "conclusion": "success"}], False),
    ("queued", [], True),
    ("queued", [{"status": "queued", "conclusion": None}], True),
    ("in_progress", [], True),
    ("in_progress", [{"status": "in_progress", "conclusion": None}], True),
    ("in_progress", [{"status": "queued", "conclusion": None}], True),
    ("in_progress", [{"status": "completed", "conclusion": "skipped"}], False),
    ("in_progress", [
        {"status": "completed", "conclusion": "skipped"},
        {"status": "completed", "conclusion": "success"},
    ], False),
]

for status, jobs, expected in cases:
    actual = blocks(status, jobs)
    assert actual is expected, (status, jobs, expected, actual)

print("Authoritative stale-run blocking contract: PASS")
