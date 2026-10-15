#!/usr/bin/env python3
"""Experimental hosted Ubuntu 26.04 QEMU/KVM CPU probe; not package certification."""
import argparse
import datetime
import hashlib
import json
import os
import platform
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

MARKER = "SUPRALINUX_HOSTED_KVM_BOOT_OK"
EXIT_VALUE = 0x2A
EXPECTED_QEMU_EXIT = (EXIT_VALUE << 1) | 1


def boot_sector():
    """Self-contained BIOS x86 16-bit first sector. Emit serial proof and exit."""
    code = bytearray()

    def write(port, value):
        # mov dx,port; mov al,value; out dx,al
        code.extend((0xBA, port & 255, port >> 8, 0xB0, value, 0xEE))

    write(0x3FB, 0x80)  # enable UART divisor latch
    write(0x3F8, 0x01)
    write(0x3F9, 0x00)
    write(0x3FB, 0x03)  # COM1 8N1
    write(0x3FA, 0xC7)  # enable and reset FIFO
    write(0x3FC, 0x0B)  # assert DTR/RTS and OUT2
    for value in (MARKER + "\n").encode("ascii"):
        # mov dx,COM1 LSR; in al,dx; test al,THRE; jz wait (-5)
        code.extend((0xBA, 0xFD, 0x03, 0xEC, 0xA8, 0x20, 0x74, 0xFB))
        write(0x3F8, value)
    # Wait for entire UART transmission before reporting completion.
    code.extend((0xBA, 0xFD, 0x03, 0xEC, 0xA8, 0x40, 0x74, 0xFB))
    write(0xF4, EXIT_VALUE)
    code.append(0xF4)  # unreachable halt
    assert len(code) <= 510
    return bytes(code).ljust(510, b"\0") + b"\x55\xaa"


def kvm_command(boot_path):
    return [
        "qemu-system-x86_64", "-machine", "pc,accel=kvm",
        "-cpu", "host", "-smp", "1", "-m", "128",
        "-display", "none", "-monitor", "none", "-serial", "stdio",
        "-no-reboot", "-boot", "order=c",
        "-drive", f"file={boot_path},format=raw,if=ide,snapshot=on",
        "-device", "isa-debug-exit,iobase=0xf4,iosize=0x04",
    ]


def tcg_command(boot_path):
    # This separate smoke certifies only the BIOS/IDE/serial boot mechanism.
    # It is never a fallback inside a KVM proof.
    cmd = kvm_command(boot_path)
    cmd[cmd.index("-machine") + 1] = "pc,accel=tcg"
    cmd[cmd.index("-cpu") + 1] = "qemu64"
    return cmd


def check_environment(require_kvm=True):
    rows = {}
    for line in Path("/etc/os-release").read_text().splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            rows[k] = v.strip('"')
    if platform.system() != "Linux" or platform.machine() != "x86_64":
        raise RuntimeError("host is not Linux x86_64")
    if rows.get("ID") != "ubuntu" or rows.get("VERSION_ID") != "26.04":
        raise RuntimeError("host is not Ubuntu 26.04")
    if require_kvm:
        kvm = Path("/dev/kvm")
        if not kvm.exists() or not stat.S_ISCHR(kvm.stat().st_mode):
            raise RuntimeError("/dev/kvm is missing or is not a character device")
        if not os.access(kvm, os.R_OK | os.W_OK):
            raise RuntimeError("/dev/kvm is not readable/writable by runner")
    return rows


def run_probe(backend="kvm"):
    assert backend in {"kvm", "tcg-smoke"}, "Refuse unknown backend"
    host = check_environment(require_kvm=(backend == "kvm"))
    with tempfile.TemporaryDirectory(prefix="supralinux-hosted-kvm-") as temp:
        boot = Path(temp) / "bootsector.img"
        boot.write_bytes(boot_sector())
        cmd = kvm_command(boot) if backend == "kvm" else tcg_command(boot)
        outcome = subprocess.run(cmd, text=True, stdout=subprocess.PIPE,
                                 stderr=subprocess.STDOUT, timeout=75, check=False)
        serial = outcome.stdout[-12000:]
        if outcome.returncode != EXPECTED_QEMU_EXIT or MARKER not in serial:
            raise RuntimeError(f"{backend} guest proof failed: exit={outcome.returncode}; serial={serial[-1600:]!r}")
        return {"guest_boot_marker": MARKER, "qemu_exit_code": outcome.returncode,
                "boot_sector_sha256": hashlib.sha256(boot.read_bytes()).hexdigest(),
                "qemu_acceleration": ("kvm-only; cpu=host; no TCG fallback" if backend == "kvm"
                                      else "tcg-only; explicit mechanism smoke; NOT KVM certification"),
                "probe_backend": backend,
                "host_os": host.get("PRETTY_NAME", "Ubuntu 26.04")}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backend", choices=["kvm", "tcg-smoke"], default="kvm")
    args = parser.parse_args()
    assert not args.output.exists(), "Refuse to overwrite evidence"
    args.output.parent.mkdir(parents=True, exist_ok=True)
    disk = os.statvfs(os.environ.get("RUNNER_TEMP", "/tmp"))
    evidence = {
        "schema": 1, "state": "INFRA_INVALID",
        "scope": ("github-hosted-ubuntu-26.04-kvm-bios-bootsector-experiment"
                  if args.backend == "kvm"
                  else "github-hosted-qemu-tcg-bootsector-mechanism-smoke-only"),
        "probe_backend": args.backend,
        "started_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source_commit": os.environ.get("GITHUB_SHA", "local"),
        "runner_image": os.environ.get("ImageOS", "unknown"),
        "runner_image_version": os.environ.get("ImageVersion", "unknown"),
        "architecture": platform.machine(), "cpu_count": os.cpu_count(),
        "runner_temp_available_bytes": disk.f_bavail * disk.f_frsize,
        "package_attempt_consumed": False,
        "authoritative_package_certification": False,
        "full_ubuntu_guest_certification": False,
        "next_gate_if_pass": "scoped-ubuntu-26.04-guest-and-autopkgtest-qemu-probe",
        "user_host_changes": False,
    }
    try:
        evidence.update(run_probe(args.backend))
        evidence["state"] = "PASS"
    except (RuntimeError, OSError, subprocess.TimeoutExpired, AssertionError) as err:
        evidence["error_type"] = type(err).__name__
        evidence["error"] = str(err)[:1900]
    evidence["finished_at"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    args.output.write_text(json.dumps(evidence, indent=2, sort_keys=True) + "\n")
    print(json.dumps(evidence, indent=2, sort_keys=True))
    return 0 if evidence["state"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
