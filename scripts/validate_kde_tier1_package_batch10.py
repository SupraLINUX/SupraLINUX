#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
 if not v: errors.append(m)
def text(p): return p.read_text(errors='replace')
def js(p): return json.loads(p.read_text())

C=ROOT/'manifests/kde-tier1-package-campaign-batch10.json'; A=ROOT/'manifests/kde-tier1-package-batch10-attempts.json'
req(C.is_file(),'Batch 10 campaign missing'); req(A.is_file(),'Batch 10 attempts ledger missing')
if not C.is_file() or not A.is_file():
 print('\n'.join(errors),file=sys.stderr); raise SystemExit(1)
c=js(C); a=js(A)
req(c.get('schema')==2 and c.get('batch')=='tier1-batch-10' and c.get('lane')=='qml-multisurface','Batch 10 identity mismatch')
req(c.get('frameworks_series')=='6.30.0' and c.get('authority')=='kde-upstream' and c.get('provider_platform')=='ubuntu-resolute','authority/provider mismatch')
req(c.get('state')=='remediation-pending-build','Batch 10 campaign must record Kirigami attempt-1 remediation state')
req(c.get('canonical_snapshot',{}).get('tier1')=='25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED after Batch 9 canonical promotion','canonical pre-Batch10 snapshot mismatch')
req(c.get('selected_nodes')==['kirigami','kquickcharts'],'selected node order mismatch')
s=c.get('shared_predecessors',{})
req(s.get('extra_cmake_modules',{}).get('version')=='6.30.0-0supralinux3' and s.get('extra_cmake_modules',{}).get('artifact_id')==10298635300,'ECM retained predecessor mismatch')
req(s.get('packaging_trees',{}).get('artifact_id')==10301938362 and s.get('packaging_trees',{}).get('artifact_sha256')=='6e91848334c018e15d7bdc1752eb5b494bdeeda8ca04c9323dde46844cf26de6','packaging reference mismatch')
req(s.get('binary_contracts',{}).get('artifact_id')==10301282501 and s.get('binary_contracts',{}).get('artifact_sha256')=='9441b2f2957b350a46026b0df3bd5eb3578e1578671aab3b7afc7a0929ce1a97','binary contract reference mismatch')
expected={
 'kirigami':('kf6-kirigami','6de811e559c20dc1086c0cf2c34bb98712dbe4d45f960c62c3c3f887332c95f8',19,15,44,104936243949,10464419377,'f83a7e508fa2031dcf5401a7590e9598ab3d5888230af60b153c4b77d4b53185'),
 'kquickcharts':('kf6-kquickcharts','9fe8c0c78ffd23ccfb99cc36477550a229c114ad057def938f38cdec35f82ab1',4,2,8,104936243779,10463808939,'5d1023d260fe167d846a8b3f16310c6771bb08f79688095bd27ba5ea79798a28')}
abi_expected={
 'kirigami':{'Kirigami':(12,2,0,10),'KirigamiControls':(19,4,0,15),'KirigamiDelegates':(1,0,0,1),'KirigamiDialogs':(1,0,0,1),'KirigamiForms':(1,0,0,1),'KirigamiFormsPrivateCards':(1,0,0,1),'KirigamiFormsPrivateFlat':(1,0,0,1),'KirigamiFormsPrivateTemplates':(1,0,0,1),'KirigamiLayouts':(26,7,0,19),'KirigamiLayoutsPrivate':(1,0,0,1),'KirigamiPlatform':(445,7,10,428),'KirigamiPolyfill':(1,0,0,1),'KirigamiPrimitives':(20,1,9,10),'KirigamiPrivate':(10,2,0,8),'KirigamiTemplates':(1,0,0,1)},
 'kquickcharts':{'QuickCharts':(393,2,9,382),'QuickChartsControls':(1,0,0,1)}}
