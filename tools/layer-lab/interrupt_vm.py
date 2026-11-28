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


def interrupt(command, log, timeout=150):
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
                if any(line.rstrip(b"\r") == MARKER for line in lines):
                    proc.kill()
                    code = proc.wait(timeout=10)
                    tail = proc.stdout.read()
                    log.write(tail)
                    log.flush()
                    if code != -signal.SIGKILL:
                        raise RuntimeError("Child did not terminate by injected SIGKILL")
                    return {"marker": MARKER.decode(), "signal": "SIGKILL", "returncode": code}
            raise RuntimeError("Guest did not reach interruption checkpoint")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=10)


if __name__ == "__main__":
    if len(sys.argv) < 5 or sys.argv[3] != "--" or sys.argv[4] != "qemu-system-x86_64":
        raise SystemExit("Expected disposable QEMU invocation")
    with Path(sys.argv[1]).open("wb") as log:
        evidence = interrupt(sys.argv[4:], log)
    Path(sys.argv[2]).write_text(json.dumps(evidence, sort_keys=True) + "\n")
    print(json.dumps(evidence, sort_keys=True))
