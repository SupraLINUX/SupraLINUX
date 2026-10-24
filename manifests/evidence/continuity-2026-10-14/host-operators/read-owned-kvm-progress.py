"""Read bounded progress counters from one exact owned gate without exposing argv."""
import argparse, base64, datetime, hashlib, json, subprocess, time
from pathlib import Path

p = argparse.ArgumentParser(); p.add_argument('host_dir', type=Path); p.add_argument('--output', type=Path, required=True); a = p.parse_args()
env = {}
for line in (a.host_dir/'host-environment.txt').read_text().splitlines():
    if '=' in line:
        k, v = line.split('=', 1); env.setdefault(k, v)
assert env['repository'] == 'SupraLINUX/SupraLINUX' and env['vm_name'] == a.host_dir.name and a.host_dir.name.startswith('supralinux-')
assert not (a.host_dir/'host-result.json').exists() and a.output.is_relative_to(Path('.work'))
code = 'EXPECTED_SOURCE='+repr(env['pr_head_sha'])+'\n'+r'''import collections,json,os,re,subprocess
from pathlib import Path
assert os.geteuid()==0 and subprocess.check_output(['systemd-detect-virt','--vm'],text=True).strip()=='kvm'
checkout=Path('/opt/actions-runner/_work/SupraLINUX/SupraLINUX')
assert subprocess.check_output(['git','-c','safe.directory='+str(checkout),'-C',str(checkout),'rev-parse','HEAD'],text=True).strip()==EXPECTED_SOURCE
root=checkout/'evidence/authoritative-plasma-package'; sizes={}; results={}
names=['build-contract.json','predecessor-inputs.json','signature.log','source-package.log','rootfs-admission.json','rootfs-sha256.txt','cache-probe/sbuild.log','cache-probe/result.json','ubuntu-baseline-preflight/result.json','ubuntu-baseline-preflight/autopkgtest/log','reviewed-baseline-stdout','sbuild.log','upstream-tests.json','lintian.log','autopkgtest.log','autopkgtest/log','autopkgtest/summary','result.json']
for name in names:
    path=root/name
    if path.is_file():
        sizes[name]=path.stat().st_size
        if name.endswith('result.json'):
            d=json.loads(path.read_text());results[name]={k:d[k] for k in ['state','stage','exit_code','package_attempt_consumed'] if k in d}
candidate_observation={}
candidate_log=root/'sbuild.log'
if candidate_log.is_file():
    raw=candidate_log.read_text(errors='replace')
    candidate_observation['sbuild_log_bytes']=candidate_log.stat().st_size
    candidate_observation['native_ctest_pass_lines']=len(re.findall(r'^\s*\d+/\d+ Test #\d+:.*?\bPassed\b',raw,re.M))
    candidate_observation['native_ctest_fail_lines']=len(re.findall(r'^\s*\d+/\d+ Test #\d+:.*?\*\*\*Failed\b',raw,re.M))
    complete=re.findall(r'100% tests passed, 0 tests failed out of (\d+)\b',raw)
    candidate_observation['ctest_all_pass_summary_seen']=bool(complete)
    candidate_observation['ctest_all_pass_summary_test_counts']=[int(value) for value in complete]
    candidate_observation['appstream_preinstall_skip_seen']='Not installed yet, skipping' in raw
    candidate_observation['native_qt_totals']=[dict(zip(['passed','failed','skipped','blacklisted'],map(int,values))) for values in re.findall(r'Totals: (\d+) passed, (\d+) failed, (\d+) skipped, (\d+) blacklisted',raw)]
    candidate_observation['package_build_finished_marker_seen']=bool(re.search(r'^Build finished at ',raw,re.M))
    candidate_observation['cmake_generation_done']=('-- Build files have been written to:' in raw)
    ninja=re.findall(r'^\[(\d+)/(\d+)\] ',raw,re.M)
    if ninja:candidate_observation['latest_ninja_progress']={'completed':int(ninja[-1][0]),'total':int(ninja[-1][1])}
test_summary=root/'autopkgtest/summary'
if test_summary.is_file():
    candidate_observation['installed_test_summary_lines']=test_summary.read_text(errors='replace').splitlines()[:12]
live_baseline=checkout/'evidence/runner-contract/reviewed-ubuntu-baseline'
baseline_observation={}
for name in ['pipeline.log','autopkgtest/log','autopkgtest/summary','result.json']:
    path=live_baseline/name
    if path.is_file():baseline_observation[name+'_bytes']=path.stat().st_size
log=live_baseline/'pipeline.log'
if log.is_file():
    raw=log.read_text(errors='replace')
    downloads=re.findall(r'^Get:([0-9]+) https?://[^\s]+ [^\n]*? ([a-z0-9][a-z0-9+.-]+) (?:amd64|all) ([^\s]+) \[([^]\n]+)\]',raw,re.M)
    baseline_observation['apt_download_lines']=len(downloads)
    if downloads:
        d=downloads[-1];baseline_observation['latest_download']={'number':int(d[0]),'package':d[1],'version':d[2],'announced_size':d[3]}
    baseline_observation['apt_unpacked_lines']=len(re.findall(r'^Unpacking ',raw,re.M))
    baseline_observation['apt_configured_lines']=len(re.findall(r'^Setting up ',raw,re.M))
    baseline_observation['functional_pass_marker_seen']='Reviewed Ubuntu baseline client completed before candidate installation: PASS' in raw
processes=collections.Counter(); archive_count=0; archive_bytes=0; roots=set()
for proc in Path('/proc').glob('[0-9]*'):
    try:
        comm=(proc/'comm').read_text().strip()
        if comm in ['apt-get','https','sbuild','autopkgtest','qemu-system-x86','cmake','ninja','make','cc1plus','c++','ld']:processes[comm]+=1
        if comm=='apt-get':
            rootpath=proc/'root';identity=rootpath.stat().st_ino
            if identity in roots:continue
            roots.add(identity)
            for file in (rootpath/'var/cache/apt/archives').glob('*.deb'):
                archive_count+=1;archive_bytes+=file.stat().st_size
    except (FileNotFoundError,ProcessLookupError,PermissionError):pass
net={name:int((Path('/sys/class/net/ens2/statistics')/name).read_text()) for name in ['rx_bytes','tx_bytes']}
print(json.dumps({'source_commit':EXPECTED_SOURCE,'file_sizes':sizes,'completed_results':results,'live_original_baseline_observation':baseline_observation,'candidate_observation':candidate_observation,'process_counts':dict(processes),'active_apt_completed_archives':archive_count,'active_apt_completed_archive_bytes':archive_bytes,'guest_network_counters':net,'scope':'read-only counters; no argv, tokens or package-state mutations'}))
'''
payload={'execute':'guest-exec','arguments':{'path':'/usr/bin/python3','arg':['-c',code],'capture-output':True}}
r=json.loads(subprocess.check_output(['virsh','--connect',env['libvirt_uri'],'qemu-agent-command',env['vm_name'],json.dumps(payload)],text=True,timeout=15))['return']
for _ in range(20):
    q=json.loads(subprocess.check_output(['virsh','--connect',env['libvirt_uri'],'qemu-agent-command',env['vm_name'],json.dumps({'execute':'guest-exec-status','arguments':{'pid':r['pid']}})],text=True,timeout=15))['return']
    if q.get('exited'):break
    time.sleep(0.5)
assert q.get('exited') and q.get('exitcode')==0 and not q.get('out-truncated')
d=json.loads(base64.b64decode(q['out-data'],validate=True));d['observed_at']=datetime.datetime.now(datetime.timezone.utc).isoformat();d['operator_source_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
with a.output.open('a') as f:f.write(json.dumps(d)+'\n')
print(json.dumps(d))
