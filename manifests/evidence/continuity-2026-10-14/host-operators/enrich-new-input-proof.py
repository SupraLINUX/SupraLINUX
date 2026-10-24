"""Add direct cleanup and source-run evidence before a new proof is published."""
import argparse,hashlib,json,shutil,subprocess,zipfile
from pathlib import Path
p=argparse.ArgumentParser();p.add_argument('proof',type=Path);p.add_argument('--cleanup',type=Path,required=True);p.add_argument('--workflow-run',type=Path);p.add_argument('--health',type=Path);p.add_argument('--host-retention',type=Path);a=p.parse_args()
root=Path.cwd();proof=json.loads(a.proof.read_text());directory=a.proof.parent
assert not subprocess.check_output(['git','ls-files','--',str(a.proof)],text=True).strip(),'Published historical proof is immutable'
campaign_path=root/'manifests/kde-plasma-package-build.json';campaign=json.loads(campaign_path.read_text());old_hash=hashlib.sha256(a.proof.read_bytes()).hexdigest()
link=next(x for key in ['package_input_certifications','package_input_incidents'] for x in campaign.get(key,[]) if x['path']==str(a.proof));assert link['sha256']==old_hash
host=Path(proof['host_evidence_dir']);run_path=a.workflow_run or host/'workflow-run.json';run=json.loads(run_path.read_text());cleanup=json.loads(a.cleanup.read_text())
transport_failure=proof.get('infrastructure_transport_result')=='FAIL'
cancelled_transport=json.loads((directory/'artifact-meta.json').read_text()).get('kind')=='sealed-host-preflight-cancelled-result-export'
assert run['head_sha']==proof['source_commit']==cleanup['source_commit'] and run['id']==proof['workflow_run_id']==cleanup['workflow_run_id'] and run['conclusion']==('cancelled' if cancelled_transport else ('failure' if transport_failure else ('success' if proof['state']=='PASS' else 'failure')))
assert all(cleanup[k] is True for k in ['vm_absent','runner_absent','overlay_absent','golden_image_preserved','execution_backing_image_preserved'])
assert hashlib.sha256((host/'evidence-sha256.txt').read_bytes()).hexdigest()==proof['host_evidence_manifest_sha256']
for source,name in [(run_path,'host-workflow-run.json'),(a.cleanup,'cleanup.json')]:
 target=directory/name;assert not target.exists();shutil.copyfile(source,target)
if a.health:
 events=[json.loads(line) for line in a.health.read_text().splitlines()]
 assert events and all(x['journal_exit_code'] in (0,1) and not x['hardware_hang_seen'] and x['eno1_carrier']=='1' for x in events)
 shutil.copyfile(a.health,directory/'host-health.jsonl')
 proof['host_health_observation']={'samples':len(events),'hardware_hang_observed':False,'physical_carrier_retained':True,'scope':'read-only periodic observations during this owned gate'}
 for name in ['network-guest-safety.json','network-guest-connectivity.json','network-live-domain.xml','network-live-domain-enabled.xml']:
  source=host/name;assert source.is_file();shutil.copyfile(source,directory/name)
if a.host_retention:
 index=json.loads(a.host_retention.read_text());assert index['state']=='PASS' and index['empty_offline_byte_restore_verified'] and not index['requires_github_for_restore']
 retained=root/index['archive_path'];assert hashlib.file_digest(retained.open('rb'),'sha256').hexdigest()==index['archive_sha256']
 for source in host.rglob('*'):
  if source.is_file():assert index['files']['external/'+str(source).removeprefix('/')]['sha256']==hashlib.sha256(source.read_bytes()).hexdigest()
 shutil.copyfile(a.host_retention,directory/'complete-host-retention-index.json')
 proof['complete_host_archive_sha256']=index['archive_sha256']
archive=root/proof['archive_path'];assert hashlib.file_digest(archive.open('rb'),'sha256').hexdigest()==proof['artifact_sha256']
with zipfile.ZipFile(archive) as z:
 assert z.testzip() is None
 name='ubuntu-baseline-preflight/autopkgtest/reviewed-baseline-stdout'
 if name in z.namelist():
  (directory/'reviewed-baseline-stdout').write_bytes(z.read(name))
 else:
  assert proof['state']=='INFRA_INVALID', 'A PASS requires the baseline marker'
 for name in ['cache-probe/sbuild.log','ubuntu-baseline-preflight/autopkgtest/log']:
  if name in z.namelist():
   target=directory/name;assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(name))
proof['files_sha256']={str(f.relative_to(directory)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(directory.rglob('*')) if f.is_file() and f!=a.proof}
a.proof.write_text(json.dumps(proof,indent=2)+'\n');link['sha256']=hashlib.sha256(a.proof.read_bytes()).hexdigest();campaign_path.write_text(json.dumps(campaign,indent=2)+'\n')
print('New unpublished input proof: original run/HEAD, ZIP CRC and direct VM/runner/overlay cleanup verified; images preserved')
