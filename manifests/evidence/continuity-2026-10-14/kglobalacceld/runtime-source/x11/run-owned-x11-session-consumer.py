#!/usr/bin/env python3
"""Run a reviewed original X11 window manager, daemon and owned client in KVM."""
import argparse
import json
import os
import select
import signal
import subprocess
import tempfile
import time
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--config', type=Path, required=True)
p.add_argument('--phase', required=True)
p.add_argument('--window-manager', type=Path, required=True)
p.add_argument('--daemon', type=Path, required=True)
p.add_argument('--consumer', type=Path, required=True)
p.add_argument('--xvfb', type=Path, required=True)
p.add_argument('--dbus-daemon', type=Path, required=True)
p.add_argument('--gdbus', type=Path, required=True)
p.add_argument('--probe-only', action='store_true')
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parent
for path in (a.config, a.window_manager, a.daemon, a.consumer, a.xvfb, a.dbus_daemon, a.gdbus):
    assert path.is_file() and path.resolve().is_relative_to(root)
assert sorted(p.name for p in Path('/sys/class/net').iterdir()) == ['lo']
assert subprocess.check_output(['systemd-detect-virt'], text=True).strip() == 'kvm'
a.output.mkdir(parents=True, exist_ok=False)
config = json.loads(a.config.read_text())['phases'][a.phase]
result = {'state': 'FAIL', 'scope': 'Owned original X11 session without GPU compositing, zero-NIC KVM',
          'canonical_effect': 'none', 'package_attempt_consumed': False}
processes = []


def stop_signal(signum, frame):
    raise RuntimeError('Owned X11 session interrupted: ' + str(signum))


def start(command, **options):
    process = subprocess.Popen(command, env=environment, start_new_session=True, **options)
    processes.append(process)
    return process


def ready(process, bus_name, object_path, logfile):
    deadline = time.monotonic() + 30
    while True:
        assert process.poll() is None, 'Owned process exited before readiness: ' + bus_name
        ping = subprocess.run([str(a.gdbus), 'call', '--session', '--dest', bus_name,
                               '--object-path', object_path, '--method', 'org.freedesktop.DBus.Peer.Ping'],
                              env=environment, capture_output=True, timeout=2)
        logfile.write_bytes(ping.stdout + ping.stderr)
        if ping.returncode == 0:
            return
        assert time.monotonic() < deadline, 'Owned bus readiness deadline: ' + bus_name
        time.sleep(0.1)


