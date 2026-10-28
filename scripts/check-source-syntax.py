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
    extensionless_python = []
    package_shells = set(root.glob("packages/**/*.sh"))
    for path in root.glob("packages/**/*"):
        if not path.is_file() or path.suffix or "__pycache__" in path.parts:
            continue
        with path.open("rb") as source:
            header = source.readline(256)
        if header.startswith(b"#!") and b"python" in header:
            extensionless_python.append(path)
        elif header.startswith(b"#!"):
            interpreters = [part.rsplit(b"/", 1)[-1] for part in header[2:].split()]
            if b"bash" in interpreters or b"sh" in interpreters:
                package_shells.add(path)
    paths = sorted(set(paths) | set(extensionless_python))
    for path in paths:
        try:
            ast.parse(path.read_bytes(), filename=str(path.relative_to(root)))
        except (SyntaxError, UnicodeError, ValueError) as exc:
            errors.append(str(exc))
    shells = sorted(set(root.glob("scripts/**/*.sh")) | package_shells)
    for path in shells:
        with path.open("rb") as source:
            header = source.readline(256)
        interpreters = [part.rsplit(b"/", 1)[-1] for part in header[2:].split()]
        interpreter = "sh" if b"sh" in interpreters and b"bash" not in interpreters else "bash"
        result = subprocess.run([interpreter, "-n", str(path)], capture_output=True, text=True)
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
