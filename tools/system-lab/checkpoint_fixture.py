#!/usr/bin/env python3
"""Synthetic cache fixture: no operating system, package, secret or external data."""
import argparse
import hashlib
from pathlib import Path

SIZE = 8 * 1024 * 1024
BLOCK = b"\x5a" * (1024 * 1024)


def verify(path):
    expected = hashlib.sha256()
    actual = hashlib.sha256()
    if path.is_symlink() or not path.is_file() or path.stat().st_size != SIZE:
        raise ValueError("Unexpected fixture type or size")
    with path.open("rb") as stream:
        for _ in range(SIZE // len(BLOCK)):
            expected.update(BLOCK)
            actual.update(stream.read(len(BLOCK)))
    if actual.digest() != expected.digest():
        raise ValueError("Checkpoint fixture mismatch")
    print(actual.hexdigest())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("create", "verify"))
    parser.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.mode == "create":
        args.path.parent.mkdir(parents=True, exist_ok=True)
        with args.path.open("xb") as stream:
            for _ in range(SIZE // len(BLOCK)):
                stream.write(BLOCK)
    verify(args.path)


if __name__ == "__main__":
    main()