versions={'kirigami':'6.30.0-0supralinux2','kquickcharts':'6.30.0-0supralinux1'}
for node,(source,sha,nbin,nabi,tests,job,artifact,digest) in expected.items():
 n=c['nodes'][node]; pkg=ROOT/'packages/kde'/node/'debian'; consumer=ROOT/'packages/kde'/node/'consumer'
 req(n.get('source_package')==source and n.get('source_sha256')==sha and n.get('package_version')==versions[node],f'{node}: source/version mismatch')
 req(n.get('kde_framework_build_dependencies')==[],f'{node}: must remain Tier 1 at upstream build level')
 req(n.get('expected_test_count')==tests,f'{node}: expected test count mismatch')
 de=n.get('diagnostic_evidence',{}); req(de.get('workflow_run')==35138333645 and de.get('job_id')==job and de.get('artifact_id')==artifact and de.get('artifact_sha256')==digest and de.get('result')=='DIAG_PASS' and de.get('promotes_package_state') is False,f'{node}: DIAG evidence mismatch')
 req(len(n.get('binary_contracts',[]))==nbin and len(n.get('abi_contracts',[]))==nabi,f'{node}: binary/ABI count mismatch')
 for abi in n.get('abi_contracts',[]):
  exp=abi_expected[node].get(abi.get('surface')); req(exp is not None,f'{node}: unexpected ABI {abi.get("surface")}')
  if exp: req((abi.get('reference_export_count'),abi.get('reference_optional_export_count'),abi.get('reference_nonoptional_inapplicable_amd64_count'),abi.get('reference_required_export_count_amd64'))==exp,f'{node}/{abi.get("surface")}: ABI partition mismatch')
 req(n.get('downstream_eligible') is False,f'{node}: pre-PASS package must not be downstream eligible')
 for f in ('control','rules','changelog','README.source','copyright.reference','run-tests-under-x.sh','source/format','upstream/signing-key.asc'): req((pkg/f).is_file(),f'{node}: missing debian/{f}')
 req((consumer/'CMakeLists.txt').is_file() and (consumer/'main.cpp').is_file(),f'{node}: consumer missing')
 control=text(pkg/'control'); rules=text(pkg/'rules')
 req('Maintainer: SupraLINUX Project <packages@supralinux.invalid>' in control and 'Rules-Requires-Root: no' in control,f'{node}: control ownership/root contract mismatch')
 req('extra-cmake-modules (>= 6.30.0~)' in control,f'{node}: ECM floor mismatch')
 req('-DBUILD_TESTING=ON' in rules and 'dbus-run-session -- xvfb-run' in rules,f'{node}: mandatory test fixture missing')
 req('BUILD_QCH=ON' not in rules and 'QT_QML_NO_CACHEGEN=ON' not in rules and '|| true' not in rules,f'{node}: forbidden downstream behavior override')
 req(not list(pkg.glob('*.symbols')) and not list(pkg.glob('*.symbols.reference')),f'{node}: retained symbols baseline must not be duplicated in git')
kir=c['nodes']['kirigami']; quick=c['nodes']['kquickcharts']
req(kir.get('state')=='remediation-pending-build' and kir.get('last_result')=='FAIL','Kirigami remediation state mismatch')
req(quick.get('state')=='prepared-pending-build' and quick.get('last_result')=='BLOCKED','KQuickCharts must retain BLOCKED as last result while remaining attemptable after Kirigami PASS')
lf=kir.get('last_failure_evidence',{})
req(lf.get('workflow_run')==35389030840 and lf.get('job_id')==105742841430 and lf.get('artifact_id')==10565625878 and lf.get('artifact_sha256')=='58b5bc72f81cdd26ea368cf810d1e1727fbdfc521203fe889bca005aa2f9aca8' and lf.get('rootfs_sha256')=='445ce98267d53ec58a98bed3ee74343f04f2465bdccf258efa95e709551ff7b1' and lf.get('tests')=='44/44 PASS' and lf.get('stage')=='sbuild','Kirigami failure evidence mismatch')
lb=quick.get('last_blocked_evidence',{})
req(lb.get('workflow_run')==35389030840 and lb.get('job_id')==105745672521 and lb.get('artifact_id')==10565780756 and lb.get('artifact_sha256')=='118afc6b702b4ec9fee050898fcbc381f5beaf2131013b619973c85e81f27ef8' and lb.get('blocked_by')=='kirigami' and lb.get('package_attempted') is False,'KQuickCharts BLOCKED evidence mismatch')
rem=kir.get('symbols_remediation',{})
req(rem.get('policy')=='optional=templinst' and len(rem.get('files',[]))==5,'Kirigami symbols-remediation policy mismatch')
rem_expected={
 'libkirigamicontrols6.symbols':('18a292f5b614aecb1f71d1f2335989dc6b7217e25dccf511e11b38c1d3206849','71cc0b7a2622f7b9b98c9d87dfa5e7824743025ff8960fdb5ef28da9ffe67f38',9,'6.30.0'),
 'libkirigamidelegates6.symbols':('b58d788f8cae861b02fdc5a681d84a23adda77d65461b84da0e1368256bfee2f','7b2f50807ea409c91094e36605a37cf8190910e0be23f8e472a051d9bcbb9954',9,'6.23.0'),
 'libkirigamiformsprivatecards6.symbols':('080732bf5305417218086c8849c77b08508a7315acfaca5e4e130161c3951614','4483ccb4b6cc376bb28e5ac408147b8cf3f190b9a394f1b38326d7500671925f',9,'6.30.0'),
 'libkirigamiformsprivateflat6.symbols':('6b501c473adb47811bb556bfd3376e5300bfc9af678b09531a375ddd1870089b','75c25d52c7415502d200b57f4dea7d9a8405aa3df20a2d5ea03349d5812fcc61',9,'6.30.0'),
 'libkirigamitemplates6.symbols':('c58094969b409f527c6fdcfc5af14ca42da6c604637cfd4b72bcc1f2c03f51e1','b60af9408ad63c919775ce099d040a5207069dd972e5daee98c974336e038582',2,'6.30.0')}
