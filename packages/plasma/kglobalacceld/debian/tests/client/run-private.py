#!/usr/bin/env python3
"""Exercise owned X11 shortcuts on private Xvfb and D-Bus, then reap them."""
import os
import select
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

assert len(sys.argv) >= 4
kind, executable, result_arg = sys.argv[1:4]
assert kind in {'application', 'library', 'native'}
client = Path(executable).resolve()
results = Path(result_arg).resolve()
results.mkdir(parents=True, exist_ok=True)
processes = []

def start(command, **options):
    process = subprocess.Popen(command, env=environment, start_new_session=True, **options)
    processes.append(process)
    return process

with tempfile.TemporaryDirectory(prefix='supra-shortcuts-private-') as temporary:
    state = Path(temporary)
    environment = os.environ.copy()
    for key in ['DISPLAY','WAYLAND_DISPLAY','SESSION_MANAGER','DBUS_SESSION_BUS_ADDRESS',
                'DBUS_SYSTEM_BUS_ADDRESS','DBUS_STARTER_ADDRESS','DBUS_STARTER_BUS_TYPE',
                'LD_PRELOAD','LD_LIBRARY_PATH','QT_PLUGIN_PATH','QT_QPA_PLATFORM_PLUGIN_PATH',
                'QML_IMPORT_PATH','QML2_IMPORT_PATH']:
        environment.pop(key, None)
    for key, directory in [('HOME','home'),('XDG_RUNTIME_DIR','runtime'),('XDG_CONFIG_HOME','config'),
                           ('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache'),
                           ('XDG_CONFIG_DIRS','empty-config'),('XDG_DATA_DIRS','empty-data')]:
        path = state/directory
        path.mkdir(mode=0o700)
        environment[key] = str(path)
    environment.update(QT_QPA_PLATFORM='xcb', XDG_SESSION_TYPE='x11', KGLOBALACCELD_PLATFORM='xcb',
                       DBUS_SYSTEM_BUS_ADDRESS=f'unix:path={state}/no-system-bus', LC_ALL='C.UTF-8')
    config = state/'bus.conf'
    config.write_text('<busconfig><type>session</type><listen>unix:tmpdir='+str(state)
                      +'</listen><auth>EXTERNAL</auth><policy context="default">'
                      +'<allow send_destination="*"/><allow receive_sender="*"/>'
                      +'<allow own="*"/></policy></busconfig>')
    with (results/'xvfb-stderr').open('w') as xerr, (results/'bus-stderr').open('w') as berr, \
         (results/'daemon-stdout').open('w') as dout, (results/'daemon-stderr').open('w') as derr:
        try:
            xvfb = start(['Xvfb','-displayfd','1','-nolisten','tcp','-noreset','-screen','0','1024x768x24'],
                         stdout=subprocess.PIPE,stderr=xerr,text=True)
            assert select.select([xvfb.stdout],[],[],10)[0], 'Private Xvfb address timeout'
            number = xvfb.stdout.readline().strip()
            assert number.isdigit(), 'Invalid private Xvfb display'
            environment['DISPLAY'] = ':'+number
            environment['SUPRA_PRIVATE_XVFB_DISPLAY'] = environment['DISPLAY']
            bus = start(['dbus-daemon','--nofork','--print-address=1','--config-file='+str(config)],
                        stdout=subprocess.PIPE,stderr=berr,text=True)
            assert select.select([bus.stdout],[],[],10)[0], 'Private D-Bus address timeout'
            address = bus.stdout.readline().strip()
            assert address.startswith('unix:'), 'Invalid private D-Bus address'
            environment['DBUS_SESSION_BUS_ADDRESS'] = address
            daemon = None
            if kind == 'application':
                daemon = start(['/usr/lib/x86_64-linux-gnu/libexec/kglobalacceld'],stdout=dout,stderr=derr)
                deadline = time.monotonic()+10
                while True:
                    assert daemon.poll() is None, 'Private installed daemon exited'
                    ping = subprocess.run(['gdbus','call','--session','--dest','org.kde.kglobalaccel',
                                           '--object-path','/kglobalaccel','--method','org.freedesktop.DBus.Peer.Ping'],
                                          env=environment,capture_output=True,timeout=2)
                    if ping.returncode == 0:break
                    assert time.monotonic()<deadline, 'Private installed daemon readiness timeout'
                    time.sleep(0.05)
            with (results/'client-stdout').open('w') as cout, (results/'client-stderr').open('w') as cerr:
                # Native suite output must reach the retained clean sbuild log.
                executed = start([str(client), *sys.argv[4:]],
                                 stdout=None if kind=='native' else cout,
                                 stderr=None if kind=='native' else cerr)
                code = executed.wait(timeout=600 if kind=='native' else 30)
                if code:raise subprocess.CalledProcessError(code,[str(client),*sys.argv[4:]])
            if daemon is not None:assert daemon.poll() is None, 'Private daemon died during client execution'
        finally:
            for process in reversed(processes):
                try:os.killpg(process.pid,signal.SIGTERM)
                except ProcessLookupError:pass
                if process.poll() is None:
                    try:process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        os.killpg(process.pid,signal.SIGKILL)
                        process.wait(timeout=5)
            for process in processes:
                if process.stdout:process.stdout.close()
assert not state.exists() and all(p.poll() is not None for p in processes)
for process in processes:
    deadline = time.monotonic()+3
    while True:
        try:
            os.killpg(process.pid, 0)
        except ProcessLookupError:
            break
        assert time.monotonic() < deadline, 'Owned process group remains after cleanup'
        time.sleep(0.05)
print('Private Xvfb, D-Bus and owned daemon/client process groups reaped; temporary directory removed')
