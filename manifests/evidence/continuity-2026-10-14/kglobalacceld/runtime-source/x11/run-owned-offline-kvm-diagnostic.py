#!/usr/bin/env python3
"""Run a local diagnostic payload in an owned disposable KVM without a NIC."""
import argparse
import base64
import datetime
import fcntl
import grp
import hashlib
import json
import os
import re
import shutil
import signal
import subprocess
import time
import uuid
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STATE = Path('/var/lib/supralinux/ephemeral-runners')
URI = 'qemu:///system'
GOLDEN = Path('/var/lib/supralinux/images/ubuntu-26.04-authoritative.qcow2')
GOLDEN_SHA = 'a0b88447d9a9ecd9785087390cf499abaf9416291864fe1be4d63d9a334b2acd'
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--payload', type=Path, required=True)
parser.add_argument('--entry', required=True)
parser.add_argument('--output', type=Path, required=True)
parser.add_argument('--memory-mib', type=int, default=4096)
parser.add_argument('--vcpus', type=int, default=2)
parser.add_argument('--timeout-seconds', type=int, default=900)
args = parser.parse_args()
payload, evidence = args.payload.resolve(), args.output.resolve()
assert payload.is_dir() and payload.is_relative_to(ROOT/'.work')
entry = Path(args.entry)
assert not entry.is_absolute() and '..' not in entry.parts
assert (payload/entry).is_file() and not (payload/entry).is_symlink()
assert evidence.is_relative_to(ROOT/'.work') and not evidence.exists()
assert 1024 <= args.memory_mib <= 8192 and 1 <= args.vcpus <= 4
assert 60 <= args.timeout_seconds <= 1800
evidence.mkdir(parents=True)
identifier = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ').lower()+'-'+str(os.getpid())
name = 'supralinux-offline-diagnostic-'+identifier
identity = str(uuid.uuid4())
work = STATE/name
overlay, iso = work/'work.qcow2', work/'payload.iso'
defined = False
status = {'schema': 1, 'scope': 'Private offline KVM diagnostic, not package build or transition admission',
          'vm_name': name, 'vm_uuid': identity, 'guest_entry': str(entry),
          'package_attempt_consumed': False, 'canonical_effect': 'none',
          'network_interfaces_requested': 0, 'github_runner_created': False}
start = datetime.datetime.now(datetime.timezone.utc).isoformat()

def save(filename, value):
    (evidence/filename).write_text(json.dumps(value, indent=2)+'\n')

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def command(argv, timeout=60, checked=True, filename=None):
    p = subprocess.Popen(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         start_new_session=True, text=True)
    try:
        stdout, stderr = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGTERM)
        try:
            stdout, stderr = p.communicate(timeout=10)
        except subprocess.TimeoutExpired:
            os.killpg(p.pid, signal.SIGKILL)
            stdout, stderr = p.communicate(timeout=10)
        if filename:
            (evidence/filename).write_text(stdout+stderr)
        raise RuntimeError('Owned command deadline: '+argv[0])
    if filename:
        (evidence/filename).write_text(stdout+stderr)
    if checked and p.returncode:
        raise RuntimeError(f'Command {argv[0]} failed ({p.returncode}): {stderr[-1500:]}')
    return p.returncode, stdout, stderr

def virsh(*argv, **options):
    return command(['virsh', '--connect', URI, *argv], **options)

def qga(value):
    _, out, _ = virsh('qemu-agent-command', name, json.dumps(value), timeout=20)
    result = json.loads(out)
    assert 'error' not in result, result
    return result['return']

def own_domain():
    rc, out, _ = virsh('domuuid', name, checked=False)
    if rc:
        return False
    assert out.strip() == identity, 'Refusing operation on a domain with another UUID'
    return True

