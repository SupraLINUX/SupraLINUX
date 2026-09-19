#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/'manifests/kde-tier1-package-campaign-batch9.json'; ATTEMPTS=ROOT/'manifests/kde-tier1-package-batch9-attempts.json'; TIER1=ROOT/'manifests/kde-frameworks-tier1.json'; DISCOVERY=ROOT/'manifests/kde-tier1-global-discovery.json'
WORKFLOW=ROOT/'.github/workflows/kde-tier1-package-batch9.yml'; ROUTER=ROOT/'.github/workflows/pr-ci-router.yml'; POLICY=ROOT/'.github/workflows/repository-policy.yml'; RUNNER=ROOT/'scripts/run-kde-tier1-package-batch9-preflight.sh'; SCOPE=ROOT/'scripts/kde-tier1-package-batch9-needed.sh'; SCOPE_TEST=ROOT/'scripts/test-kde-tier1-package-batch9-scope.sh'; DOC=ROOT/'docs/kde-tier1-package-batch9.md'
errors=[]
def req(c,m):
 if not c: errors.append(m)
def text(p):
 if not p.exists(): errors.append(f'missing {p.relative_to(ROOT)}'); return ''
 return p.read_text()
try:
 c=json.loads(CAMPAIGN.read_text()); a=json.loads(ATTEMPTS.read_text()); t=json.loads(TIER1.read_text()); g=json.loads(DISCOVERY.read_text())
