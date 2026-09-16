#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
RUN=35047623320
COMMIT='c7a7a6adca9e44d5ff9bdee984d9f40a097290f9'
FINAL='18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED'

KW_FILES={
'libkf6windowsystem_data_deb_sha256':'f6c55bec9b08ccbf002bb52016f080c0804e3161576f01acccd608900a662200',
'libkf6windowsystem_dev_deb_sha256':'d3a7f2fb13af68faf8bf36c048f039ff4aeaa50a90e44c5afb13f53bd7711e5c',
'libkf6windowsystem_doc_deb_sha256':'6c6b080d60946cff5ba7b7762407b5da3dfb275e38e7a7d82fdcd0e1378d78de',
'libkf6windowsystem6_deb_sha256':'fd5245b8b292f94e6dce9be56e0ca721e7b4d007a8a85be9dd98fcbcd4671acc',
'qml6_module_org_kde_kwindowsystem_deb_sha256':'07d4f715ea2783ae3b8daf88b907edf4cb62ae44760d190e8a8ddea908594b01',
'libkf6windowsystem6_dbgsym_ddeb_sha256':'57c83b7263d3235f27a237baa76d2818acdd77c77f2fbdc078647b5148127f2d',
'qml6_module_org_kde_kwindowsystem_dbgsym_ddeb_sha256':'88d07aac93c80c33001669da71d4fa3ba40193d9b292572d19beeb2b08818fc9',
'changes_sha256':'bb8caef7dfd048774e12e552add9a915b91394b96f9046d1dd3c8262dbee6a6e',
'buildinfo_sha256':'f6fdb22a061aaf05e13c9eca2f8f305518c6965bfa91c41774aabd8e7165d87a',
'dsc_sha256':'0b07ad33cd0238a853ef222d2195b8bbd7cc7f0fa22a1d4f46d5c6bf88906f87',
'orig_tar_sha256':'639a501b877446b19905399d27e2be2b6ebb0bb481abe3209dc4d535a12e12ca',
'debian_tar_sha256':'c0048558625428b6daf6e8524276a20d284b8723cee758fa760cf38ac6f578f8',
'rootfs_sha256':'c9b726402226ff31d1117fbf6db2a2d9497debd4efc7cd4d91494fcf6de55215'}
SO_FILES={
'libkf6solid_bin_deb_sha256':'804ba4fcbd8eefb088ba771bed1eeb9317e3662cee91f5724de7581ae13ce9b8',
'libkf6solid_data_deb_sha256':'949d495165f79e1a980476d12fa3573a8748f94e3f86412d679cab9ff2de3aaf',
'libkf6solid_dev_deb_sha256':'dc01cfc7e8158129391580304d56d5bf8f5c685eca2b39e080237d96ae087286',
'libkf6solid_doc_deb_sha256':'684afa8723f89970b2f7b34cc9b53ca67dfedd0194fe9b6173111299bee8ba63',
'libkf6solid6_deb_sha256':'e8f573ce4e6d14e5796908c72d27505b32e1ccd23c806c073ac79333626ba9fe',
'libkf6solid_bin_dbgsym_ddeb_sha256':'7fe44a287c5c4727375d6b07431435111031d7aa0bfb097136a9f160c24dd2ae',
'libkf6solid6_dbgsym_ddeb_sha256':'ab1c956f40fb21cd411b91e847f32c24a1770e1bf4d2025fc59fb9079b9d468a',
'changes_sha256':'41de01ccad5f7365edd0a4ae158c56331f48d21cadd9666aedbdd75e99db7966',
'buildinfo_sha256':'993c920cd61cd4bcdbbb347bc06c778d774794d6c5f249ae82c47c172a0536c8',
'dsc_sha256':'4c299abff676ae86528c1fded9aed0bdc1bd98cfc8284c7c20ca996e80fae588',
'orig_tar_sha256':'bdbfdc9f26b87e12b951097825af2956f2dee3f14c701d780277b69701f2c74e',
'debian_tar_sha256':'f4aec00b52e9c2c3446c9cd61b6f3278ea3c4848f5f6949cc263176cc085235f',
'rootfs_sha256':'1c7e6571a3c5d744a010c8b2750984190f2a4a062884f0682462773e090c9179'}
KW_PASS={'result':'PASS','workflow_run':RUN,'job_id':104640833059,'commit':COMMIT,'attempted_package_version':'6.30.0-0supralinux4','artifact_id':10428130399,'artifact_sha256':'9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272','stage':'complete','tests':'14/14 PASS','lintian':'PASS-errors','consumer_smoke':'PASS','abi_soname':'libKF6WindowSystem.so.6','ecm_predecessor':'6.30.0-0supralinux3','validated_gate':'sbuild-summary-plus-dsc-plus-changes','apt_check':'PASS','consumer_runtime_closure':'PASS','downstream_eligible':True,'files':KW_FILES}
SO_PASS={'result':'PASS','workflow_run':RUN,'job_id':104640833295,'commit':COMMIT,'attempted_package_version':'6.30.0-0supralinux2','artifact_id':10427653865,'artifact_sha256':'cff267d012a3e103b53bd6e19757e6c3b0af7dc873f4cd166a4505f58aee8389','stage':'complete','tests':'5/5 PASS','lintian':'PASS-errors','consumer_smoke':'PASS','abi_soname':'libKF6Solid.so.6','ecm_predecessor':'6.30.0-0supralinux3','validated_gate':'sbuild-summary-plus-dsc-plus-changes','apt_check':'PASS','consumer_runtime_closure':'PASS','downstream_eligible':True,'files':SO_FILES}