def host_health():
    _, features, _ = command(['ethtool', '-k', 'eno1'])
    health = {'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'carrier': Path('/sys/class/net/eno1/carrier').read_text().strip()}
    for feature, label in [('tcp-segmentation-offload','tso'), ('generic-segmentation-offload','gso')]:
        health[label] = next(line.split(':',1)[1].strip() for line in features.splitlines() if line.startswith(feature+':'))
    rc, out, err = command(['journalctl','-k','--since',start,'--no-pager','-o','cat'], checked=False)
    health['kernel_journal_read_exit_code'] = rc
    health['hardware_hang_observed'] = bool(re.search(r'Hardware Unit Hang',out,re.I)) if rc == 0 else None
    with (evidence/'host-health.jsonl').open('a') as log:
        log.write(json.dumps(health)+'\n')
    assert rc == 0, 'Kernel journal unavailable; no healthy claim'
    assert health['carrier']=='1' and health['tso']=='off' and health['gso']=='off'
    assert not health['hardware_hang_observed'], 'Observed host hardware hang; stop own VM'

def signal_stop(signum, frame):
    raise RuntimeError('Diagnostic interrupted by signal '+str(signum))

signal.signal(signal.SIGTERM, signal_stop)
signal.signal(signal.SIGINT, signal_stop)
lock = (STATE/'.locks/SupraLINUX-SupraLINUX-authoritative.lock').open('a')
fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
try:
    print('Verifying unchanged golden image and offline payload', flush=True)
    assert sha(GOLDEN) == GOLDEN_SHA
    assert f'golden_image_sha256={GOLDEN_SHA}' in Path(str(GOLDEN)+'.provenance.txt').read_text()
    assert 'source_checkout_removed=yes' in Path(str(GOLDEN)+'.provenance.txt').read_text()
    assert os.access('/dev/kvm', os.R_OK | os.W_OK)
    domains = virsh('list','--all','--name')[1].splitlines()
    assert name not in domains and not work.exists()
    networks_before = virsh('net-list','--all','--name')[1].splitlines()
    save('networks-before.json', [v for v in networks_before if v])
    host_health()
    inventory = {}
    for p in sorted(payload.rglob('*')):
        if p.is_symlink():
            target = p.resolve()
            assert target.is_relative_to(payload) and target.exists(), 'Payload symlink escapes its input tree'
        elif p.is_file():
            inventory[str(p.relative_to(payload))] = {'sha256': sha(p), 'size': p.stat().st_size}
    save('payload-index.json', inventory)
    group = grp.getgrnam('libvirt-qemu').gr_gid
    assert group in os.getgroups()
    work.mkdir(mode=0o710)
    os.chown(work, -1, group)
    command(['qemu-img','create','-f','qcow2','-F','qcow2','-b',str(GOLDEN),str(overlay)], filename='overlay-create.log')
    os.chown(overlay, -1, group)
    overlay.chmod(0o660)
    command(['genisoimage','-quiet','-R','-iso-level','3','-V','SUPRADIAG','-o',str(iso),str(payload)], timeout=600, filename='iso-create.log')
    os.chown(iso, -1, group)
    iso.chmod(0o640)
    status.update(golden_image=str(GOLDEN), golden_image_sha256=GOLDEN_SHA, payload_iso_sha256=sha(iso))
    shutil.copyfile(iso, evidence/'payload.iso')
    assert sha(evidence/'payload.iso') == status['payload_iso_sha256']
    status['exact_payload_iso_retained'] = True
    argv = ['virt-install','--connect',URI,'--name',name,'--uuid',identity,
            '--memory',str(args.memory_mib),'--vcpus',str(args.vcpus),'--cpu','host-passthrough',
            '--qemu-commandline=-global host-x86_64-cpu.kvm-asyncpf=off -global host-x86_64-cpu.kvm-asyncpf-int=off',
            '--import','--disk',f'path={overlay},format=qcow2,bus=virtio,cache=none',
            '--disk',f'path={iso},format=raw,device=cdrom,readonly=on','--network','none',
            '--channel','unix,target.type=virtio,target.name=org.qemu.guest_agent.0',
            '--graphics','none','--noautoconsole','--osinfo','detect=on,require=off','--print-xml']
    xml = command(argv, timeout=120)[1]
    tree = ET.fromstring(xml)
    assert tree.attrib['type']=='kvm' and tree.findtext('name')==name and tree.findtext('uuid')==identity
    assert not tree.findall('./devices/interface') and not tree.findall('./devices/hostdev')
    assert not tree.findall('./devices/filesystem') and not tree.findall('./devices/graphics')
    disks = tree.findall('./devices/disk')
    assert len(disks)==2
    assert {d.find('source').attrib['file'] for d in disks} == {str(overlay),str(iso)}
    assert next(d for d in disks if d.find('source').attrib['file']==str(iso)).find('readonly') is not None
    (evidence/'reviewed-domain.xml').write_text(xml)
    save('host-environment.json',status | {'state_dir':str(work), 'libvirt_uri':URI})
    defined = True
    virsh('define',str(evidence/'reviewed-domain.xml'),filename='define.log')
    assert own_domain()
    print('Booting owned KVM; domain XML contains no NIC, host device or shared directory', flush=True)
    virsh('start',name,filename='start.log')
    _, active_xml, _ = virsh('dumpxml',name)
    (evidence/'live-domain.xml').write_text(active_xml)
    assert not ET.fromstring(active_xml).findall('./devices/interface')
    kvm=json.loads(virsh('qemu-monitor-command',name,'{"execute":"query-kvm"}')[1])['return']
    assert kvm['enabled'] and kvm['present']
    save('actual-kvm.json',kvm)
    ready = time.monotonic()+180
    while True:
        try:
            qga({'execute':'guest-ping'})
            break
        except (RuntimeError,AssertionError):
            assert time.monotonic()<ready,'Guest agent did not become ready'
            host_health()
            time.sleep(5)
    code = '''import pathlib,subprocess,sys
assert [p.name for p in pathlib.Path('/sys/class/net').iterdir()]==['lo']
mount=pathlib.Path('/mnt/supradiag'); mount.mkdir(exist_ok=True)
subprocess.run(['mount','-o','ro,nosuid,nodev','/dev/sr0',str(mount)],check=True)
out=pathlib.Path('/var/tmp/supra-offline-diagnostic');out.mkdir(exist_ok=False)
r=subprocess.run(['/usr/bin/python3',str(mount/%r),str(out)],timeout=%d)
sys.exit(r.returncode)
''' % (str(entry), args.timeout_seconds)
    print('Executing reviewed diagnostic payload over the local QEMU guest-agent channel', flush=True)
    pid=qga({'execute':'guest-exec','arguments':{'path':'/usr/bin/python3','arg':['-c',code],'capture-output':True}})['pid']
    deadline=time.monotonic()+args.timeout_seconds+30
    while True:
        guest=qga({'execute':'guest-exec-status','arguments':{'pid':pid}})
        if guest.get('exited'):
            break
        assert time.monotonic()<deadline,'Guest diagnostic deadline exceeded'
        host_health()
        time.sleep(10)
    save('guest-exec-result.json',guest)
    for field,filename in [('out-data','guest-stdout.log'),('err-data','guest-stderr.log')]:
        (evidence/filename).write_bytes(base64.b64decode(guest.get(field,'')))
    status['diagnostic_exit_code']=guest.get('exitcode')
    print('Diagnostic completed; stopping owned VM and exporting all result files', flush=True)
    virsh('shutdown',name,checked=False,filename='shutdown.log')
    until=time.monotonic()+60
    while virsh('domstate',name)[1].strip()!='shut off':
        if time.monotonic()>=until:
            virsh('destroy',name,filename='stop-after-deadline.log')
            break
        time.sleep(5)
    command([str(ROOT/'scripts/with-libguestfs-runtime.sh'),'virt-copy-out','-a',str(overlay),
             '/var/tmp/supra-offline-diagnostic',str(evidence)],timeout=600,filename='export.log')
    status['guest_results_exported']=True
    status['state']='PASS' if guest.get('exitcode')==0 else 'DIAGNOSTIC_FAIL'
    host_health()
except Exception as error:
    status.update(state='INFRA_INVALID',error=str(error))
    print('Offline diagnostic stopped: '+str(error),flush=True)
finally:
    # Clean only this UUID; preservation wins over deleting an uncertain disk.
    cleaned=False
    try:
        if defined and own_domain():
            virsh('dumpxml',name,checked=False,filename='final-domain.xml')
            if virsh('domstate',name)[1].strip()!='shut off':
                virsh('destroy',name,filename='cleanup-stop.log')
            virsh('undefine',name,filename='cleanup-undefine.log')
        assert not own_domain(),'Owned VM still registered; overlay preserved'
        if work.exists():
            assert work.parent==STATE and work.name==name and not work.is_symlink()
            shutil.rmtree(work)
        assert not work.exists() and GOLDEN.is_file()
        cleaned=True
    except Exception as error:
        status['cleanup_error']=str(error)
    networks_after = [v for v in virsh('net-list','--all','--name')[1].splitlines() if v]
    save('networks-after.json',networks_after)
    status.update(cleanup_verified=cleaned,vm_absent=cleaned,overlay_absent=cleaned,
                  golden_preserved=GOLDEN.is_file(),finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
    save('host-result.json',status)
    print(json.dumps(status),flush=True)
    lock.close()
raise SystemExit(0 if status.get('state')=='PASS' and status.get('cleanup_verified') else 1)