except Exception as e: print(f'ERROR: cannot read Batch 9 manifests: {e}',file=sys.stderr); raise SystemExit(1)
req(c.get('schema')==2 and c.get('batch')=='tier1-batch-9' and c.get('lane')=='multi-abi','Batch 9 campaign identity mismatch')
req(c.get('frameworks_series')=='6.30.0' and c.get('authority')=='kde-upstream' and c.get('provider_platform')=='ubuntu-resolute','Batch 9 authority/provider/version mismatch')
req(c.get('selected_nodes')==['kconfig','ki18n','sonnet'],'Batch 9 selected nodes/order mismatch')
req(c.get('canonical_snapshot')=={'state':'pre-batch-9','tier1':'22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED after Batch 8 canonical promotion'},'Batch 9 historical snapshot mismatch')
s=c.get('shared_predecessors',{})
req(s.get('extra_cmake_modules')=={'state':'PASS','version':'6.30.0-0supralinux3','workflow_run':34694951158,'artifact_id':10298635300,'deb_sha256':'ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f'},'Batch 9 ECM predecessor evidence mismatch')
pt=s.get('packaging_trees',{}); req(pt.get('workflow_run')==34708030450 and pt.get('artifact_id')==10301938362 and pt.get('artifact_sha256')=='6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6' and pt.get('snapshot_json_sha256')=='f761a2d92005107eac2e82322b1b776e4f8867851e657ce79748f0cb266ee345','packaging-tree evidence mismatch')
bc=s.get('binary_contracts',{}); req(bc.get('workflow_run')==34704117024 and bc.get('artifact_id')==10301282501 and bc.get('artifact_sha256')=='9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97' and bc.get('contracts_json_sha256')=='e44507d0dd73db913a91bd4852c452f783618aab0bd6a3790e4c4f4c40707b7b','binary-contract reference evidence mismatch')
sd=s.get('source_diagnostic',{}); req(sd.get('workflow_run')==35138333645 and sd.get('commit')=='6b3a8b9f408c5fff4bceec81ac9ffb3e47a4dbd3' and sd.get('promotes_package_state') is False,'source diagnostic must remain non-promoting')
expected={
'kconfig':('kf6-kconfig','0e98bac324cd716849202d4b246a948e363d6792a8eb09c78417cdde9559f56e','6.30.0-0supralinux4',9,3,104936243505,10464074545,'9f05b0e368c4d1a7eb3dbec441680b423fd3f8b4a7fc2a0cdcbf9edbb3ca6e68'),
'ki18n':('kf6-ki18n','dfbfc8af89b3bc68810b094bf87746db87c3eeb35b75caeb1882681ebed563bd','6.30.0-0supralinux1',8,3,104936243967,10463404553,'86b5f05313d164358ac36e1cc4982b72fad90bad3175114d2b2b493691a6bec3'),
'sonnet':('kf6-sonnet','1574ef5c17f38e315de104b94580ccc1b7ec1db2650cb4bace2e14159bf61e10','6.30.0-0supralinux3',8,2,104936243844,10464073832,'6b17c7f02213282a520f4127feb010e9a37dbbafce9c8ab17d7f76164b22d7b6')}
canonical={x['id']:x for x in t.get('nodes',[])}
for node,(source,sha,package_version,nbin,nabi,job,artifact,digest) in expected.items():
 n=c.get('nodes',{}).get(node,{}); pkg=ROOT/'packages/kde'/node/'debian'; cons=ROOT/'packages/kde'/node/'consumer'
 req(n.get('upstream_version')=='6.30.0' and n.get('source_package')==source and n.get('package_version')==package_version and n.get('source_sha256')==sha,f'{node}: source/package pin mismatch')
 req(n.get('kde_framework_build_dependencies')==[],f'{node}: Tier 1 build dependency regression')
 req(n.get('upstream_defaults',{}).get('BUILD_TESTING')=='ON',f'{node}: BUILD_TESTING must be ON')
 req(n.get('qch_profile')=='OFF-common-supralinux-frameworks',f'{node}: QCH profile mismatch')
 req(len(n.get('binary_contracts',[]))==nbin and len(n.get('abi_contracts',[]))==nabi,f'{node}: binary/ABI contract count mismatch')
 abi_expected={
  'kconfig':{'ConfigCore':(648,6,8,634),'ConfigGui':(170,2,0,168),'ConfigQml':(22,0,0,22)},
  'ki18n':{'I18n':(122,1,0,121),'I18nLocaleData':(58,2,0,56),'I18nQml':(33,0,0,33)},
  'sonnet':{'SonnetCore':(263,9,0,254),'SonnetUi':(179,5,0,174)}
 }[node]
 for abi in n.get('abi_contracts',[]):
  exp=abi_expected.get(abi.get('surface'))
  req(exp is not None,f"{node}/{abi.get('surface')}: unexpected ABI surface")
  if exp is not None:
   req((abi.get('reference_export_count'),abi.get('reference_optional_export_count'),abi.get('reference_nonoptional_inapplicable_amd64_count'),abi.get('reference_required_export_count_amd64'))==exp,f"{node}/{abi.get('surface')}: ABI baseline partition mismatch")
 d=n.get('diagnostic_evidence',{}); req(d.get('workflow_run')==35138333645 and d.get('job_id')==job and d.get('artifact_id')==artifact and d.get('artifact_sha256')==digest and d.get('result')=='DIAG_PASS' and d.get('promotes_package_state') is False,f'{node}: DIAG_PASS evidence mismatch')
 req(n.get('state') in {'prepared-pending-build','remediation-pending-build','PASS'},f'{node}: invalid campaign state')
 can=canonical.get(node,{})
 pkgcan=can.get('packaging',{})
 req(can.get('state')=='PASS' and pkgcan.get('state')=='PASS',f'{node}: canonical state must be promoted PASS')
 req(pkgcan.get('package_version')==package_version and pkgcan.get('downstream_eligible') is True and pkgcan.get('attempt_ledger')=='manifests/kde-tier1-package-batch9-attempts.json',f'{node}: canonical packaging promotion mismatch')
 req(pkgcan.get('claim')=='hosted-clean-package-preflight' and pkgcan.get('authoritative') is False,f'{node}: canonical hosted PASS claim mismatch')
 canon_passes=[x for x in pkgcan.get('evidence',[]) if isinstance(x,dict) and x.get('result')=='PASS']
 req(len(canon_passes)==1,f'{node}: canonical promotion must retain exactly one current PASS')
 if canon_passes:
  cp=canon_passes[0]; pe=n.get('pass_evidence',{})
  req(cp.get('workflow_run')==pe.get('workflow_run') and cp.get('job_id')==pe.get('job_id') and cp.get('artifact_id')==pe.get('artifact_id') and cp.get('artifact_sha256')==pe.get('artifact_sha256') and cp.get('tests')==pe.get('tests') and cp.get('lintian')=='PASS-errors' and cp.get('consumer_smoke')=='PASS' and cp.get('apt_check')=='PASS' and cp.get('qml_import_smoke')=='PASS',f'{node}: canonical PASS evidence mismatch')
  req(cp.get('abi_sonames')==[a['soname'] for a in n.get('abi_contracts',[])],f'{node}: canonical ABI SONAME evidence mismatch')
 for rel in ('README.source','changelog','control','copyright.reference','rules','source/format','upstream/signing-key.asc'):
  req((pkg/rel).exists(),f'{node}: missing package file {rel}')
 req((cons/'CMakeLists.txt').exists() and (cons/'main.cpp').exists(),f'{node}: consumer source missing')
 control=text(pkg/'control'); rules=text(pkg/'rules'); readme=text(pkg/'README.source')
 req('Maintainer: SupraLINUX Project <packages@supralinux.invalid>' in control and 'Rules-Requires-Root: no' in control,f'{node}: Supra metadata missing')
 req('extra-cmake-modules (>= 6.30.0~)' in control,f'{node}: ECM floor mismatch')
 req('-DBUILD_TESTING=ON' in rules and '-DBUILD_QCH=OFF' in rules,f'{node}: test/QCH profile mismatch')
 req('QSKIP' not in '\n'.join(p.name for p in (pkg/'patches').glob('*')) if (pkg/'patches').exists() else True,f'{node}: QSKIP patch present')
 req(not (pkg/'patches/cross.patch').exists(),f'{node}: Debian cross.patch must not be carried')
 key=pkg/'upstream/signing-key.asc'
 if key.exists(): req(hashlib.sha256(key.read_bytes()).hexdigest()=='86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d',f'{node}: signing key hash mismatch')
 for abi in n.get('abi_contracts',[]):
  req(len(abi.get('reference_sha256',''))==64 and abi.get('reference_export_count',0)>0,f"{node}/{abi.get('surface')}: retained symbols evidence incomplete")
  req(not (pkg/abi['symbols_file']).exists(),f"{node}/{abi['surface']}: active symbols file must be materialized only by clean runner")
  req(not (pkg/(abi['symbols_file']+'.reference')).exists(),f"{node}/{abi['surface']}: retained baseline must not be duplicated into package tree")
 req('retained, hash-pinned Debian 6.28 packaging-tree artifact' in readme,f'{node}: retained symbols policy undocumented')