def load(p): return json.loads((ROOT/p).read_text())
def save(p,obj): (ROOT/p).write_text(json.dumps(obj,indent=2,ensure_ascii=False)+'\n')
def append_once(path,marker,text,prepend=False):
 p=ROOT/path; old=p.read_text()
 if marker in old: return
 p.write_text((text+'\n\n'+old) if prepend else (old.rstrip()+'\n\n'+text.rstrip()+'\n'))

camp=load('manifests/kde-tier1-package-campaign-batch6.json')
camp['state']='PASS'; camp['canonical_snapshot']={'state':'promoted-at-batch-closure','tier1':FINAL}
crp=camp['shared_packaging_inputs']['consumer_runtime_policy']; crp['status']='validated'; crp['validated_by_run']=RUN; crp['validated_commit']=COMMIT
kw=camp['nodes']['kwindowsystem']; so=camp['nodes']['solid']
if not any(x.get('workflow_run')==RUN and x.get('job_id')==104640833059 for x in kw['evidence']): kw['evidence'].append(KW_PASS)
else:
 for i,x in enumerate(kw['evidence']):
  if x.get('workflow_run')==RUN and x.get('job_id')==104640833059: kw['evidence'][i]=KW_PASS
kw.update(state='PASS',last_result='PASS',downstream_eligible=True,last_pass_files=KW_FILES)
kw['remediation'].update(status='validated',validated_by_run_id=RUN,validated_by_job_id=104640833059,validated_by_artifact_id=10428130399,validated_consumer_runtime_closure='PASS')
if not any(x.get('workflow_run')==RUN and x.get('job_id')==104640833295 for x in so['evidence']): so['evidence'].append(SO_PASS)
else:
 for i,x in enumerate(so['evidence']):
  if x.get('workflow_run')==RUN and x.get('job_id')==104640833295: so['evidence'][i]=SO_PASS
so.update(state='PASS',last_result='PASS',downstream_eligible=True,last_pass_files=SO_FILES)
so['shared_runner_revalidation']={'status':'PASS','trigger':'consumer-runtime-closure-remediation','package_change':False,'package_version':'6.30.0-0supralinux2','retained_pass_workflow_run':35038057329,'retained_pass_artifact_id':10423914110,'revalidation_workflow_run':RUN,'revalidation_job_id':104640833295,'revalidation_artifact_id':10427653865,'revalidation_artifact_sha256':SO_PASS['artifact_sha256'],'reason':'Shared Batch 6 consumer-runtime closure was revalidated without a package change; prior PASS evidence is retained and the exact same package revision passed under the corrected runner.'}
save('manifests/kde-tier1-package-campaign-batch6.json',camp)

tier=load('manifests/kde-frameworks-tier1.json')
byid={n['id']:n for n in tier['nodes']}
for node,cn in [('kwindowsystem',kw),('solid',so)]:
 t=byid[node]; t['packaging']={'state':'PASS','package_version':cn['package_version'],'claim':'hosted-clean-package-preflight','authoritative':False,'downstream_eligible':True,'evidence':cn['evidence']}; t['state']='PASS'