signal.signal(signal.SIGTERM, stop_signal)
signal.signal(signal.SIGINT, stop_signal)
with tempfile.TemporaryDirectory(prefix='supra-x11-session-private-') as temporary:
    state = Path(temporary)
    environment = os.environ.copy()
    for key in ['DISPLAY', 'WAYLAND_DISPLAY', 'SESSION_MANAGER', 'DBUS_SESSION_BUS_ADDRESS',
                'DBUS_SYSTEM_BUS_ADDRESS', 'DBUS_STARTER_ADDRESS', 'DBUS_STARTER_BUS_TYPE',
                'LD_PRELOAD', 'LD_LIBRARY_PATH', 'QT_PLUGIN_PATH', 'QT_QPA_PLATFORM_PLUGIN_PATH',
                'QML_IMPORT_PATH', 'QML2_IMPORT_PATH', 'KWIN_WAYLAND_NO_PERMISSION_CHECKS']:
        environment.pop(key, None)
    for key, directory in [('HOME', 'home'), ('XDG_RUNTIME_DIR', 'runtime'), ('XDG_CONFIG_HOME', 'config'),
                           ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache'), ('XDG_CONFIG_DIRS', 'empty-config')]:
        path = state / directory
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    for key, values in config.items():
        assert key in {'LD_LIBRARY_PATH', 'QT_PLUGIN_PATH', 'LIBGL_DRIVERS_PATH',
                       '__EGL_VENDOR_LIBRARY_FILENAMES', 'QML_IMPORT_PATH', 'QML2_IMPORT_PATH',
                       'XDG_DATA_DIRS', 'XKB_CONFIG_ROOT'}
        for value in values:
            assert Path(value).resolve().is_relative_to(root) and Path(value).exists(), (key, value)
        environment[key] = ':'.join(values)
    environment.update(LD_BIND_NOW='1', LD_DEBUG='libs', LIBGL_ALWAYS_SOFTWARE='1',
                       KWIN_COMPOSE='N', QT_QUICK_BACKEND='software', QT_QPA_PLATFORM='xcb',
                       KGLOBALACCELD_PLATFORM='xcb', XDG_SESSION_TYPE='x11',
                       QT_LOGGING_RULES='kwin_core.debug=true',
                       DBUS_SYSTEM_BUS_ADDRESS=f'unix:path={state}/no-system-bus', LC_ALL='C.UTF-8')
    (state / 'config/kwinrc').write_text('[Compositing]\nEnabled=false\n[org.kde.kdecoration2]\nNoPlugin=true\n')
    bus_config = state / 'bus.conf'
    bus_config.write_text('<busconfig><type>session</type><listen>unix:tmpdir=' + str(state)
        + '</listen><auth>EXTERNAL</auth><policy context="default">'
        + '<allow send_destination="*"/><allow receive_sender="*"/><allow own="*"/>'
        + '</policy></busconfig>')
    with (a.output / 'xvfb-stderr.log').open('w') as xerr, (a.output / 'bus-stderr.log').open('w') as berr, \
         (a.output / 'daemon-stdout.log').open('w') as dout, (a.output / 'daemon-stderr.log').open('w') as derr, \
         (a.output / 'window-manager-stdout.log').open('w') as kout, (a.output / 'window-manager-stderr.log').open('w') as kerr, \
         (a.output / 'consumer-stdout.log').open('w') as cout, (a.output / 'consumer-stderr.log').open('w') as cerr:
        try:
            xvfb = start([str(a.xvfb), '-displayfd', '1', '-nolisten', 'tcp', '-noreset', '-screen', '0', '1024x768x24'],
                         stdout=subprocess.PIPE, stderr=xerr, text=True)
            assert select.select([xvfb.stdout], [], [], 10)[0], 'Owned Xvfb address deadline'
            number = xvfb.stdout.readline().strip()
            assert number.isdigit()
            environment['DISPLAY'] = ':' + number
            environment['SUPRA_PRIVATE_XVFB_DISPLAY'] = environment['DISPLAY']
            bus = start([str(a.dbus_daemon), '--nofork', '--print-address=1', '--config-file=' + str(bus_config)],
                        stdout=subprocess.PIPE, stderr=berr, text=True)
            assert select.select([bus.stdout], [], [], 10)[0], 'Owned D-Bus address deadline'
            address = bus.stdout.readline().strip()
            assert address.startswith('unix:')
            environment['DBUS_SESSION_BUS_ADDRESS'] = address
            daemon = start([str(a.daemon)], stdout=dout, stderr=derr)
            ready(daemon, 'org.kde.kglobalaccel', '/kglobalaccel', a.output / 'daemon-readiness.log')
            window_manager = start([str(a.window_manager), '--no-kactivities'], stdout=kout, stderr=kerr)
            ready(window_manager, 'org.kde.KWin', '/KWin', a.output / 'window-manager-readiness.log')
            support = subprocess.run([str(a.gdbus), 'call', '--session', '--dest', 'org.kde.KWin',
                                      '--object-path', '/KWin', '--method', 'org.kde.KWin.supportInformation'],
                                     env=environment, capture_output=True, text=True, timeout=5)
            (a.output / 'window-manager-support.log').write_text(support.stdout + support.stderr)
            assert support.returncode == 0 and 'X11' in support.stdout, 'Actual original X11 workspace not established'
            result['owned_original_x11_workspace_and_daemon_ready'] = 'PASS'
            if a.probe_only:
                result['consumer_execution'] = 'NOT RUN; small session mechanism certification'
            else:
                consumer = start([str(a.consumer)], stdout=cout, stderr=cerr)
                code = consumer.wait(timeout=45)
                result['consumer_exit_code'] = code
                assert code == 0, 'Unchanged original public client assertions failed'
            assert xvfb.poll() is None and daemon.poll() is None and window_manager.poll() is None
            result['state'] = 'PASS'
        except Exception as error:
            result['error'] = str(error)
        finally:
            signal.signal(signal.SIGTERM, signal.SIG_IGN)
            for process in reversed(processes):
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait(timeout=5)
                if process.stdout:
                    process.stdout.close()
            result['owned_processes_reaped'] = all(p.poll() is not None for p in processes)
result['owned_temporary_directory_removed'] = not state.exists()
(a.output / 'result.json').write_text(json.dumps(result, indent=2) + '\n')
print(json.dumps(result))
raise SystemExit(0 if result['state'] == 'PASS' and result['owned_processes_reaped'] and result['owned_temporary_directory_removed'] else 1)
