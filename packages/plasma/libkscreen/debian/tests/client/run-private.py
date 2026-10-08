#!/usr/bin/env python3
import os
from pathlib import Path
import resource
import select
import signal
import subprocess
import sys
import tempfile
import time

client, profile, destination = map(Path, sys.argv[1:4])
mode = sys.argv[4:]
assert mode in [[], ['xrandr']]
destination.mkdir(parents=True, exist_ok=True)
processes = []
def limits(): resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
def start(argv, env, **streams):
    process = subprocess.Popen(argv, env=env, start_new_session=True, preexec_fn=limits, **streams)
    processes.append(process)
    return process
def first_line(process):
    assert select.select([process.stdout], [], [], 8)[0], 'Private provider readiness timeout'
    line = process.stdout.readline().decode().strip()
    assert line and process.poll() is None, 'Private provider exited during startup'
    return line
with tempfile.TemporaryDirectory(prefix='supralinux-kscreen-') as temporary:
    root = Path(temporary)
    runtime = root/'runtime'; runtime.mkdir(mode=0o700)
    env = os.environ.copy()
    for key in ['DBUS_SESSION_BUS_ADDRESS', 'DBUS_SYSTEM_BUS_ADDRESS', 'DISPLAY', 'WAYLAND_DISPLAY', 'SESSION_MANAGER', 'QT_PLUGIN_PATH', 'QML_IMPORT_PATH', 'QML2_IMPORT_PATH']:
        env.pop(key, None)
    env.update(XDG_RUNTIME_DIR=str(runtime), XDG_CONFIG_HOME=str(root/'config'), XDG_DATA_HOME=str(root/'data'),
               XDG_CACHE_HOME=str(root/'cache'), QT_QPA_PLATFORM='xcb', KSCREEN_BACKEND='XRandR' if mode else 'Fake',
               KSCREEN_BACKEND_INPROCESS='0', KSCREEN_LOGGING='false', LC_ALL='C.UTF-8',
               DBUS_SYSTEM_BUS_ADDRESS='unix:path='+str(runtime/'no-system-bus'))
    config = root/'bus.conf'
    config.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(runtime)+'</listen>'
                      '<policy context="default"><allow own="*"/><allow send_destination="*"/>'
                      '<allow receive_sender="*"/></policy></busconfig>')
    try:
        with (destination/'bus.log').open('w') as buslog, (destination/'xvfb.log').open('w') as xlog, (destination/'launcher.log').open('w') as launchlog:
            bus = start(['dbus-daemon', '--nofork', '--config-file='+str(config), '--print-address=1'], env,
                        stdout=subprocess.PIPE, stderr=buslog)
            env['DBUS_SESSION_BUS_ADDRESS'] = first_line(bus)
            display = start(['Xvfb', '-displayfd', '1', '-nolisten', 'tcp', '-screen', '0', '1280x800x24'], env,
                            stdout=subprocess.PIPE, stderr=xlog)
            env['DISPLAY'] = ':'+first_line(display)
            helpers = list(Path('/usr/lib').glob('*/libexec/kf6/kscreen_backend_launcher'))
            assert len(helpers) == 1, 'Installed launcher path ambiguous'
            launcher = start([str(helpers[0])], env, stdout=launchlog, stderr=subprocess.STDOUT)
            deadline = time.monotonic()+8
            ready = False
            while time.monotonic() < deadline and launcher.poll() is None:
                probe = subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.kde.KScreen', '--object-path', '/',
                                        '--method', 'org.freedesktop.DBus.Peer.Ping'], env=env, capture_output=True, timeout=3)
                if probe.returncode == 0: ready = True; break
                time.sleep(0.05)
            assert ready, 'Owned installed backend launcher did not start'
            result = subprocess.run([str(client.resolve()), str(profile.resolve()), *mode], env=env, capture_output=True,
                                    text=True, timeout=45, preexec_fn=limits)
            (destination/'client.log').write_text(result.stdout+result.stderr)
            print(result.stdout+result.stderr, flush=True)
            assert result.returncode == 0, result.returncode
            markers = ['Installed KScreen XRandR backend on private Xvfb'] if mode else ['Installed KScreen D-Bus/Fake backend', 'Installed ScreenDpms construction/properties']
            for marker in markers:
                assert marker in result.stdout, marker
    finally:
        for process in reversed(processes):
            if process.poll() is None:
                os.killpg(process.pid, signal.SIGTERM)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired: os.killpg(process.pid, signal.SIGKILL); process.wait()
            if process.stdout is not None: process.stdout.close()
print('Owned installed launcher, private D-Bus and Xvfb reaped; runtime directory removed')