save('manifests/kde-frameworks-tier1.json',tier)

dag=load('manifests/kde-dag.json')
for node,cn,passfiles in [('kwindowsystem',kw,KW_FILES),('solid',so,SO_FILES)]:
 dn={'tier':1,'upstream_version':cn['upstream_version'],'source_url':cn['source_url'],'source_sha256':cn['source_sha256'],'source_evidence':'https://kde.org/info/kde-frameworks-6.30.0/','source_authority':'kde-upstream','package_provider':'supralinux','source_package':cn['source_package'],'binary_packages':[x['name'] for x in cn['binary_contracts']],'package_version':cn['package_version'],'depends_on':['extra-cmake-modules'],'state':'PASS','claim':'hosted-clean-package-preflight','authoritative':False,'downstream_eligible':True,'evidence':cn['evidence'],'pass_files':passfiles,'remediation':cn.get('remediation',{})}
 if node=='solid': dn['shared_runner_revalidation']=cn['shared_runner_revalidation']
 dag['nodes'][node]=dn
save('manifests/kde-dag.json',dag)

validator=r'''#!/usr/bin/env python3
from __future__ import annotations
import json,sys
from pathlib import Path
R=Path(__file__).resolve().parents[1]; errs=[]
def req(v,m):
 if not v: errs.append(m)
def load(p): return json.loads((R/p).read_text())
def txt(p): return (R/p).read_text()
c=load('manifests/kde-tier1-package-campaign-batch6.json'); t=load('manifests/kde-frameworks-tier1.json'); d=load('manifests/kde-dag.json')
tier={x['id']:x for x in t['nodes']}; dag=d['nodes']
req(c.get('state')=='PASS','batch state'); req(c.get('canonical_snapshot')=={'state':'promoted-at-batch-closure','tier1':'18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED'},'canonical closure snapshot')
counts={s:sum(x.get('state')==s for x in t['nodes']) for s in ('PASS','pending','FAIL','BLOCKED')}; req(counts=={'PASS':18,'pending':11,'FAIL':0,'BLOCKED':0},f'Tier1 counts {counts}')
crp=c['shared_packaging_inputs']['consumer_runtime_policy']; req(crp.get('status')=='validated' and crp.get('validated_by_run')==35047623320,'consumer runtime closure'); req(crp.get('install_method')=='apt-get-local-debs' and crp.get('apt_check_required') is True and crp.get('exact_built_versions_required') is True,'consumer runtime policy')
expected={'kwindowsystem':(104640833059,10428130399,'9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272','6.30.0-0supralinux4','14/14 PASS','libKF6WindowSystem.so.6'),'solid':(104640833295,10427653865,'cff267d012a3e103b53bd6e19757e6c3b0af7dc873f4cd166a4505f58aee8389','6.30.0-0supralinux2','5/5 PASS','libKF6Solid.so.6')}
for n,(job,art,digest,ver,tests,soname) in expected.items():
 cn=c['nodes'][n]; req(cn.get('state')=='PASS' and cn.get('last_result')=='PASS' and cn.get('downstream_eligible') is True,f'{n} ledger PASS'); ev=cn['evidence'][-1]; req(ev.get('result')=='PASS' and ev.get('workflow_run')==35047623320 and ev.get('job_id')==job and ev.get('artifact_id')==art and ev.get('artifact_sha256')==digest,f'{n} final evidence'); req(ev.get('attempted_package_version')==ver and ev.get('tests')==tests and ev.get('lintian')=='PASS-errors' and ev.get('consumer_smoke')=='PASS' and ev.get('abi_soname')==soname and ev.get('apt_check')=='PASS' and ev.get('consumer_runtime_closure')=='PASS',f'{n} final gates'); req(tier[n].get('state')=='PASS' and tier[n]['packaging'].get('state')=='PASS' and tier[n]['packaging'].get('package_version')==ver and tier[n]['packaging'].get('downstream_eligible') is True,f'{n} Tier1 promotion'); req(dag.get(n,{}).get('state')=='PASS' and dag[n].get('package_version')==ver and dag[n].get('downstream_eligible') is True,f'{n} DAG promotion')
kw=c['nodes']['kwindowsystem']; req([x.get('result') for x in kw['evidence']]==['FAIL','FAIL','FAIL','FAIL','PASS'],'kwindowsystem retained history'); req([x.get('workflow_run') for x in kw['evidence']]==[35034742520,35038057329,35040999577,35046462679,35047623320],'kwindowsystem run history'); req(kw['evidence'][3].get('tests')=='14/14 CTest suites PASS' and kw['evidence'][3].get('failure_substage')=='runner/external-runtime-closure-not-materialized','kwindowsystem runner FAIL retained'); req(kw.get('last_pass_files',{}).get('rootfs_sha256')=='c9b726402226ff31d1117fbf6db2a2d9497debd4efc7cd4d91494fcf6de55215','kwindowsystem final rootfs')
so=c['nodes']['solid']; req([x.get('result') for x in so['evidence']]==['FAIL','PASS','PASS'],'solid retained history plus revalidation'); req(so.get('shared_runner_revalidation',{}).get('status')=='PASS' and so['shared_runner_revalidation'].get('revalidation_workflow_run')==35047623320,'solid runner revalidation'); req(so.get('last_pass_files',{}).get('rootfs_sha256')=='1c7e6571a3c5d744a010c8b2750984190f2a4a062884f0682462773e090c9179','solid final rootfs')
runner=txt('scripts/run-kde-tier1-package-batch6-preflight.sh'); req('apt-get' in runner and '--no-install-recommends' in runner and 'apt-get check' in runner and 'LD_LIBRARY_PATH' in runner,'runner closure implementation'); scope=txt('scripts/kde-tier1-package-batch6-needed.sh'); req('run-kde-tier1-package-batch6-preflight.sh' in scope,'shared runner affects scope')
for p in ('docs/kde-tier1-package-batch6.md','docs/status/2026-09-15-batch6.md','docs/status/2026-09-15.md','docs/kde-tier1-dependencies.md','docs/kde-dag.md'):
 s=txt(p); req('BATCH6-CANONICAL-CLOSURE' in s and '18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED' in s,f'{p} closure documentation')
if errs:
 for e in errs: print('ERROR:',e,file=sys.stderr)
 raise SystemExit(1)
print('KDE Tier 1 Batch 6 canonical closure: PASS')
print('KWindowSystem and Solid are canonical hosted-preflight PASS/downstream-eligible.')
print('Canonical Tier 1: 18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED')
'''
vp=ROOT/'scripts/validate_kde_tier1_package_batch6.py'; vp.write_text(validator); vp.chmod(0o755)

