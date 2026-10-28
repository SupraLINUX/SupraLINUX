#!/usr/bin/env python3
"""Exercise a real private Wayland socket with both old and rebuilt clients."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

server, client, output = map(Path, sys.argv[1:])
output.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory() as directory:
    runtime = Path(directory)
    runtime.chmod(0o700)
    env = dict(os.environ, XDG_RUNTIME_DIR=str(runtime))
    with (output/'server.log').open('w') as log:
        process = subprocess.Popen([str(server)], env=env, stdout=log, stderr=subprocess.STDOUT)
        try:
            deadline = time.monotonic()+10
            while not (runtime/'supra-wire').exists():
                assert process.poll() is None and time.monotonic() < deadline, 'Private Wayland server did not start'
                time.sleep(0.02)
            for version in [1, 7, 8, 20]:
                execution = subprocess.run([str(client), str(version)], env=env, timeout=10,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
                (output/f'client-version-{version}.log').write_text(execution.stdout)
                assert execution.returncode == 0, execution.stdout
                assert f'negotiated version {version}, candidate server PID event 4242: PASS' in execution.stdout
                print(execution.stdout, end='')
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