# Diagnostic provider fixtures must be preserved in package preparation; Ubuntu is provider, not authority.
req(c['nodes']['kconfig'].get('diagnostic_provider_packages')==['qt6-base-dev','qt6-base-private-dev','qt6-declarative-dev','qt6-tools-dev'],'KConfig diagnostic provider fixture mismatch')
req(c['nodes']['ki18n'].get('diagnostic_provider_packages')==['iso-codes','language-pack-fr-base','locales-all','qt6-base-dev','qt6-declarative-dev','qt6-tools-dev'],'KI18n diagnostic provider fixture mismatch')
req(c['nodes']['sonnet'].get('diagnostic_provider_packages')==['hspell','libaspell-dev','libhunspell-dev','libvoikko-dev','qt6-base-dev','qt6-declarative-dev','qt6-tools-dev'],'Sonnet diagnostic provider fixture mismatch')
ki_control=text(ROOT/'packages/kde/ki18n/debian/control'); ki_rules=text(ROOT/'packages/kde/ki18n/debian/rules')
req('language-pack-fr-base <!nocheck>' in ki_control and 'locales-all <!nocheck>' in ki_control,'KI18n test locale providers must match DIAG_PASS fixture')
req('env -u LC_ALL -u LC_COLLATE -u LC_CTYPE LANG=en_US.UTF-8' in ki_rules,'KI18n test environment must leave LC_ALL/LC_* unset')
# KConfig retains only layout patch; Sonnet/KI18n retain no patches.
kpol=c['nodes']['kconfig']['patch_policy']; req(kpol.get('retained')==['Allow-packagers-set-kconfig_compiler-install-dir.patch'] and len(kpol.get('excluded',[]))==2,'KConfig patch policy mismatch')
req((ROOT/'packages/kde/kconfig/debian/patches/series').read_text().strip()=='Allow-packagers-set-kconfig_compiler-install-dir.patch','KConfig series must contain only technical layout patch')
req(c['nodes']['sonnet']['patch_policy'].get('excluded')==['cross.patch'],'Sonnet cross.patch exclusion must be explicit')
req(c.get('state')=='PASS','Batch 9 campaign must be canonically promoted PASS')
req(c.get('canonical_promotion')=={'status':'promoted','tier1':'25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED','dag_nodes':['kconfig','ki18n','sonnet']},'Batch 9 canonical promotion snapshot mismatch')
# Reviewed ABI deltas are deterministic, hash-guarded, and run immediately before dh_makeshlibs.
deltas={
 'kconfig':{
  'script':'packages/kde/kconfig/debian/apply-symbols-delta.py',
  'base':'c131c44659cce576fbc0754a2a55fd470aa9c065f3efc7d92b49c0042dc758ea',
  'result':'8a8220263cd60e88208e68138cb0f7288a4d99d3a99c0349e62be314d9d1fd04',
  'symbol':'_ZN16KStandardActions16staticMetaObjectE@Base 6.29.0'},
 'sonnet':{
  'script':'packages/kde/sonnet/debian/apply-symbols-delta.py',
  'base':'da300d1551304beac95a201ecd5c27fbf1286fe1e2ef7ab893b959e5e656f2b6',
  'result':'e75af49fd74700ef8a2c21ce55decaf96439479223770c63654410f3c3f956bb',
  'symbol':'_ZN6Sonnet8Settings22defaultSkipRunTogetherEv@Base 6.30.0'}}
