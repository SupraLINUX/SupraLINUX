"""Fail-closed validation of rootfs console markers and boot file hashes."""
import argparse
import hashlib
import json
from pathlib import Path
import re

BOOT_FILES = {"boot/vmlinuz-linux-lts": "target-kernel",
              "boot/initramfs-linux-lts.img": "target-initrd"}


def check_builder(console, status):
    # Serial console typically uses CRLF; splitlines accepts LF or CRLF.
    lines = console.splitlines()
    exits = [s for s in lines if s.startswith("SUPRA_BUILD_VM_EXIT=")]
    if (status.strip() != "0" or exits != ["SUPRA_BUILD_VM_EXIT=0"]
            or lines.count("SUPRA_BUILD_VM_READY") != 1
            or lines.index("SUPRA_BUILD_VM_READY") >= lines.index(exits[0])):
        raise ValueError("Missing or inconsistent builder readiness/exit evidence")


def parse_hashes(content):
    result = {}
    for line in content.splitlines():
        match = re.fullmatch(r"([0-9a-f]{64})  (boot/[A-Za-z0-9.-]+)", line)
        if not match:
            raise ValueError("Malformed boot hash entry")
        digest, path = match.groups()
        if path not in BOOT_FILES or path in result:
            raise ValueError("Unexpected or duplicate boot hash entry")
        result[path] = digest
    if result.keys() != BOOT_FILES.keys():
        raise ValueError("Incomplete boot hashes")
    return result


def check_hashes(content, work):
    for path, digest in parse_hashes(content).items():
        actual = hashlib.sha256()
        with (work / BOOT_FILES[path]).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                actual.update(chunk)
        if actual.hexdigest() != digest:
            raise ValueError(f"Extracted boot file mismatch: {path}")


def check_target(console):
    if console.splitlines().count("SUPRA_TARGET_BOOT_READY") != 1:
        raise ValueError("Target did not emit unique readiness marker")


def target_report(console, accel):
    check_target(console)
    if accel not in ("kvm", "tcg"):
        raise ValueError("Unknown target accelerator")
    return {"schema_version": 2, "direct_kernel_boot_verified": True,
            "accelerator": accel, "kvm_target_boot_verified": accel == "kvm",
            "uefi_boot_verified": False, "release_signed": False}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("phase", choices=["builder", "hashes", "target"])
    p.add_argument("evidence", type=Path)
    p.add_argument("work", type=Path, nargs="?")
    p.add_argument("--accel", choices=["kvm", "tcg"])
    a = p.parse_args()
    if a.phase == "builder":
        check_builder((a.evidence / "rootfs-vm-console.log").read_text(errors="replace"),
                      (a.evidence / "rootfs-vm-status.txt").read_text())
        print("Builder readiness and clean exit verified")
    elif a.phase == "hashes":
        if a.work is None:
            p.error("hashes phase requires extracted boot files directory")
        check_hashes((a.evidence / "rootfs-boot-files.sha256").read_text(), a.work)
        print("Extracted kernel and initramfs hashes verified")
    else:
        if a.accel is None:
            p.error("target phase requires explicit accelerator")
        report = target_report((a.evidence / "rootfs-target-console.log").read_text(errors="replace"), a.accel)
        (a.evidence / "rootfs-target-boot.json").write_text(json.dumps(report, sort_keys=True) + "\n")
        print("Direct target kernel boot verified")


if __name__ == "__main__":
    main()
