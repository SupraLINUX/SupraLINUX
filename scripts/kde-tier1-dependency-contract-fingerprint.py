#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = "manifests/kde-frameworks-tier1-dependencies.json"


def load_manifest(ref: str | None, path: str) -> dict:
    if ref is None:
        return json.loads((ROOT / path).read_text(encoding="utf-8"))
    raw = subprocess.check_output(["git", "show", f"{ref}:{path}"], cwd=ROOT, text=True)
    return json.loads(raw)


def contract(manifest: dict) -> dict:
    provider = manifest.get("provider_candidate", {})
    return {
        "schema": manifest.get("schema"),
        "authority": manifest.get("authority"),
        "frameworks": manifest.get("frameworks"),
        "target": manifest.get("target"),
        "provider": {
            "distribution": provider.get("distribution"),
            "series": provider.get("series"),
        },
        "common": manifest.get("common"),
        "qt_provider_packages": manifest.get("qt_provider_packages"),
        "requirements": manifest.get("requirements"),
        "nodes": manifest.get("nodes"),
    }


def serialized_contract(manifest: dict) -> bytes:
    return json.dumps(contract(manifest), sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Print the semantic provider-input fingerprint for the KDE Tier 1 dependency manifest.")
    parser.add_argument("--git-ref", default=None, help="Read the manifest from this git commit/ref instead of the working tree.")
    parser.add_argument("--manifest", default=DEFAULT_MANIFEST, help="Repository-relative manifest path.")
    parser.add_argument("--json", action="store_true", help="Print the normalized contract JSON instead of its SHA-256.")
    args = parser.parse_args()

    data = load_manifest(args.git_ref, args.manifest)
    payload = serialized_contract(data)
    if args.json:
        print(payload.decode("utf-8"))
    else:
        print(hashlib.sha256(payload).hexdigest())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
