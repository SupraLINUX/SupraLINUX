#!/usr/bin/env python3
import os
from pathlib import Path
import resource
import signal
import subprocess
import sys
import tempfile
import time

server, client, destination = map(Path, sys.argv[1:])
destination.mkdir(parents=True, exist_ok=True)
with tempfile.TemporaryDirectory(prefix='supralinux-kwayland-') as temporary:
    root = Path(temporary)
    runtime = root/'runtime';runtime.mkdir(mode=0o700)
    env = os.environ.copy()
    for key in ['DBUS_SESSION_BUS_ADDRESS','DBUS_SYSTEM_BUS_ADDRESS','DISPLAY','WAYLAND_DISPLAY','SESSION_MANAGER']:
        env.pop(key, None)
    env.update(XDG_RUNTIME_DIR=str(runtime), XDG_CONFIG_HOME=str(root/'config'), XDG_DATA_HOME=str(root/'data'),
               XDG_CACHE_HOME=str(root/'cache'), QT_QPA_PLATFORM='offscreen', LC_ALL='C.UTF-8')
    def limits(): resource.setrlimit(resource.RLIMIT_CORE, (0,0))
    with (destination/'server.log').open('w') as log:
        process = subprocess.Popen([str(server.resolve())], env=env, stdout=log, stderr=subprocess.STDOUT,
                                   start_new_session=True, preexec_fn=limits)
        try:
            deadline = time.monotonic()+8
            while not (runtime/'supra-compat').exists() and process.poll() is None and time.monotonic()<deadline:
                time.sleep(0.02)
            assert (runtime/'supra-compat').is_socket(), 'Private server did not start'
            result = subprocess.run([str(client.resolve())], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                    text=True, timeout=45, preexec_fn=limits)
            (destination/'client.log').write_text(result.stdout)
            print(result.stdout, flush=True)
            assert result.returncode == 0, result.returncode
        finally:
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: os.killpg(process.pid,signal.SIGKILL);process.wait()
    output = (destination/'server.log').read_text()
    print(output, flush=True)
    for marker in ['Native surface scale/region/damage/commit/frame verified','Native surface resource destroyed',
                   'Native window state request verified','Native window close request verified']:
        assert marker in output, marker
print('Owned private Wayland server reaped and runtime directory removed')
