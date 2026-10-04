#!/usr/bin/env python3
"""Check every script before validators or package execution can start."""
import argparse
import ast
import json
import subprocess
from pathlib import Path


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def check(root):
    errors = []
    paths = sorted(set(root.glob("scripts/**/*.py")) | set(root.glob("packages/**/*.py")))
    for path in paths:
        try:
            ast.parse(path.read_bytes(), filename=str(path.relative_to(root)))
        except (SyntaxError, UnicodeError, ValueError) as exc:
            errors.append(str(exc))
    shells = sorted(root.glob("scripts/**/*.sh"))
    for path in shells:
        result = subprocess.run(["bash", "-n", str(path)], capture_output=True, text=True)
        if result.returncode:
            errors.append(result.stderr.strip())
    manifests = sorted(root.glob("manifests/**/*.json"))
    for path in manifests:
        try:
            json.loads(path.read_text(), object_pairs_hook=unique_object)
        except (ValueError, UnicodeError) as exc:
            errors.append(f"{path.relative_to(root)}: {exc}")
    return errors, (len(paths), len(shells), len(manifests))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    errors, counts = check(args.root)
    for error in errors:
        print(f"ERROR: {error}")
    if errors:
        raise SystemExit(1)
    print(f"Source syntax: PASS; Python={counts[0]} Bash={counts[1]} JSON={counts[2]}")


if __name__ == "__main__":
    main()