marker='BATCH6-CANONICAL-CLOSURE'
block='''<!-- BATCH6-CANONICAL-CLOSURE -->\n## Batch 6 canonical closure\n\nKWindowSystem `6.30.0-0supralinux4` and Solid `6.30.0-0supralinux2` are canonical hosted-clean-package-preflight PASS and downstream-eligible. Final evidence is workflow run `35047623320`: KWindowSystem job `104640833059`, artifact `10428130399`, ZIP SHA-256 `9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272`, 14/14 tests PASS; Solid job `104640833295`, artifact `10427653865`, ZIP SHA-256 `cff267d012a3e103b53bd6e19757e6c3b0af7dc873f4cd166a4505f58aee8389`, 5/5 tests PASS. Both pass Lintian error gating, consumer smoke, exact local-package installation and `apt-get check`. The shared consumer-runtime closure remediation is therefore validated. Canonical Tier 1 is **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**. Historical FAIL attempts remain retained as evidence; BLOCKED remains distinct from FAIL.\n'''
append_once('docs/kde-tier1-package-batch6.md',marker,block)
append_once('docs/status/2026-09-15-batch6.md',marker,block)
append_once('docs/kde-tier1-dependencies.md',marker,block)
append_once('docs/kde-dag.md',marker,block)
status_banner='''<!-- BATCH6-CANONICAL-CLOSURE -->\n> Current canonical KDE Frameworks Tier 1 state after Batch 6 closure: **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**. KWindowSystem and Solid were promoted from final workflow run `35047623320`; historical sections below remain historical evidence.\n'''
append_once('docs/status/2026-09-15.md',marker,status_banner,prepend=True)
print('Batch 6 closure materialized')
