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
req(c.get('state')=='implementation-ready-pending-build','Batch 10 state must remain pre-build')
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
for node,(source,sha,nbin,nabi,tests,job,artifact,digest) in expected.items():
 n=c['nodes'][node]; pkg=ROOT/'packages/kde'/node/'debian'; consumer=ROOT/'packages/kde'/node/'consumer'
 req(n.get('source_package')==source and n.get('source_sha256')==sha and n.get('package_version')=='6.30.0-0supralinux1',f'{node}: source/version mismatch')
 req(n.get('kde_framework_build_dependencies')==[],f'{node}: must remain Tier 1 at upstream build level')
 req(n.get('expected_test_count')==tests,f'{node}: expected test count mismatch')
 de=n.get('diagnostic_evidence',{}); req(de.get('workflow_run')==35138333645 and de.get('job_id')==job and de.get('artifact_id')==artifact and de.get('artifact_sha256')==digest and de.get('result')=='DIAG_PASS' and de.get('promotes_package_state') is False,f'{node}: DIAG evidence mismatch')
 req(len(n.get('binary_contracts',[]))==nbin and len(n.get('abi_contracts',[]))==nabi,f'{node}: binary/ABI count mismatch')
 for abi in n.get('abi_contracts',[]):
  exp=abi_expected[node].get(abi.get('surface')); req(exp is not None,f'{node}: unexpected ABI {abi.get("surface")}')
  if exp: req((abi.get('reference_export_count'),abi.get('reference_optional_export_count'),abi.get('reference_nonoptional_inapplicable_amd64_count'),abi.get('reference_required_export_count_amd64'))==exp,f'{node}/{abi.get("surface")}: ABI partition mismatch')
 req(n.get('state')=='prepared-pending-build' and n.get('last_result') is None and n.get('downstream_eligible') is False,f'{node}: premature package state')
 for f in ('control','rules','changelog','README.source','copyright.reference','run-tests-under-x.sh','source/format','upstream/signing-key.asc'): req((pkg/f).is_file(),f'{node}: missing debian/{f}')
 req((consumer/'CMakeLists.txt').is_file() and (consumer/'main.cpp').is_file(),f'{node}: consumer missing')
 control=text(pkg/'control'); rules=text(pkg/'rules')
 req('Maintainer: SupraLINUX Project <packages@supralinux.invalid>' in control and 'Rules-Requires-Root: no' in control,f'{node}: control ownership/root contract mismatch')
 req('extra-cmake-modules (>= 6.30.0~)' in control,f'{node}: ECM floor mismatch')
 req('-DBUILD_TESTING=ON' in rules and 'dbus-run-session -- xvfb-run' in rules,f'{node}: mandatory test fixture missing')
 req('BUILD_QCH=ON' not in rules and 'QT_QML_NO_CACHEGEN=ON' not in rules and '|| true' not in rules,f'{node}: forbidden downstream behavior override')
 req(not list(pkg.glob('*.symbols')) and not list(pkg.glob('*.symbols.reference')),f'{node}: retained symbols baseline must not be duplicated in git')
if c['nodes']['kirigami']['upstream_defaults']!={'BUILD_SHARED_LIBS':'ON','DESKTOP_ENABLED':'ON','BUILD_EXAMPLES':'OFF','UBUNTU_TOUCH':'OFF','USE_DBUS':'ON','BUILD_TESTING':'ON'}: errors.append('Kirigami upstream defaults mismatch')
if c['nodes']['kquickcharts']['upstream_defaults']!={'BUILD_SHARED_LIBS':'ON','BUILD_EXAMPLES':'OFF','BUILD_TESTING':'ON'}: errors.append('KQuickCharts upstream defaults mismatch')
kp=c['nodes']['kquickcharts'].get('package_validation_dependencies',[])
req(len(kp)==1 and kp[0].get('node')=='kirigami' and kp[0].get('kind')=='qml-runtime-closure' and kp[0].get('not_kde_framework_build_dependency') is True,'QuickCharts Kirigami package-validation dependency mismatch')
req(c['nodes']['kirigami'].get('package_validation_dependencies')==[],'Kirigami must have no package-validation predecessor')
req(a.get('attempts')=={'kirigami':[],'kquickcharts':[]} and a.get('validation_incidents')=={'kirigami':[],'kquickcharts':[]},'Batch 10 ledger must be empty before first real attempt')
tier=js(ROOT/'manifests/kde-frameworks-tier1.json'); nodes={x['id']:x for x in tier['nodes']}
for node in ('kirigami','kquickcharts'): req(nodes[node].get('state')=='pending' and nodes[node].get('packaging',{}).get('state')=='pending',f'{node}: canonical state promoted prematurely')
runner=text(ROOT/'scripts/run-kde-tier1-package-batch10-preflight.sh'); scope=text(ROOT/'scripts/kde-tier1-package-batch10-needed.sh'); workflow=text(ROOT/'.github/workflows/kde-tier1-package-batch10.yml')
for token in ('reference_required_export_count_amd64','abi-reference-counts.txt','0supralinux','qmlimportscanner','KIRIGAMI_ARTIFACT_DIR','qml6-module-org-kde-kirigami','consumer-smoke','sbuild --verbose'):
 req(token in runner,f'Batch10 runner missing {token}')
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
for token in ('25 PASS / 4 pending','DIAG_PASS','10464419377','10463808939','package_validation_dependency','BLOCKED','KF6::KirigamiPlatform','qml6-module-org-kde-kirigami'):
 req(token in doc,f'Batch10 documentation missing {token}')
if errors:
 print('\n'.join(f'ERROR: {e}' for e in errors),file=sys.stderr); raise SystemExit(1)
print('KDE Tier 1 Batch 10 preparation validation: PASS')
print('Nodes: kirigami runnable; kquickcharts package-validation-dependent on Kirigami PASS')
print('Canonical state remains 25 PASS / 4 pending')
