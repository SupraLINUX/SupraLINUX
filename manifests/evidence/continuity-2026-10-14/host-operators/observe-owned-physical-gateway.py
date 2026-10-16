"""Observe the existing host gateway during one owned gate; never change networking."""
import argparse, datetime, json, os, signal, subprocess, time
from pathlib import Path

def stop_owned_gate(env, proc_root=Path('/proc')):
 assert env['repository']=='SupraLINUX/SupraLINUX' and env['vm_name'].startswith('supralinux-')
 core_pid=int(env['vm_name'].rsplit('-',1)[1])
 command=(proc_root/str(core_pid)/'cmdline').read_bytes().split(b'\0')
 assert any(Path(arg.decode()).name=='run-kvm-jit-gate-core.sh' for arg in command if arg), 'Owned gate process identity unavailable'
 stopped=subprocess.run(['virsh','--connect',env['libvirt_uri'],'destroy',env['vm_name']],capture_output=True,timeout=15)
 assert stopped.returncode==0, 'Owned VM could not be stopped after gateway loss'
 os.kill(core_pid,signal.SIGTERM)

p=argparse.ArgumentParser();p.add_argument('host_dir',type=Path);p.add_argument('--output',type=Path,required=True);p.add_argument('--timeout-seconds',type=int,default=8400);a=p.parse_args()
env={}
for line in (a.host_dir/'host-environment.txt').read_text().splitlines():
 if '=' in line:
  key,value=line.split('=',1);env.setdefault(key,value)
assert env['repository']=='SupraLINUX/SupraLINUX' and env['vm_name']==a.host_dir.name and a.host_dir.name.startswith('supralinux-')
assert a.output.is_relative_to(Path('.work')) and not a.output.exists()
routes=json.loads(subprocess.check_output(['ip','-j','route','show','default'],text=True))
gateways={r['gateway'] for r in routes if r.get('dev')=='eno1' and r.get('gateway')}
assert len(gateways)==1, 'Expected one existing physical gateway'
assert 60<=a.timeout_seconds<=24000
deadline=time.monotonic()+a.timeout_seconds; failures=0;samples=0
print('Read-only physical gateway observer active; one small ping per 30 seconds',flush=True)
with a.output.open('w') as f:
 while not (a.host_dir/'host-result.json').exists() and time.monotonic()<deadline:
  try:
   result=subprocess.run(['ping','-n','-c','1','-W','2',next(iter(gateways))],capture_output=True,timeout=5)
   code=result.returncode
  except subprocess.TimeoutExpired:code=124
  failures=failures+1 if code else 0;samples+=1
  event={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'host existing physical default gateway reachability; guest never enters LAN','ping_exit_code':code,'consecutive_failures':failures,'carrier':Path('/sys/class/net/eno1/carrier').read_text().strip(),'host_network_modified':False}
  f.write(json.dumps(event)+'\n');f.flush()
  if failures:print('Physical gateway observation: ping failed; consecutive='+str(failures),flush=True)
  if failures>=3:
   stop_owned_gate(env)
   print('Three physical gateway failures: exact owned VM stopped; gate cleanup signalled',flush=True)
   break
  for _ in range(30):
   if (a.host_dir/'host-result.json').exists():break
   time.sleep(1)
print('Read-only physical gateway observer closed; samples='+str(samples),flush=True)