for node,meta in deltas.items():
 delta=text(ROOT/meta['script']); rules=text(ROOT/'packages/kde'/node/'debian/rules')
 req(meta['base'] in delta and meta['result'] in delta and meta['symbol'] in delta,f'{node}: reviewed symbols delta mismatch')
 req('override_dh_makeshlibs:' in rules and '\tpython3 debian/apply-symbols-delta.py' in rules and '\tdh_makeshlibs' in rules and rules.index('\tpython3 debian/apply-symbols-delta.py') < rules.index('\tdh_makeshlibs'),f'{node}: symbols delta must execute before dh_makeshlibs')
req('6.29.0' in text(ROOT/'packages/kde/kconfig/debian/apply-symbols-delta.py'),'KConfig reviewed ABI minimum mismatch')
req(c['nodes']['sonnet'].get('last_failure_evidence',{}).get('reviewed_upstream_minimum')=='6.30.0','Sonnet reviewed ABI minimum mismatch')
inc=c.get('validation_incidents',{})
incident_expected={
 'kconfig':(105633436677,10551433966,'eed45f10d52f3190fcf099ceb63c4138f1c346d191d6aa85429b1beafd829b95','cd684394244cb651b6d36171bf140e8dfae4905d92b5f4da2d87d89b66754629','90/90 PASS','ConfigCore',640,648,634),
 'sonnet':(105633436582,10551832586,'f9352e5f5c3cd527cc32887896b1c6c4441e1291ee103204de470e3378a77218','9e79ae0631e0c4b7a59f3fb82af976eaaf9c388c01b57edfebd30001f37d38af','8/8 PASS','SonnetCore',255,263,254)}
req(inc.get('ki18n')==[],'KI18n must have no cycle-3 validation incident')
for node,(job,artifact,digest,rootfs,tests,surface,observed,total,required) in incident_expected.items():
 hist=inc.get(node,[])
 req(len(hist)==1,f'{node}: expected exactly one validation-cycle-3 infrastructure incident')
 if len(hist)==1:
  x=hist[0]
  req(x.get('validation_cycle')==3 and x.get('commit')=='97e4feb51df541501b027ba80c4b86907d8763c8' and x.get('workflow_run')==35355395436 and x.get('job_id')==job and x.get('artifact_id')==artifact and x.get('artifact_sha256')==digest and x.get('rootfs_sha256')==rootfs and x.get('stage')=='abi-contract' and x.get('classification')=='runner-false-negative-total-export-floor' and x.get('package_state_effect')=='none' and x.get('package_build')=='successful' and x.get('lintian')=='PASS-errors' and x.get('tests')==tests and x.get('observed_surface')==surface and x.get('observed_exports')==observed and x.get('reference_total_exports')==total and x.get('reference_required_exports_amd64')==required,f'{node}: validation-cycle-3 incident evidence mismatch')
for node in ('kconfig','sonnet'):
 control=text(ROOT/'packages/kde'/node/'debian/control')
 readme=text(ROOT/'packages/kde'/node/'debian/README.source')
 req('python3:any,' in control,f'{node}: python3:any build prerequisite missing')
 req('attempt 2' in readme and 'python3:any' in readme,f'{node}: attempt-2 python3 remediation undocumented')
