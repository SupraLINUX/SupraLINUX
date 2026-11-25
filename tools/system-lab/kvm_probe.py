"""Runner capability probe: no downloaded guest OS, disks, network or host mutation."""
import json
import os
import pathlib
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time

out = pathlib.Path(sys.argv[1]).resolve()
out.mkdir(parents=True, exist_ok=True)
report = {"host": platform.platform(), "cpu_count": os.cpu_count(),
          "free_disk_bytes": shutil.disk_usage(out).free,
          "kvm_device": os.path.exists("/dev/kvm"),
          "kvm_access": os.access("/dev/kvm", os.R_OK | os.W_OK)}
report["qemu_version"] = subprocess.check_output(
    ["qemu-system-x86_64", "--version"], text=True).splitlines()[0]
# Tiny original boot sector: write a known message via BIOS teletype, then halt.
# This is a disposable synthetic guest, not the SupraLINUX operating system.
message = b"SUPRA SYSTEM LAB - VM BOOT OK\r\n"
code = bytearray([0x31,0xc0,0x8e,0xd8,0xbe,0x00,0x00,0xac,0x84,0xc0,
                  0x74,0x08,0xb4,0x0e,0xbb,0x07,0x00,0xcd,0x10,0xeb,0xf3,
                  0xfa,0xf4,0xeb,0xfd])
address = 0x7c00 + len(code)
code[5:7] = address.to_bytes(2, "little")
sector = (code + message + b"\x00").ljust(510, b"\x00") + b"\x55\xaa"
def attempt(accel):
    with tempfile.TemporaryDirectory(prefix="supra-qmp-") as tmp:
        path = pathlib.Path(tmp)
        sock = path / "qmp.sock"
        disk = path / "boot.raw"
        disk.write_bytes(sector.ljust(1474560, b"\x00"))
        cmd = ["qemu-system-x86_64", "-machine", "pc,accel="+accel,
               "-m", "128", "-smp", "1", "-display", "none", "-vga", "std",
               "-net", "none", "-monitor", "none", "-serial", "none",
               "-qmp", "unix:"+str(sock)+",server=on,wait=off",
               "-drive", "file="+str(disk)+",format=raw,if=floppy,readonly=on",
               "-boot", "a", "-no-reboot"]
        with (out / (accel+"-qemu.log")).open("w") as log:
            proc = subprocess.Popen(cmd, stdout=log, stderr=log)
            try:
                deadline = time.monotonic()+20
                while not sock.exists():
                    if proc.poll() is not None or time.monotonic()>deadline:
                        raise RuntimeError("QEMU exited or QMP socket unavailable")
                    time.sleep(0.1)
                with socket.socket(socket.AF_UNIX) as s:
                    s.settimeout(15)
                    s.connect(str(sock))
                    with s.makefile("rwb") as stream:
                        def read():
                            line = stream.readline()
                            if not line:
                                raise RuntimeError("QMP closed")
                            return json.loads(line)
                        def call(command, arguments=None):
                            request = {"execute": command}
                            if arguments is not None:
                                request["arguments"] = arguments
                            stream.write((json.dumps(request)+"\n").encode())
                            stream.flush()
                            while True:
                                response = read()
                                if "error" in response:
                                    raise RuntimeError(str(response["error"]))
                                if "return" in response:
                                    return response["return"]
                        greeting = read()
                        call("qmp_capabilities")
                        kvm = call("query-kvm")
                        # Wait for BIOS and tiny guest to reach its screen.
                        time.sleep(8 if accel == "tcg" else 4)
                        screenshot = out / (accel+"-screen.ppm")
                        call("screendump", {"filename": str(screenshot)})
                        if screenshot.stat().st_size < 100:
                            raise RuntimeError("Empty screenshot")
                        result = {"accel": accel, "query_kvm": kvm,
                                  "screenshot": screenshot.name,
                                  "screenshot_bytes": screenshot.stat().st_size,
                                  "qmp": greeting["QMP"]["version"]}
                        if accel == "kvm" and not kvm["enabled"]:
                            raise RuntimeError("KVM requested but not enabled")
                        return result
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
report["attempts"] = []
result = None
for accel in (["kvm", "tcg"] if report["kvm_access"] else ["tcg"]):
    try:
        result = attempt(accel)
        report["attempts"].append(result)
        break
    except Exception as exc:
        report["attempts"].append({"accel": accel, "error": str(exc)})
report["status"] = "PASS_KVM_CAPTURE" if result and result["accel"] == "kvm" else (
    "PASS_TCG_CAPTURE_KVM_UNAVAILABLE" if result else "FAIL_CAPTURE")
(out / "report.json").write_text(json.dumps(report, indent=2)+"\n")
print(json.dumps(report, indent=2))
# QMP capture success does not prove the message is visually correct.
# Verify the artifact separately. No OS boot claim.
sys.exit(0 if result else 1)
