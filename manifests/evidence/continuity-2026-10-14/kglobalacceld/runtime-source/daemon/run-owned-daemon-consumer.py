#!/usr/bin/env python3
"""Test a frozen daemon and consumer on the caller's owned private bus/display."""
import argparse
import json
import os
import signal
import subprocess
import time
from pathlib import Path

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--daemon', type=Path, required=True)
p.add_argument('--consumer', type=Path, required=True)
p.add_argument('--gdbus', type=Path, required=True)
p.add_argument('--output', type=Path, required=True)
a = p.parse_args()
root = Path(__file__).resolve().parent
for path in (a.daemon, a.consumer, a.gdbus):
    assert path.resolve().is_relative_to(root) and path.is_file()
assert os.environ['DISPLAY'] == os.environ['SUPRA_PRIVATE_XVFB_DISPLAY']
assert Path(os.environ['HOME']).parent.name.startswith('supra-shortcuts-private-')
assert os.environ['DBUS_SESSION_BUS_ADDRESS'].startswith('unix:')
a.output.mkdir(parents=True, exist_ok=False)
processes = []
result = {'state': 'NOT RUN', 'canonical_effect': 'none', 'package_attempt_consumed': False}
def stop_signal(signum, frame):
    raise RuntimeError('Owned consumer interrupted: ' + str(signum))
signal.signal(signal.SIGTERM, stop_signal)
signal.signal(signal.SIGINT, stop_signal)
def start(command, stdout, stderr):
    process = subprocess.Popen(command, stdout=stdout, stderr=stderr, start_new_session=True)
    processes.append(process)
    return process
try:
    with (a.output/'daemon-stdout.log').open('w') as dout, (a.output/'daemon-stderr.log').open('w') as derr, \
         (a.output/'consumer-stdout.log').open('w') as cout, (a.output/'consumer-stderr.log').open('w') as cerr:
        daemon = start([str(a.daemon)], dout, derr)
        deadline = time.monotonic()+15
        while True:
            assert daemon.poll() is None, 'Frozen daemon exited before readiness'
            ping = subprocess.run([str(a.gdbus),'call','--session','--dest','org.kde.kglobalaccel',
                '--object-path','/kglobalaccel','--method','org.freedesktop.DBus.Peer.Ping'],
                capture_output=True, timeout=2)
            (a.output/'last-readiness.log').write_bytes(ping.stdout+ping.stderr)
            if ping.returncode == 0:
                break
            assert time.monotonic()<deadline, 'Frozen daemon readiness deadline'
            time.sleep(0.1)
        consumer = start([str(a.consumer)], cout, cerr)
        code = consumer.wait(timeout=30)
        result['consumer_exit_code'] = code
        assert code == 0, 'Frozen consumer assertions failed'
        assert daemon.poll() is None, 'Frozen daemon died during consumer execution'
        result['state'] = 'PASS'
except Exception as error:
    result.update(state='FAIL', error=str(error))
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
    result['owned_children_reaped'] = all(p.poll() is not None for p in processes)
    (a.output/'result.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
raise SystemExit(0 if result['state']=='PASS' and result['owned_children_reaped'] else 1)