sonnet_lf=c['nodes']['sonnet'].get('last_failure_evidence',{})
req(sonnet_lf.get('workflow_run')==35354088696 and sonnet_lf.get('cause')=='lintian-rules-require-build-prerequisite-python3' and sonnet_lf.get('symbols_delta')=='PASS','sonnet: attempt-2 failure classification mismatch')
kconfig_lf=c['nodes']['kconfig'].get('last_failure_evidence',{})
req(kconfig_lf.get('validation_cycle')==4 and kconfig_lf.get('workflow_run')==35358920602 and kconfig_lf.get('job_id')==105645094816 and kconfig_lf.get('artifact_id')==10553307816 and kconfig_lf.get('artifact_sha256')=='7bc04355d35d9bd86033ffaceb89a2addbb79e9e5d49ef14f59be58f2cfde312' and kconfig_lf.get('rootfs_sha256')=='3c863b17d63bf75492b41bcb774d6d40616ffe646ded3d0c50fb51562c17df57' and kconfig_lf.get('stage')=='consumer-smoke' and kconfig_lf.get('cause')=='libkf6config-dev-missing-qt6-declarative-dev-consumer-closure' and kconfig_lf.get('apt_check')=='PASS' and kconfig_lf.get('qml_import_smoke')=='PASS','KConfig cycle-4 consumer failure evidence mismatch')
kconfig_pass=c['nodes']['kconfig'].get('pass_evidence',{})
req(c['nodes']['kconfig'].get('state')=='PASS' and c['nodes']['kconfig'].get('downstream_eligible') is True and kconfig_pass.get('validation_cycle')==5 and kconfig_pass.get('workflow_run')==35360530830 and kconfig_pass.get('job_id')==105650448776 and kconfig_pass.get('artifact_id')==10554715051 and kconfig_pass.get('artifact_sha256')=='bd36a8288c1c36fa2ae1a83d685a816cc1077fc576b59a23951972ddcbdd835e' and kconfig_pass.get('rootfs_sha256')=='cf14256f216dd3ec9a67a7bca3bd46e8624391ffe40b2c08567dc1fe90a4b9e3' and kconfig_pass.get('tests')=='90/90 PASS' and kconfig_pass.get('lintian')=='PASS-errors' and kconfig_pass.get('apt_check')=='PASS' and kconfig_pass.get('consumer_smoke')=='PASS' and kconfig_pass.get('qml_import_smoke')=='PASS' and kconfig_pass.get('abi_exports')=={'ConfigCore':640,'ConfigGui':171,'ConfigQml':22},'KConfig retained attempt-4 PASS evidence mismatch')
closure=c.get('closure_evidence',{})
req(closure.get('repository_policy',{}).get('workflow_run')==35360530531 and closure.get('repository_policy',{}).get('job_id')==105650391908 and closure.get('repository_policy',{}).get('result')=='PASS','Batch 9 final Repository Policy evidence mismatch')
req(closure.get('pr_ci',{}).get('workflow_run')==35360530830 and closure.get('pr_ci',{}).get('commit')=='bfb02cdc6f6086ed41092cc900563dfa3be86e64','Batch 9 final PR CI evidence mismatch')
req(closure.get('scope_skips',{}).get('ki18n',{}).get('job_id')==105650448606 and closure.get('scope_skips',{}).get('sonnet',{}).get('job_id')==105650448640,'Batch 9 retained PASS scope-skip evidence mismatch')
pre=c.get('promotion_precheck',{})
req(pre.get('repository_policy',{}).get('workflow_run')==35365719747 and pre.get('repository_policy',{}).get('job_id')==105667583358 and pre.get('repository_policy',{}).get('result')=='PASS','Batch 9 promotion precheck Repository Policy mismatch')
req(pre.get('scope_skips')=={'kconfig':105667619494,'ki18n':105667619517,'sonnet':105667619509},'Batch 9 promotion precheck scope-skip evidence mismatch')
rp=c.get('repository_policy_incidents',[])
req(len(rp)==1 and rp[0].get('workflow_run')==35365460369 and rp[0].get('job_id')==105666708183 and rp[0].get('classification')=='infrastructure-validator-documentation-case-sensitivity' and rp[0].get('package_state_effect')=='none','Batch 9 closure-validator incident evidence mismatch')
kconfig_control=text(ROOT/'packages/kde/kconfig/debian/control')
m=re.search(r'(?ms)^Package: libkf6config-dev\n(.*?)(?=^Package:|\Z)',kconfig_control)
req(m is not None,'KConfig libkf6config-dev stanza missing')
if m:
 req('qt6-declarative-dev (>= 6.9.0~),' in m.group(1),'KConfig libkf6config-dev must depend on qt6-declarative-dev >= 6.9.0')
