#!/usr/bin/env python3
"""Read-only direct cleanup audit of one owned offline diagnostic domain."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path

p=argparse.ArgumentParser(description=__doc__)
p.add_argument('execution',type=Path)
a=p.parse_args()
root=Path.cwd().resolve()
assert a.execution.resolve().is_relative_to(root/'.work')
h=json.loads((a.execution/'host-result.json').read_text())
env=json.loads((a.execution/'host-environment.json').read_text())
name=h['vm_name']
assert name.startswith('supralinux-offline-diagnostic-')
def virsh(*args):
    return subprocess.run(['virsh','--connect','qemu:///system',*args],capture_output=True,text=True,timeout=20)
assert virsh('domuuid',name).returncode!=0
state=Path(env['state_dir'])
assert state.parent==Path('/var/lib/supralinux/ephemeral-runners') and state.name==name and not state.exists()
net=virsh('net-list','--all','--name')
assert net.returncode==0
before=json.loads((a.execution/'networks-before.json').read_text())
after=[v for v in net.stdout.splitlines() if v]
assert before==after==[]
running=virsh('list','--name')
assert running.returncode==0
owned=[v for v in running.stdout.splitlines() if v.startswith('supralinux-')]
assert not owned and Path(h['golden_image']).exists() and h['github_runner_created'] is False
with (a.execution/'payload.iso').open('rb') as stream:
    digest=hashlib.file_digest(stream,'sha256').hexdigest()
assert digest==h['payload_iso_sha256']
audit={'state':'PASS','vm_name':name,'vm_uuid':h['vm_uuid'],'direct_domain_absent':True,
       'direct_state_dir_and_overlay_absent':True,'no_github_runner_created':True,
       'libvirt_networks_before_after':after,'other_project_running_vms':owned,
       'golden_preserved':True,'exact_payload_iso_sha256':digest}
target=a.execution/'direct-cleanup.json'
assert not target.exists()
target.write_text(json.dumps(audit,indent=2)+'\n')
print('Direct owned domain/overlay cleanup and exact retained ISO digest PASS; networks []')
