#!/usr/bin/env python3
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
counts={s:sum(x.get('state')==s for x in t['nodes']) for s in ('PASS','pending','FAIL','BLOCKED')}; req(counts=={'PASS':21,'pending':8,'FAIL':0,'BLOCKED':0},f'Tier1 current counts {counts}')
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
print('Canonical Tier 1 current state: 21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED; Batch 6 historical closure remains 18/11')