req('validation cycle 4' in text(ROOT/'packages/kde/kconfig/debian/README.source') and 'Qt6Qml' in text(ROOT/'packages/kde/kconfig/debian/README.source'),'KConfig cycle-4 consumer dependency remediation undocumented')
ki_pass=c['nodes']['ki18n'].get('pass_evidence',{})
req(c['nodes']['ki18n'].get('state')=='PASS' and c['nodes']['ki18n'].get('downstream_eligible') is True and ki_pass.get('validation_cycle')==4 and ki_pass.get('workflow_run')==35358920602 and ki_pass.get('job_id')==105645094825 and ki_pass.get('artifact_id')==10553916882 and ki_pass.get('artifact_sha256')=='2a0d66f2760c49ba1128b8b51c741173a72e6f3ab51f3eb17c3584896d30a678' and ki_pass.get('rootfs_sha256')=='c3a542cadce65b491d0997f7fa61cfabc2b44188a2021c151858349766fd148d' and ki_pass.get('tests')=='17/17 PASS' and ki_pass.get('consumer_smoke')=='PASS','KI18n retained cycle-4 PASS evidence mismatch')
sonnet_pass=c['nodes']['sonnet'].get('pass_evidence',{})
req(c['nodes']['sonnet'].get('state')=='PASS' and c['nodes']['sonnet'].get('downstream_eligible') is True and sonnet_pass.get('validation_cycle')==4 and sonnet_pass.get('workflow_run')==35358920602 and sonnet_pass.get('job_id')==105645094787 and sonnet_pass.get('artifact_id')==10554216487 and sonnet_pass.get('artifact_sha256')=='ae5a33cf8699b96b7b7b8c1a83bc4d37a484878029818c1885b4f4f44f15b431' and sonnet_pass.get('rootfs_sha256')=='38f9fcd9dd6cb379bd5ba1fbfb5c93f57b49db71c166615415ff663366fc54bb' and sonnet_pass.get('tests')=='8/8 PASS' and sonnet_pass.get('consumer_smoke')=='PASS','Sonnet retained cycle-4 PASS evidence mismatch')
# Attempt ledger is append-only and now records the three real attempt-1 results.
req(a.get('schema')==1 and a.get('batch')=='tier1-batch-9','Batch 9 attempts identity mismatch')
for node in expected:
 hist=a.get('attempts',{}).get(node); req(isinstance(hist,list),f'{node}: attempts list missing')
 if isinstance(hist,list):
  req([x.get('attempt') for x in hist]==list(range(1,len(hist)+1)),f'{node}: attempt numbers not append-only/sequential')
  req(all(x.get('result') in {'PASS','FAIL'} for x in hist),f'{node}: attempt result must be PASS/FAIL only')
attempt1_expected={
 'kconfig':(105609530611,10549115856,'6579cc838436e1390c950da9037997ae4646fb4fb40d5e69290377c16f385b6c','FAIL','90/90 PASS'),
 'ki18n':(105609530707,10548710619,'d213147477242b08a1dac78611b30eacb60f9bd727abb1313d5a2c8bc7c24cf4','PASS','17/17 PASS'),
 'sonnet':(105609530666,10549100349,'d01d279dc2645efd9ecc01506e17c0f99aecadda761bc12236af7ae1341a3fc6','FAIL','8/8 PASS')}
for node,(job,artifact,digest,result,tests) in attempt1_expected.items():
 hist=a['attempts'][node]
 req(len(hist)>=1,f'{node}: attempt 1 evidence missing')
 if hist:
  x=hist[0]
  req(x.get('attempt')==1 and x.get('commit')=='958d9990f0c5c6e85ade45faf8b7fa1a62c0c3af' and x.get('workflow_run')==35348130023 and x.get('job_id')==job and x.get('artifact_id')==artifact and x.get('artifact_sha256')==digest and x.get('result')==result and x.get('tests')==tests,f'{node}: attempt 1 retained evidence mismatch')
