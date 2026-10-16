#!/usr/bin/env python3
"""Route current work without reopening closed package campaigns."""
import argparse
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def plan(paths, planning, qt_changed=False):
    plasma_changed = any(
        path.startswith(("manifests/kde-plasma", "scripts/run-kde-plasma",
                         "scripts/validate_kde_plasma"))
        or path in {".github/workflows/kde-plasma-lane.yml", "scripts/plan-pr-ci.py"}
        for path in paths
    )
    qt_changed = qt_changed or any(path in {
        ".github/workflows/qt-provider-preflight.yml", "scripts/run-qt-provider-preflight.sh",
        "scripts/qt-provider-preflight-needed.sh",
    } for path in paths)
    return {
        "run_plasma_lane": plasma_changed and planning.get("execution_authorized") is True,
        "run_qt_provider": qt_changed,
        "phase": planning.get("status"),
        "changed_path_count": len(paths),
        "historical_package_lanes": "manual-or-reusable-only",
    }


def git(*args):
    return subprocess.check_output(["git", "-C", str(ROOT), *args])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("before")
    parser.add_argument("after")
    parser.add_argument("--github-output", type=Path)
    args = parser.parse_args()
    for ref in (args.before, args.after):
        if not re.fullmatch(r"[0-9a-fA-F]{40}", ref):
            parser.error("comparison refs must be complete commit SHAs")
        git("cat-file", "-e", f"{ref}^{{commit}}")
    paths = git("diff", "--name-only", "-z", args.before, args.after, "--").decode().split("\0")
    paths = [path for path in paths if path]
    qt_changed = False
    if "manifests/desktop-stack.json" in paths:
        def profile(ref):
            data = json.loads(git("show", f"{ref}:manifests/desktop-stack.json"))
            return {key: data.get(key) for key in ("platform", "desktop", "qt")}
        qt_changed = profile(args.before) != profile(args.after)
    planning = json.loads((ROOT / "manifests/kde-plasma.json").read_text())["planning"]
    result = plan(paths, planning, qt_changed)
    if args.github_output:
        with args.github_output.open("a") as output:
            for key in ("run_plasma_lane", "run_qt_provider"):
                output.write(f"{key}={str(result[key]).lower()}\n")
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
