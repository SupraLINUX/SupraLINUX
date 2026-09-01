#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NoReturn


def fail(message: str) -> NoReturn:
    print(f"AURORA_KSQ_1_CHECKPOINT_FAILURE: {message}", file=sys.stderr)
    raise SystemExit(1)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_env(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            fail(f"malformed env line in {path}: {line!r}")
        key, value = line.split("=", 1)
        out[key] = value
    return out


def package_field(deb: Path, field: str) -> str:
    try:
        return subprocess.run(
            ["dpkg-deb", "-f", str(deb), field],
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        fail(f"cannot read {field} from {deb}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", type=Path, required=True)
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.spec.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not data:
        fail("checkpoint spec must be a non-empty JSON array")

    target = args.target.resolve()
    evidence_out = args.evidence.resolve()
    shutil.rmtree(target, ignore_errors=True)
    target.mkdir(parents=True, exist_ok=True)
    evidence_out.mkdir(parents=True, exist_ok=True)

    expected_first = 1
    cumulative = 0
    filenames: set[str] = set()
    packages: dict[str, str] = {}
    chain_rows: list[str] = [
        "first_order\tlast_order\trun_id\tartifact_id\tartifact_digest\tnew_debs\taccumulated_debs\tnew_debs_manifest_sha256\tbuild_manifest_sha256"
    ]

    for index, item in enumerate(data, 1):
        if not isinstance(item, dict):
            fail(f"checkpoint {index} is not an object")
        required = {
            "root",
            "first_order",
            "last_order",
            "run_id",
            "artifact_id",
            "artifact_digest",
            "new_debs",
            "accumulated_debs",
            "new_debs_manifest_sha256",
            "build_manifest_sha256",
        }
        missing = sorted(required - item.keys())
        if missing:
            fail(f"checkpoint {index} missing fields: {missing}")

        first = int(item["first_order"])
        last = int(item["last_order"])
        new_count = int(item["new_debs"])
        accumulated = int(item["accumulated_debs"])
        if first != expected_first or last < first:
            fail(f"checkpoint chain is not contiguous at {first}-{last}; expected first {expected_first}")

        root = Path(item["root"]).resolve()
        chunk = f"chunk-{first:03d}-{last:03d}"
        evidence = root / "ksq-1/full" / chunk / "evidence"
        debs = root / "ksq-1/full" / chunk / "new-debs"
        status_path = evidence / "range-status.env"
        hash_path = evidence / "new-debs.sha256"
        manifest_path = evidence / "build-manifest.tsv"
        for path in (status_path, hash_path, manifest_path):
            if not path.is_file():
                fail(f"checkpoint {first}-{last} missing {path.relative_to(root)}")
        if not debs.is_dir():
            fail(f"checkpoint {first}-{last} new-debs directory missing")

        status = read_env(status_path)
        expected_status = {
            "AURORA_KSQ_1_RANGE_STATUS": "PASS",
            "AURORA_KSQ_1_RANGE_FIRST_ORDER": str(first),
            "AURORA_KSQ_1_RANGE_LAST_ORDER": str(last),
            "AURORA_KSQ_1_RANGE_NEW_DEBS": str(new_count),
            "AURORA_KSQ_1_RANGE_ACCUMULATED_DEBS": str(accumulated),
        }
        for key, value in expected_status.items():
            if status.get(key) != value:
                fail(f"checkpoint {first}-{last} {key}: expected {value}, got {status.get(key)!r}")

        if sha256(hash_path) != item["new_debs_manifest_sha256"]:
            fail(f"checkpoint {first}-{last} new-debs.sha256 identity mismatch")
        if sha256(manifest_path) != item["build_manifest_sha256"]:
            fail(f"checkpoint {first}-{last} build-manifest.tsv identity mismatch")

        actual_debs = sorted(debs.glob("*.deb"))
        if len(actual_debs) != new_count:
            fail(f"checkpoint {first}-{last} has {len(actual_debs)} DEBs, expected {new_count}")

        manifest_hashes: dict[str, str] = {}
        for line in hash_path.read_text(encoding="utf-8").splitlines():
            parts = line.split(None, 1)
            if len(parts) != 2:
                fail(f"checkpoint {first}-{last} malformed checksum line: {line!r}")
            digest, filename = parts
            filename = filename.lstrip("*")
            if "/" in filename or filename in manifest_hashes:
                fail(f"checkpoint {first}-{last} invalid/duplicate checksum target: {filename}")
            manifest_hashes[filename] = digest

        actual_names = {path.name for path in actual_debs}
        if set(manifest_hashes) != actual_names:
            fail(f"checkpoint {first}-{last} checksum manifest does not exactly cover new DEBs")

        for deb in actual_debs:
            expected_digest = manifest_hashes[deb.name]
            actual_digest = sha256(deb)
            if actual_digest != expected_digest:
                fail(f"checkpoint {first}-{last} SHA-256 mismatch: {deb.name}")
            if deb.name in filenames:
                fail(f"checkpoint filename overlap: {deb.name}")
            package = package_field(deb, "Package")
            if package in packages:
                fail(
                    f"binary package produced by multiple checkpoints: {package}: "
                    f"{packages[package]} and {deb.name}"
                )
            filenames.add(deb.name)
            packages[package] = deb.name
            shutil.copy2(deb, target / deb.name)

        cumulative += new_count
        if cumulative != accumulated:
            fail(f"checkpoint {first}-{last} accumulated count {accumulated} != chain total {cumulative}")
        expected_first = last + 1

        chain_rows.append(
            f"{first}\t{last}\t{item['run_id']}\t{item['artifact_id']}\t{item['artifact_digest']}\t"
            f"{new_count}\t{accumulated}\t{item['new_debs_manifest_sha256']}\t{item['build_manifest_sha256']}"
        )

    restored = sorted(target.glob("*.deb"))
    if len(restored) != cumulative:
        fail(f"restored DEB count {len(restored)} != expected {cumulative}")

    (evidence_out / "checkpoint-chain.tsv").write_text("\n".join(chain_rows) + "\n", encoding="utf-8")
    with (evidence_out / "checkpoint-debs.sha256").open("w", encoding="utf-8") as out:
        for deb in restored:
            out.write(f"{sha256(deb)}  {deb.name}\n")
    (evidence_out / "checkpoint-status.env").write_text(
        "\n".join(
            [
                "AURORA_KSQ_1_CHECKPOINT_CHAIN=PASS",
                f"AURORA_KSQ_1_CHECKPOINT_RANGES={len(data)}",
                f"AURORA_KSQ_1_CHECKPOINT_LAST_ORDER={expected_first - 1}",
                f"AURORA_KSQ_1_CHECKPOINT_DEBS={cumulative}",
                "AURORA_KSQ_1_CHECKPOINT_OVERLAP=none",
                "",
            ]
        ),
        encoding="utf-8",
    )
    print(f"AURORA_KSQ_1_CHECKPOINT_LAST_ORDER={expected_first - 1}")
    print(f"AURORA_KSQ_1_CHECKPOINT_DEBS={cumulative}")
    print("AURORA_KSQ_1_CHECKPOINT_CHAIN_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
