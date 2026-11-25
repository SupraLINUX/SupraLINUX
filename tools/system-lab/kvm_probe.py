"""Verify actual boot fixture, accelerator and framebuffer. No real guest OS."""
import hashlib
import json
import os
from pathlib import Path
import platform
import shutil
import subprocess
import sys
import tempfile
import time

from fixture import READY, boot_disk
from framebuffer import parse_ppm, check_fixture, png_bytes
from qmp import Qmp

def wait_for(predicate, proc, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if proc.poll() is not None:
            raise RuntimeError("QEMU exited")
        if predicate():
            return
        time.sleep(0.1)
    raise TimeoutError("Guest readiness timed out")

def attempt(accel, out):
    with tempfile.TemporaryDirectory(prefix="supra-qmp-") as tmp:
        path = Path(tmp)
        sock, disk = path / "qmp.sock", path / "boot.raw"
        marker = out / f"{accel}-guest.log"
        marker.write_bytes(b"")
        disk.write_bytes(boot_disk())
        cmd = ["qemu-system-x86_64", "-machine", "pc,accel="+accel,
               "-m", "128", "-smp", "1", "-display", "none", "-vga", "std",
               "-net", "none", "-monitor", "none", "-serial", "none",
               "-debugcon", "file:"+str(marker),
               "-qmp", "unix:"+str(sock)+",server=on,wait=off",
               "-drive", "file="+str(disk)+",format=raw,if=floppy,readonly=on",
               "-boot", "a", "-no-reboot"]
        with (out / f"{accel}-qemu.log").open("w") as log:
            proc = subprocess.Popen(cmd, stdout=log, stderr=log)
            try:
                wait_for(sock.exists, proc)
                with Qmp(sock) as qmp:
                    kvm = qmp.call("query-kvm")
                    if accel == "kvm" and not kvm["enabled"]:
                        raise RuntimeError("KVM requested but not enabled")
                    wait_for(lambda: READY in marker.read_bytes(), proc)
                    screenshot = out / f"{accel}-screen.ppm"
                    deadline = time.monotonic() + 10
                    while True:
                        qmp.call("screendump", {"filename": str(screenshot)})
                        data = screenshot.read_bytes()
                        width, height, pixels = parse_ppm(data)
                        try:
                            colors = check_fixture(width, height, pixels)
                            break
                        except ValueError:
                            if time.monotonic() >= deadline:
                                raise
                            time.sleep(0.2)
                    png = out / f"{accel}-screen.png"
                    png.write_bytes(png_bytes(width, height, pixels))
                    return {"accel": accel, "query_kvm": kvm,
                            "guest_ready": True, "fixture_verified": True,
                            "screenshot": png.name, "width": width, "height": height,
                            "screenshot_sha256": hashlib.sha256(png.read_bytes()).hexdigest(),
                            "qmp": qmp.greeting["QMP"]["version"], **colors}
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()

def main():
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report = {"schema_version": 2, "host": platform.platform(),
              "cpu_count": os.cpu_count(), "free_disk_bytes": shutil.disk_usage(out).free,
              "kvm_device": os.path.exists("/dev/kvm"),
              "kvm_access": os.access("/dev/kvm", os.R_OK | os.W_OK),
              "qemu_version": subprocess.check_output(
                  ["qemu-system-x86_64", "--version"], text=True).splitlines()[0],
              "attempts": []}
    result = None
    for accel in (["kvm", "tcg"] if report["kvm_access"] else ["tcg"]):
        try:
            result = attempt(accel, out)
            report["attempts"].append(result)
            break
        except Exception as exc:
            report["attempts"].append({"accel": accel, "error": str(exc)})
    report["status"] = ("PASS_KVM_FIXTURE" if result and result["accel"] == "kvm" else
                        "PASS_TCG_FIXTURE_KVM_NOT_VERIFIED" if result else "FAIL_FIXTURE")
    (out / "report.json").write_text(json.dumps(report, indent=2)+"\n")
    print(json.dumps(report, indent=2))
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())
