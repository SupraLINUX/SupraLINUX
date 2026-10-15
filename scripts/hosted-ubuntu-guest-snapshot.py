#!/usr/bin/env python3
"""SHA-256 admission for rebuildable hosted Ubuntu QEMU milestones."""
import datetime
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "scripts/hosted-ubuntu-guest-lane.sh"
KEYRING = Path("/usr/share/keyrings/ubuntu-archive-keyring.gpg")


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def image_info(image):
    j = json.loads(subprocess.check_output(["qemu-img", "info", "--output=json", str(image)], text=True))
    assert j["format"] == "qcow2" and j["virtual-size"] == 8 * 1024**3
    assert not j.get("backing-filename"), "Milestone must be independent"
    return {"sha256": sha(image), "size": j["virtual-size"]}


def smoke(summary):
    lines = Path(summary).read_text().splitlines()
    assert sum(bool(re.fullmatch(r"guest-smoke\s+PASS", s.strip())) for s in lines) == 1, "Missing exact guest PASS"
    assert not any(re.search(r"\b(FAIL|SKIP|FLAKY)\b", s) for s in lines), "Other failing/skipped DEP-8 tests"
    return sha(summary)


def check(image, path, require_pass=False):
    j = json.loads(path.read_text())
    assert j["schema"] == 1 and j["scope"] == "hosted-resolute-amd64-qemu-milestone"
    assert j["series"] == "resolute" and j["arch"] == "amd64"
    assert j["builder_sha256"] == sha(BUILDER), "Builder input drift"
    assert j["ubuntu_keyring_sha256"] == sha(KEYRING), "Ubuntu trust drift"
    assert j["base"] == image_info(image), "Snapshot hash/format drift"
    created = datetime.datetime.fromisoformat(j["created_at"])
    age = datetime.datetime.now(datetime.timezone.utc) - created
    assert 0 <= age.total_seconds() <= 8 * 86400, "Snapshot stale"
    assert j["package_attempt_consumed"] is False and j["release_certified"] is False
    if require_pass:
        assert j["state"] == "PASS" and j["dep8_pass"] is True, "Uncertified snapshot cannot be reused"
        assert re.fullmatch(r"[0-9a-f]{40}", j["validated_by_sha"])
    return j


def main():
    action, image, path, *rest = sys.argv[1:]
    image, path = Path(image), Path(path)
    if action == "create":
        assert not path.exists()
        j = {"schema": 1, "scope": "hosted-resolute-amd64-qemu-milestone",
             "state": "PREPARED", "dep8_pass": False, "series": "resolute", "arch": "amd64",
             "builder_sha256": sha(BUILDER), "ubuntu_keyring_sha256": sha(KEYRING),
             "base": image_info(image),
             "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
             "package_attempt_consumed": False, "release_certified": False}
        path.write_text(json.dumps(j, indent=2, sort_keys=True) + "\n")
    elif action == "verify":
        check(image, path, True)
    elif action == "inspect":
        check(image, path, False)
    elif action == "test":
        check(image, path, False)
        assert len(rest) == 1
        print("DEP-8 smoke summary sha256:", smoke(rest[0]))
    elif action == "seal":
        assert len(rest) == 1
        j = check(image, path, False)
        assert j["state"] == "PREPARED"
        j["dep8_summary_sha256"] = smoke(rest[0])
        j["dep8_pass"] = True
        j["state"] = "PASS"
        j["validated_by_sha"] = subprocess.check_output(
            ["git", "-C", str(ROOT), "rev-parse", "HEAD"], text=True).strip()
        path.write_text(json.dumps(j, indent=2, sort_keys=True) + "\n")
    else:
        raise SystemExit("Unknown snapshot action")
    print("Hosted Ubuntu guest milestone check:", action, "PASS")


if __name__ == "__main__":
    main()