attempt2_expected={
 'kconfig':(105629086800,10551565818,'44095dd2f16b7101c0f1dbe65fb561d79361b28a8b5f255151760e64a4ea09a3','a3ef32e90b7f8c734110becf63a327503855e3c5d495fb340668f944cb24b30c','FAIL','90/90 PASS'),
 'ki18n':(105629086722,10550338682,'08271a40a392b0d947b05413c54c913230261d26bff1ed12d91d37a85400a3bd','2e45730952a04dc7b8ed5fe96c6e479427697a5d6fc0c840cc8817fe81c24974','PASS','17/17 PASS'),
 'sonnet':(105629086871,10551700066,'3d995b55c0e106554957bd7cfc2a1f63df19fc3c7b95a59be9fa0df51a9f6c23','bca53d5e3e2f5e536987ad3d8885ba44d814db9a2bd80b7ed07b006bc394b5f7','FAIL','8/8 PASS')}
for node,(job,artifact,digest,rootfs,result,tests) in attempt2_expected.items():
 hist=a['attempts'][node]
 req(len(hist)>=2,f'{node}: attempt 2 evidence missing')
 if len(hist)>=2:
  x=hist[1]
  req(x.get('attempt')==2 and x.get('commit')=='f23d5b995468d16189ef18e9b59b63ac3927736f' and x.get('workflow_run')==35354088696 and x.get('job_id')==job and x.get('artifact_id')==artifact and x.get('artifact_sha256')==digest and x.get('rootfs_sha256')==rootfs and x.get('result')==result and x.get('tests')==tests,f'{node}: attempt 2 retained evidence mismatch')
attempt3_expected={
 'kconfig':(105645094816,10553307816,'7bc04355d35d9bd86033ffaceb89a2addbb79e9e5d49ef14f59be58f2cfde312','3c863b17d63bf75492b41bcb774d6d40616ffe646ded3d0c50fb51562c17df57','6.30.0-0supralinux3','FAIL','consumer-smoke','90/90 PASS'),
 'ki18n':(105645094825,10553916882,'2a0d66f2760c49ba1128b8b51c741173a72e6f3ab51f3eb17c3584896d30a678','c3a542cadce65b491d0997f7fa61cfabc2b44188a2021c151858349766fd148d','6.30.0-0supralinux1','PASS','complete','17/17 PASS'),
 'sonnet':(105645094787,10554216487,'ae5a33cf8699b96b7b7b8c1a83bc4d37a484878029818c1885b4f4f44f15b431','38f9fcd9dd6cb379bd5ba1fbfb5c93f57b49db71c166615415ff663366fc54bb','6.30.0-0supralinux3','PASS','complete','8/8 PASS')}
for node,(job,artifact,digest,rootfs,version,result,stage,tests) in attempt3_expected.items():
 hist=a['attempts'][node]
 req(len(hist)>=3,f'{node}: attempt 3 evidence missing')
 if len(hist)>=3:
  x=hist[2]
  req(x.get('attempt')==3 and x.get('validation_cycle')==4 and x.get('package_version')==version and x.get('commit')=='1048fd52df303957d2db82c29988c8170b6fd656' and x.get('workflow_run')==35358920602 and x.get('job_id')==job and x.get('artifact_id')==artifact and x.get('artifact_sha256')==digest and x.get('rootfs_sha256')==rootfs and x.get('result')==result and x.get('stage')==stage and x.get('tests')==tests,f'{node}: attempt 3 retained evidence mismatch')
hist=a['attempts']['kconfig']
req(len(hist)==4,'KConfig attempt 4 must be the final retained Batch 9 package attempt')
if len(hist)>=4:
 x=hist[3]
 req(x.get('attempt')==4 and x.get('validation_cycle')==5 and x.get('package_version')=='6.30.0-0supralinux4' and x.get('commit')=='bfb02cdc6f6086ed41092cc900563dfa3be86e64' and x.get('workflow_run')==35360530830 and x.get('job_id')==105650448776 and x.get('artifact_id')==10554715051 and x.get('artifact_sha256')=='bd36a8288c1c36fa2ae1a83d685a816cc1077fc576b59a23951972ddcbdd835e' and x.get('rootfs_sha256')=='cf14256f216dd3ec9a67a7bca3bd46e8624391ffe40b2c08567dc1fe90a4b9e3' and x.get('result')=='PASS' and x.get('stage')=='complete' and x.get('tests')=='90/90 PASS' and x.get('downstream_eligible') is True,'KConfig attempt 4 retained PASS evidence mismatch')
