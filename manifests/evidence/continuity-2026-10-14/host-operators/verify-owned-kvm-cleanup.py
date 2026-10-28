"""Read-only cleanup audit for a completed gate; never remove shared resources."""
import argparse
import datetime
import json
import subprocess
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument('host_dir', type=Path)
parser.add_argument('output', type=Path)
args = parser.parse_args()
host = json.loads((args.host_dir/'host-result.json').read_text())
environment = {}
for line in (args.host_dir/'host-environment.txt').read_text().splitlines():
    if '=' in line:
        key, value = line.split('=', 1)
        if key not in environment:
            environment[key] = value
assert environment['repository'] == 'SupraLINUX/SupraLINUX'
assert environment['runner_organization'] == 'SupraLINUX'
vm = environment['vm_name']
assert vm.startswith('supralinux-') and '/' not in vm
assert args.host_dir.name == vm
runner_id = int(environment['runner_id']) if environment.get('runner_id') else None
domains = subprocess.check_output(['virsh', '--connect', environment['libvirt_uri'],
                                  'list', '--all', '--name'], text=True).splitlines()
assert vm not in domains, 'Owned VM remains registered'
query = f'.runners[] | select(.id == {runner_id if runner_id is not None else 'null'} or .name == "{vm}") | .id'
runners = subprocess.check_output(['gh', 'api', '--paginate',
                                  'orgs/SupraLINUX/actions/runners', '--jq', query], text=True)
assert not runners.strip(), 'Owned runner remains registered'
overlay = Path('/var/lib/supralinux/ephemeral-runners')/vm
assert not overlay.exists(), 'Owned writable overlay remains'
golden = Path(environment['golden_image'])
backing = Path(environment['execution_backing_image'])
assert golden.is_file() and backing.is_file(), 'Preserved images are missing'
audit = {
    'schema': 1, 'scope': 'direct post-gate cleanup verification',
    'checked_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'vm_name': vm, 'vm_absent': True,
    'runner_id': runner_id, 'runner_absent': True,
    'overlay_directory': str(overlay), 'overlay_absent': True,
    'golden_image_preserved': True, 'execution_backing_image_preserved': True,
    'workflow_run_id': int(host['workflow_run_id']) if host.get('workflow_run_id') else None,
    'source_commit': environment['pr_head_sha'], 'host_evidence_dir': str(args.host_dir),
}
assert not args.output.exists(), 'Refusing to replace an existing audit'
args.output.write_text(json.dumps(audit, indent=2)+'\n')
print(f'Cleanup verified: VM, runner {runner_id} and overlay absent; images preserved')
