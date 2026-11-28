"""Bounded fault injection into a child disposable QEMU process only."""
import json
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
import os

MARKER = b"SUPRA_TRIAL_INTERRUPT_POINT"


def interrupt(command, log, timeout=150, marker=MARKER):
    if marker not in (MARKER, b'SUPRA_INSTALL_INTERRUPT_POINT'):
        raise ValueError('Unknown laboratory checkpoint')
    deadline = time.monotonic() + timeout
    pending = b""
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as proc, selectors.DefaultSelector() as sel:
        sel.register(proc.stdout, selectors.EVENT_READ)
        try:
            while time.monotonic() < deadline:
                if not sel.select(max(0, deadline - time.monotonic())):
                    break
                chunk = os.read(proc.stdout.fileno(), 65536)
                if not chunk:
                    break
                log.write(chunk)
                log.flush()
                pending += chunk
                lines = pending.split(b"\n")
                pending = lines.pop()
                if len(pending) > 1024 * 1024:
                    raise RuntimeError("Unbounded console line")
                if any(line.rstrip(b"\r") == marker for line in lines):
                    proc.kill()
                    code = proc.wait(timeout=10)
                    tail = proc.stdout.read()
                    log.write(tail)
                    log.flush()
                    if code != -signal.SIGKILL:
                        raise RuntimeError("Child did not terminate by injected SIGKILL")
                    return {"marker": marker.decode(), "signal": "SIGKILL", "returncode": code}
            raise RuntimeError("Guest did not reach interruption checkpoint")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)


if __name__ == "__main__":
    args = sys.argv[3:]
    marker = MARKER
    if args and args[0] == "--install":
        marker = b"SUPRA_INSTALL_INTERRUPT_POINT"
        args = args[1:]
    if len(args) < 2 or args[0] != "--" or args[1] != "qemu-system-x86_64":
        raise SystemExit("Expected disposable QEMU invocation")
    with Path(sys.argv[1]).open("wb") as log:
        evidence = interrupt(args[1:], log, timeout=300, marker=marker)
    Path(sys.argv[2]).write_text(json.dumps(evidence, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))
