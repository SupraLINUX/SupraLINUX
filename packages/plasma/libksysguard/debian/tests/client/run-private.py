#!/usr/bin/env python3
"""Own the sensor provider and a private D-Bus daemon, then reap both."""
import os
import hashlib
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
        plugins = list(build.rglob('ksysguard_sensorface.so'))
        assert len(qml) == len(plugins) == 1, 'Expected one native QML and package-structure plugin output'
        assert qml[0].resolve().is_relative_to(build) and qml[0].parents[4] == build/'bin'
        assert 'module org.kde.ksysguard.sensors' in qml[0].read_text().splitlines(), 'Wrong native QML URI'
        plugin = plugins[0]
        assert plugin == build/'bin/ksysguard_sensorface.so' and plugin.resolve().is_relative_to(build), 'Foreign native plugin output'
        payload = plugin.read_bytes()
        assert len(payload) >= 64 and payload[:6] == b'\x7fELF\x02\x01' and int.from_bytes(payload[18:20], 'little') == 62, 'Expected amd64 ELF plugin'
        plugin_root = state/'qt-plugins'
        staged_plugin = plugin_root/'kf6/packagestructure/ksysguard_sensorface.so'
        staged_plugin.parent.mkdir(parents=True)
        staged_plugin.write_bytes(payload)
        assert staged_plugin.read_bytes() == payload, 'Native plugin staging changed bytes'
        inputs = {'scope': 'owned native runtime input staging; no package result',
                  'source_root': str(source), 'build_root': str(build),
                  'qml_import_root': str(qml[0].parents[4]),
                  'qml_dir_sha256': hashlib.sha256(qml[0].read_bytes()).hexdigest(),
                  'plugin_build_path': str(plugin), 'plugin_staged_path': str(staged_plugin), 'plugin_install_namespace': 'kf6/packagestructure/ksysguard_sensorface.so',
                  'plugin_sha256': hashlib.sha256(payload).hexdigest(), 'byte_preserving_private_staging': True}
        (results/'native-inputs.json').write_text(json.dumps(inputs, indent=2)+'\n')
        print('Owned native input staging: '+json.dumps(inputs, sort_keys=True), flush=True)
        environment['QML_IMPORT_PATH'] = str(qml[0].parents[4])
        environment['QML2_IMPORT_PATH'] = environment['QML_IMPORT_PATH']
        environment['QT_PLUGIN_PATH'] = str(plugin_root)
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
