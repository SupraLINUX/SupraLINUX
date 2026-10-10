#!/usr/bin/python3
# SPDX-License-Identifier: CC0-1.0
"""Run installed CLI tools only against owned files and a closed private bus."""
import argparse
import json
import os
import signal
import subprocess
import tempfile
import time
from pathlib import Path

parser=argparse.ArgumentParser()
parser.add_argument('client',type=Path)
parser.add_argument('output',type=Path)
args=parser.parse_args()
assert args.client.is_file() and not args.output.exists()
args.output.mkdir(parents=True)
(args.output/'payload').mkdir()
processes=[]
cleanup_errors=[]
failure=None
observation={'state':'INFRA_INVALID','scope':'private CLI fixture mechanism did not complete'}

def group_exists(pgid):
    try:
        os.killpg(pgid,0)
    except ProcessLookupError:
        return False
    return True

def wait_group_absent(pgid,seconds):
    deadline=time.monotonic()+seconds
    while group_exists(pgid) and time.monotonic()<deadline:
        time.sleep(.05)
    return not group_exists(pgid)

with tempfile.TemporaryDirectory(prefix='supra-cli-private-') as temporary:
    state=Path(temporary)
    environment={'PATH':'/usr/bin:/bin','LANG':'C.UTF-8','LC_ALL':'C.UTF-8'}
    for key,name in [('HOME','home'),('XDG_RUNTIME_DIR','runtime'),
                     ('XDG_CONFIG_HOME','config'),('XDG_DATA_HOME','data'),('XDG_CACHE_HOME','cache')]:
        directory=state/name
        directory.mkdir(mode=0o700)
        environment[key]=str(directory)
    address='unix:path='+str(state/'runtime/bus')
    environment.update(DBUS_SESSION_BUS_ADDRESS=address,
        DBUS_SYSTEM_BUS_ADDRESS=address,
        QT_QPA_PLATFORM='offscreen',QT_QUICK_BACKEND='software',
        QT_QUICK_CONTROLS_STYLE='Fusion')
    configuration=state/'bus.conf'
    configuration.write_text('<busconfig><type>session</type><listen>'+address+'</listen>'
        '<policy context="default"><allow own="*"/><allow send_destination="*"/><allow receive_sender="*"/></policy></busconfig>\n')
    try:
        with (args.output/'bus.log').open('wb') as bus_log:
            bus=subprocess.Popen(['/usr/bin/dbus-daemon','--nofork','--nopidfile',
                '--config-file='+str(configuration)],env=environment,stdout=bus_log,stderr=subprocess.STDOUT,start_new_session=True)
            processes.append(bus)
            deadline=time.monotonic()+5
            while not (state/'runtime/bus').exists() and bus.poll() is None and time.monotonic()<deadline:
                time.sleep(.05)
            assert (state/'runtime/bus').exists() and bus.poll() is None, 'Owned bus did not start'
            with (args.output/'client-stdout.log').open('wb') as stdout, (args.output/'client-stderr.log').open('wb') as stderr:
                client=subprocess.Popen([str(args.client.resolve()),str((args.output/'payload').resolve())],
                    env=environment,stdout=stdout,stderr=stderr,start_new_session=True)
                processes.append(client)
                try:
                    returncode=client.wait(timeout=60)
                except subprocess.TimeoutExpired:
                    observation={'state':'INFRA_INVALID','scope':'owned client mechanism timed out','timeout_seconds':60}
                    raise
            observation={'state':'FAIL' if returncode else 'PASS',
                'scope':'actual original installed CLI against private fixture','returncode':returncode}
            assert returncode==0,'Installed KCM fixture returned failure'
            results=[json.loads(line) for line in (args.output/'client-stdout.log').read_text().splitlines() if line.startswith('{')]
            assert results and results[-1]['state']=='PASS'
            observation.update(client_result=results[-1])
    except BaseException as exc:
        failure=exc
        observation['error']=repr(exc)
    finally:
        # Every process group was created by this invocation; continue cleanup
        # after an individual failure and retain original stdout/stderr bytes.
        for process in reversed(processes):
            try:
                os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait(timeout=3)
            if not wait_group_absent(process.pid,3):
                try:
                    os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:
                    pass
            if not wait_group_absent(process.pid,3):
                cleanup_errors.append('Owned process group remains: '+str(process.pid))
        (args.output/'result.json').write_text(json.dumps(observation,indent=2)+'\n')
assert not state.exists()
(args.output/'cleanup.json').write_text(json.dumps({
    'state':'PASS' if not cleanup_errors else 'FAIL',
    'owned_process_groups_absent':not cleanup_errors,'private_runtime_absent':not state.exists(),
    'errors':cleanup_errors},indent=2)+'\n')
print((args.output/'result.json').read_text(),end='')
print((args.output/'cleanup.json').read_text(),end='')
assert not cleanup_errors,cleanup_errors
if failure is not None:
    raise failure