seen_rem={x.get('symbols_file'):(x.get('baseline_sha256'),x.get('result_sha256'),x.get('added_optional_symbols'),x.get('minimum_version')) for x in rem.get('files',[])}
req(seen_rem==rem_expected,'Kirigami deterministic symbols-remediation hashes mismatch')
kir_pkg=ROOT/'packages/kde/kirigami/debian'; delta=kir_pkg/'apply-symbols-delta.py'
req(delta.is_file(),'Kirigami symbols-delta helper missing')
delta_txt=text(delta); kir_control=text(kir_pkg/'control'); kir_rules=text(kir_pkg/'rules')
for token in ('optional=templinst','71cc0b7a2622f7b9b98c9d87dfa5e7824743025ff8960fdb5ef28da9ffe67f38','7b2f50807ea409c91094e36605a37cf8190910e0be23f8e472a051d9bcbb9954','4483ccb4b6cc376bb28e5ac408147b8cf3f190b9a394f1b38326d7500671925f','75c25d52c7415502d200b57f4dea7d9a8405aa3df20a2d5ea03349d5812fcc61','b60af9408ad63c919775ce099d040a5207069dd972e5daee98c974336e038582','6.23.0'):
 req(token in delta_txt,f'Kirigami symbols-delta helper missing {token}')
req('python3:any' in kir_control,'Kirigami delta helper requires python3:any Build-Depends')
req('override_dh_makeshlibs:' in kir_rules and 'python3 debian/apply-symbols-delta.py' in kir_rules,'Kirigami rules do not apply reviewed symbols delta before dh_makeshlibs')
if c['nodes']['kirigami']['upstream_defaults']!={'BUILD_SHARED_LIBS':'ON','DESKTOP_ENABLED':'ON','BUILD_EXAMPLES':'OFF','UBUNTU_TOUCH':'OFF','USE_DBUS':'ON','BUILD_TESTING':'ON'}: errors.append('Kirigami upstream defaults mismatch')
if c['nodes']['kquickcharts']['upstream_defaults']!={'BUILD_SHARED_LIBS':'ON','BUILD_EXAMPLES':'OFF','BUILD_TESTING':'ON'}: errors.append('KQuickCharts upstream defaults mismatch')
kp=c['nodes']['kquickcharts'].get('package_validation_dependencies',[])
req(len(kp)==1 and kp[0].get('node')=='kirigami' and kp[0].get('kind')=='qml-runtime-closure' and kp[0].get('not_kde_framework_build_dependency') is True,'QuickCharts Kirigami package-validation dependency mismatch')
req(c['nodes']['kirigami'].get('package_validation_dependencies')==[],'Kirigami must have no package-validation predecessor')
req(a.get('validation_incidents')=={'kirigami':[],'kquickcharts':[]},'Batch 10 validation-incident ledger mismatch')
ka=a.get('attempts',{}).get('kirigami',[]); qa=a.get('attempts',{}).get('kquickcharts',[])
req(len(ka)==1 and qa==[],'Batch 10 real-attempt ledger must contain only Kirigami attempt 1')
if len(ka)==1:
 x=ka[0]
 req(x.get('attempt')==1 and x.get('package_version')=='6.30.0-0supralinux1' and x.get('commit')=='67a6558513a82d4a1b4426a9b705eafdadbd3bf4' and x.get('workflow_run')==35389030840 and x.get('job_id')==105742841430 and x.get('artifact_id')==10565625878 and x.get('artifact_sha256')=='58b5bc72f81cdd26ea368cf810d1e1727fbdfc521203fe889bca005aa2f9aca8' and x.get('rootfs_sha256')=='445ce98267d53ec58a98bed3ee74343f04f2465bdccf258efa95e709551ff7b1' and x.get('result')=='FAIL' and x.get('stage')=='sbuild' and x.get('tests')=='44/44 PASS','Kirigami attempt-1 evidence mismatch')
blocked=a.get('blocked_events',{}).get('kquickcharts',[])
req(a.get('blocked_events',{}).get('kirigami')==[] and len(blocked)==1,'Batch 10 BLOCKED ledger mismatch')
if len(blocked)==1:
 x=blocked[0]
 req(x.get('validation_cycle')==1 and x.get('commit')=='67a6558513a82d4a1b4426a9b705eafdadbd3bf4' and x.get('workflow_run')==35389030840 and x.get('job_id')==105745672521 and x.get('artifact_id')==10565780756 and x.get('artifact_sha256')=='118afc6b702b4ec9fee050898fcbc381f5beaf2131013b619973c85e81f27ef8' and x.get('result')=='BLOCKED' and x.get('blocked_by')=='kirigami' and x.get('package_attempted') is False,'KQuickCharts BLOCKED evidence mismatch')
