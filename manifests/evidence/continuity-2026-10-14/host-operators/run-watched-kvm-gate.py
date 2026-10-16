"""Run one authorized KVM gate with read-only host hang monitoring."""
import argparse, datetime, json, os, select, signal, subprocess, time
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('gate');p.add_argument('--startup',action='store_true');p.add_argument('--log',type=Path,required=True);p.add_argument('--health',type=Path,required=True)
a=p.parse_args();assert not a.log.exists() and not a.health.exists()
env=os.environ.copy();env['SUPRALINUX_GITHUB_TOKEN']=subprocess.check_output(['gh','auth','token'],text=True).strip();env['SUPRALINUX_RUNNER_GROUP_ID']='3'
if a.startup:env.update(SUPRALINUX_JIT_STARTUP_PREFLIGHT='1',SUPRALINUX_VM_MEMORY_MIB='2048',SUPRALINUX_VM_VCPUS='2')
start=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')
process=subprocess.Popen(['scripts/run-kvm-jit-gate.sh',a.gate],env=env,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
next_check=0;incident=False
with a.log.open('wb') as log,a.health.open('w') as health:
 while process.poll() is None:
  if time.monotonic()>=next_check:
   command=['journalctl','-k','-b','--since',start,'--no-pager','-o','cat','-g','Hardware Unit Hang|NETDEV WATCHDOG']
   try:
    result=subprocess.run(command,capture_output=True,text=True,timeout=10)
    carrier=Path('/sys/class/net/eno1/carrier').read_text().strip()
   except Exception as error:
    result=subprocess.CompletedProcess(command,2,'',type(error).__name__)
    carrier='unknown'
   event={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'journal_exit_code':result.returncode,'hardware_hang_seen':'Hardware Unit Hang' in result.stdout or 'NETDEV WATCHDOG' in result.stdout,'eno1_carrier':carrier}
   health.write(json.dumps(event)+'\n');health.flush()
   if not incident and (result.returncode not in (0,1) or event['hardware_hang_seen'] or carrier!='1'):
    incident=True
    # The core wrapper execs the shell with the same PID; only its unique owned VM may be stopped.
    owned=list(Path('/var/lib/supralinux/evidence/host-kvm').glob('supralinux-*-'+str(process.pid)))
    assert len(owned)<=1
    if owned:
     subprocess.run(['virsh','--connect','qemu:///system','destroy',owned[0].name],capture_output=True,text=True,timeout=15)
    process.send_signal(signal.SIGTERM)
    print('Host network health incident: owned gate stopped for cleanup',flush=True)
   next_check=time.monotonic()+10
  ready,_,_=select.select([process.stdout],[],[],1)
  if ready:
   data=os.read(process.stdout.fileno(),65536)
   log.write(data);log.flush();print(data.decode(errors='replace'),end='',flush=True)
 data=process.stdout.read();log.write(data);print(data.decode(errors='replace'),end='',flush=True)
rc=process.wait();print('WATCHED_KVM_GATE_EXIT_CODE='+str(rc),flush=True)
raise SystemExit(rc or int(incident))