req(len(a['attempts']['ki18n'])==3 and len(a['attempts']['sonnet'])==3,'Scope-skipped KI18n/Sonnet must not gain fake package attempts')
ledger_inc=a.get('validation_incidents',{})
req(ledger_inc.get('ki18n')==[],'KI18n attempt ledger must have no validation-cycle-3 incident')
for node,(job,artifact,digest,rootfs,tests,_,observed,total,required) in incident_expected.items():
 hist=ledger_inc.get(node,[])
 req(len(hist)==1,f'{node}: attempt ledger validation incident missing')
 if len(hist)==1:
  x=hist[0]
  req(x.get('validation_cycle')==3 and x.get('classification')=='INFRA' and x.get('package_state_effect')=='none' and x.get('commit')=='97e4feb51df541501b027ba80c4b86907d8763c8' and x.get('workflow_run')==35355395436 and x.get('job_id')==job and x.get('artifact_id')==artifact and x.get('artifact_sha256')==digest and x.get('rootfs_sha256')==rootfs and x.get('tests')==tests,f'{node}: attempt ledger infrastructure incident mismatch')
# After canonical promotion, Batch 9 leaves global discovery and the lane is completed.
req(set(g.get('nodes',{}))=={'kirigami','kquickcharts','kuserfeedback','prison'},'post-Batch9 global discovery set mismatch')
for node in expected: req(node not in g.get('nodes',{}),f'{node}: promoted PASS must leave global discovery')
ma=g.get('lanes',{}).get('multi-abi',{})
req(ma.get('status')=='completed' and ma.get('nodes')==[],'multi-ABI lane must be completed after Batch 9 promotion')
snap=g.get('promoted_snapshot',{})
req((snap.get('pass'),snap.get('pending'),snap.get('current_fail'),snap.get('blocked'))==(25,4,0,0),'post-Batch9 promoted snapshot mismatch')
workflow=text(WORKFLOW); router=text(ROUTER); policy=text(POLICY); runner=text(RUNNER); scope=text(SCOPE); scope_test=text(SCOPE_TEST); doc=text(DOC)
for token in ('fail-fast: false','max-parallel: 3','node: [kconfig, ki18n, sonnet]','artifact-ids: \'10298635300\'','artifact-ids: \'10301938362\'','artifact-ids: \'10301282501\'','run-kde-tier1-package-batch9-preflight.sh'):
 req(token in workflow,f'Batch 9 workflow missing {token}')
req('uses: ./.github/workflows/kde-tier1-package-batch9.yml' in router,'PR router must invoke Batch 9')
req('Test KDE Tier 1 Batch 9 package scope' in policy and 'Validate KDE Tier 1 batch 9 preparation' in policy,'Repository Policy must test/validate Batch 9')
for token in ('abi-contract','reference_required_export_count_amd64','reference_optional_export_count','reference_nonoptional_inapplicable_amd64_count','abi-reference-counts.txt',"STAGE='qml-import-smoke'","STAGE='qml-package-contract'",'consumer-runtime-closure','lintian --fail-on error','0supralinux','DDEBS','sbuild --verbose'):
 req(token in runner,f'Batch 9 runner gate missing {token}')
req('manifests/kde-tier1-package-campaign-batch9.json' in scope and 'packages/kde/${NODE}/' in scope,'Batch 9 scope selector contract missing')
req('KDE Tier 1 Batch 9 scope selector: PASS' in scope_test,'Batch 9 scope test marker missing')
for token in ('9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97','DIAG_PASS','QSKIP','cross.patch','22 PASS / 7 pending','6.30.0-0supralinux1','package_state_effect=none','634','254','reference_required_export_count_amd64','validation cycle 4','validation cycle 5','Qt6Qml','qt6-declarative-dev','10553307816','10553916882','10554216487','10554715051','bd36a8288c1c36fa2ae1a83d685a816cc1077fc576b59a23951972ddcbdd835e','25 PASS / 4 pending','35365719747'):
 req(token.lower() in doc.lower(),f'Batch 9 documentation missing {token}')
if errors:
 for e in errors: print('ERROR:',e,file=sys.stderr)
 raise SystemExit(1)
print('KDE Tier 1 Batch 9 preparation validation: PASS')
print('Batch 9 canonical closure: 3/3 PASS promoted; Tier 1 is 25 PASS / 4 pending / 0 FAIL / 0 BLOCKED')
print('Lane: multi-ABI completed; remaining discovery nodes=4')