tier=js(ROOT/'manifests/kde-frameworks-tier1.json'); nodes={x['id']:x for x in tier['nodes']}
for node in ('kirigami','kquickcharts'): req(nodes[node].get('state')=='pending' and nodes[node].get('packaging',{}).get('state')=='pending',f'{node}: canonical state promoted prematurely')
runner=text(ROOT/'scripts/run-kde-tier1-package-batch10-preflight.sh'); scope=text(ROOT/'scripts/kde-tier1-package-batch10-needed.sh'); workflow=text(ROOT/'.github/workflows/kde-tier1-package-batch10.yml')
for token in ('reference_required_export_count_amd64','abi-reference-counts.txt','0supralinux','qmlimportscanner','KIRIGAMI_ARTIFACT_DIR','qml6-module-org-kde-kirigami','consumer-smoke','sbuild --verbose'):
 req(token in runner,f'Batch10 runner missing {token}')
req("grep -R -Eq 'QT_QML_NO_CACHEGEN=ON|BUILD_QCH=ON" not in runner,'Batch10 runner must not recursively scan documentation for behavior overrides')
req('dh_auto_test.*\\|\\|[[:space:]]*true' in runner,'Batch10 runner must explicitly guard test-command suppression')
req('packages/kde/${NODE}/*' in scope,'Batch10 selector must rebuild the selected node package tree')
req('packages/kde/kirigami/*' in scope,'Batch10 selector must propagate Kirigami package changes to KQuickCharts')
req('package_validation_dependencies' in json.dumps(c['nodes']['kquickcharts']),'Batch10 campaign must retain package-validation dependency metadata')
for token in ('needs: kirigami-package',"state':'BLOCKED",'Download current-run Kirigami PASS artifact','Download retained Kirigami PASS artifact','needs.kirigami-package.outputs.built'):
 req(token in workflow,f'Batch10 workflow missing {token}')
req('KF6::KirigamiPlatform' in text(ROOT/'packages/kde/kirigami/consumer/CMakeLists.txt'),'Kirigami official C++ target missing')
qc_cmake=text(ROOT/'packages/kde/kquickcharts/consumer/CMakeLists.txt'); qc_cpp=text(ROOT/'packages/kde/kquickcharts/consumer/main.cpp')
req('KF6::QuickCharts' in qc_cmake and 'KF6::QuickChartsControls' in qc_cmake and 'qml_register_types_org_kde_quickcharts' in qc_cpp and 'qml_register_types_org_kde_quickcharts_controls' in qc_cpp,'QuickCharts consumer contract incomplete')
router=text(ROOT/'.github/workflows/pr-ci-router.yml'); policy=text(ROOT/'.github/workflows/repository-policy.yml')
req('kde-tier1-package-batch10.yml' in router,'PR CI router missing Batch10 reusable workflow')
req('test-kde-tier1-package-batch10-scope.sh' in policy and 'validate_kde_tier1_package_batch10.py' in policy,'Repository Policy missing Batch10 checks')
g=js(ROOT/'manifests/kde-tier1-global-discovery.json'); lane=g['lanes']['qml-multisurface']
req(lane.get('status')=='implementation-ready' and lane.get('runner')=='scripts/run-kde-tier1-package-batch10-preflight.sh' and lane.get('workflow')=='.github/workflows/kde-tier1-package-batch10.yml','global discovery Batch10 lane not implementation-ready')
req(g['nodes']['kirigami'].get('readiness')=='runnable','Kirigami global readiness mismatch')
req(g['nodes']['kquickcharts'].get('readiness')=='package-validation-dependent','QuickCharts global readiness mismatch')
doc=text(ROOT/'docs/kde-tier1-package-batch10.md')
for token in ('25 PASS / 4 pending','DIAG_PASS','10464419377','10463808939','package_validation_dependency','BLOCKED','35389030840','10565625878','10565780756','44/44 PASS','optional=templinst','KF6::KirigamiPlatform','qml6-module-org-kde-kirigami'):
 req(token in doc,f'Batch10 documentation missing {token}')
if errors:
 print('\n'.join(f'ERROR: {e}' for e in errors),file=sys.stderr); raise SystemExit(1)
print('KDE Tier 1 Batch 10 remediation validation: PASS')
print('Nodes: kirigami remediation-pending-build; kquickcharts last-result BLOCKED and package-validation-dependent on Kirigami PASS')
print('Canonical state remains 25 PASS / 4 pending')
