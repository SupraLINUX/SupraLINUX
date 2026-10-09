#!/usr/bin/env python3
"""Own the sensor provider and a private D-Bus daemon, then reap both."""
import os
import select
import json
import shutil
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

assert len(sys.argv) >= 4
server, client, results = [Path(value).resolve() for value in sys.argv[1:4]]
results.mkdir(parents=True, exist_ok=True)
processes = []
with tempfile.TemporaryDirectory(prefix='supra-stats-private-') as temporary:
    state = Path(temporary)
    environment = os.environ.copy()
    for key in ['DISPLAY', 'WAYLAND_DISPLAY', 'SESSION_MANAGER', 'DBUS_SESSION_BUS_ADDRESS',
                'DBUS_SYSTEM_BUS_ADDRESS', 'QT_PLUGIN_PATH', 'QML_IMPORT_PATH', 'QML2_IMPORT_PATH']:
        environment.pop(key, None)
    for key, directory in [('HOME', 'home'), ('XDG_RUNTIME_DIR', 'runtime'), ('XDG_CONFIG_HOME', 'config'),
                           ('XDG_DATA_HOME', 'data'), ('XDG_CACHE_HOME', 'cache')]:
        path = state/directory
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(QT_QPA_PLATFORM='offscreen', QT_QUICK_BACKEND='software',
                       DBUS_SYSTEM_BUS_ADDRESS=f'unix:path={state}/no-system-bus')
    if len(sys.argv) > 4:
        source = Path(environment.pop('SUPRALINUX_NATIVE_SOURCE_ROOT')).resolve()
        build = Path(environment.pop('SUPRALINUX_NATIVE_BUILD_ROOT')).resolve()
        assert build.is_relative_to(source) and (source/'systemstats').is_dir()
        qml = list(build.rglob('org/kde/ksysguard/sensors/qmldir'))
        plugins = list(build.rglob('kf6/packagestructure/ksysguard_sensorface.so'))
        assert len(qml) == len(plugins) == 1, 'Expected one candidate QML and package-structure plugin tree'
        environment['QML_IMPORT_PATH'] = str(qml[0].parents[4])
        environment['QML2_IMPORT_PATH'] = environment['QML_IMPORT_PATH']
        environment['QT_PLUGIN_PATH'] = str(plugins[0].parents[2])
        for package in (source/'faces/facepackages').iterdir():
            if not (package/'metadata.json').is_file():
                continue
            identity = json.loads((package/'metadata.json').read_text())['KPlugin']['Id']
            assert '/' not in identity and identity.startswith('org.kde.ksysguard.')
            target = state/'data/ksysguard/sensorfaces'/identity
            shutil.copytree(package, target)
    configuration = state/'bus.conf'
    configuration.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(state)
                             +'</listen><auth>EXTERNAL</auth><policy context="default">'
                             +'<allow send_destination="*"/><allow receive_sender="*"/>'
                             +'<allow own="*"/></policy></busconfig>')
    with (results/'provider-stdout').open('w') as provider_out, (results/'provider-stderr').open('w') as provider_err, \
         (results/'bus-stderr').open('w') as bus_err:
        try:
            bus = subprocess.Popen(['dbus-daemon', '--nofork', '--print-address=1',
                                    '--config-file='+str(configuration)], env=environment,
                                   stdout=subprocess.PIPE, stderr=bus_err, text=True, start_new_session=True)
            processes.append(bus)
            assert select.select([bus.stdout], [], [], 10)[0], 'Private bus address timeout'
            environment['DBUS_SESSION_BUS_ADDRESS'] = bus.stdout.readline().strip()
            assert environment['DBUS_SESSION_BUS_ADDRESS'].startswith('unix:'), 'Invalid private bus address'
            provider = subprocess.Popen([str(server)], env=environment, stdout=provider_out,
                                        stderr=provider_err, start_new_session=True)
            processes.append(provider)
            started = time.monotonic()
            while True:
                assert provider.poll() is None, 'Private sensor provider exited'
                check = subprocess.run(['gdbus', 'call', '--session', '--dest', 'org.kde.ksystemstats1',
                                        '--object-path', '/org/kde/ksystemstats1', '--method', 'org.freedesktop.DBus.Peer.Ping'],
                                       env=environment, capture_output=True, timeout=2)
                if check.returncode == 0:
                    break
                assert time.monotonic()-started < 10, 'Private sensor provider readiness timeout'
                time.sleep(0.05)
            interface = subprocess.check_output(['gdbus', 'introspect', '--session', '--dest',
                                                 'org.kde.ksystemstats1', '--object-path', '/org/kde/ksystemstats1'],
                                                env=environment, text=True, timeout=5)
            (results/'actual-interface.txt').write_text(interface)
            with (results/'client-stdout').open('w') as output, (results/'client-stderr').open('w') as errors:
                command = [str(client), *sys.argv[4:]] if len(sys.argv) > 4 else [str(client), str(results)]
                executed = subprocess.Popen(command, env=environment, stdout=None if len(sys.argv) > 4 else output,
                                            stderr=None if len(sys.argv) > 4 else errors,
                                            start_new_session=True)
                processes.append(executed)
                code = executed.wait(timeout=600 if len(sys.argv) > 4 else 45)
                if code:
                    raise subprocess.CalledProcessError(code, command)
        finally:
            for process in reversed(processes):
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                except ProcessLookupError:
                    pass
                if process.poll() is None:
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=5)
            if processes and processes[0].stdout:
                processes[0].stdout.close()
assert not state.exists() and all(process.poll() is not None for process in processes)
for process in processes:
    deadline = time.monotonic()+3
    while True:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            break
        assert time.monotonic() < deadline, 'Owned process group remains after cleanup'
        time.sleep(0.05)
print('Owned sensor provider and D-Bus daemon reaped; runtime directory removed')
