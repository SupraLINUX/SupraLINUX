#!/usr/bin/env python3
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[1]
errors=[]
def req(v,m):
 if not v: errors.append(m)
def text(p): return p.read_text(errors='replace')
def js(p): return json.loads(p.read_text())
def exact(seq,n,label):
 if not isinstance(seq,list):
  errors.append(f'{label}: expected list')
  return [{} for _ in range(n)]
 if len(seq)!=n:
  errors.append(f'{label}: expected {n}, got {len(seq)}')
 return (list(seq)+[{} for _ in range(n)])[:n]

C=ROOT/'manifests/kde-tier1-package-campaign-batch10.json'; A=ROOT/'manifests/kde-tier1-package-batch10-attempts.json'
req(C.is_file(),'Batch 10 campaign missing'); req(A.is_file(),'Batch 10 attempts ledger missing')
if not C.is_file() or not A.is_file():
 print('\n'.join(errors),file=sys.stderr); raise SystemExit(1)
c=js(C); a=js(A)
req(c.get('schema')==2 and c.get('batch')=='tier1-batch-10' and c.get('lane')=='qml-multisurface','Batch 10 identity mismatch')
req(c.get('frameworks_series')=='6.30.0' and c.get('authority')=='kde-upstream' and c.get('provider_platform')=='ubuntu-resolute','authority/provider mismatch')
req(c.get('state')=='PASS','Batch 10 campaign technical closure must be PASS before canonical promotion')
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
versions={'kirigami':'6.30.0-0supralinux2','kquickcharts':'6.30.0-0supralinux4'}
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
 req(n.get('downstream_eligible') is True,f'{node}: retained campaign PASS must be downstream-eligible')
 for f in ('control','rules','changelog','README.source','copyright.reference','run-tests-under-x.sh','source/format','upstream/signing-key.asc'): req((pkg/f).is_file(),f'{node}: missing debian/{f}')
 req((consumer/'CMakeLists.txt').is_file() and (consumer/'main.cpp').is_file(),f'{node}: consumer missing')
 control=text(pkg/'control'); rules=text(pkg/'rules')
 req('Maintainer: SupraLINUX Project <packages@supralinux.invalid>' in control and 'Rules-Requires-Root: no' in control,f'{node}: control ownership/root contract mismatch')
 req('extra-cmake-modules (>= 6.30.0~)' in control,f'{node}: ECM floor mismatch')
 req('-DBUILD_TESTING=ON' in rules and 'dbus-run-session -- xvfb-run' in rules,f'{node}: mandatory test fixture missing')
 req('BUILD_QCH=ON' not in rules and 'QT_QML_NO_CACHEGEN=ON' not in rules and '|| true' not in rules,f'{node}: forbidden downstream behavior override')
 req(not list(pkg.glob('*.symbols')) and not list(pkg.glob('*.symbols.reference')),f'{node}: retained symbols baseline must not be duplicated in git')
kir=c['nodes']['kirigami']; quick=c['nodes']['kquickcharts']
req(kir.get('state')=='PASS' and kir.get('last_result')=='PASS' and kir.get('downstream_eligible') is True,'Kirigami retained PASS state mismatch')
req(quick.get('state')=='PASS' and quick.get('last_result')=='PASS' and quick.get('downstream_eligible') is True,'KQuickCharts retained PASS state mismatch')
lf=kir.get('last_failure_evidence',{})
req(lf.get('workflow_run')==35389030840 and lf.get('job_id')==105742841430 and lf.get('artifact_id')==10565625878 and lf.get('artifact_sha256')=='58b5bc72f81cdd26ea368cf810d1e1727fbdfc521203fe889bca005aa2f9aca8' and lf.get('rootfs_sha256')=='445ce98267d53ec58a98bed3ee74343f04f2465bdccf258efa95e709551ff7b1' and lf.get('tests')=='44/44 PASS' and lf.get('stage')=='sbuild','Kirigami failure evidence mismatch')
lb=quick.get('last_blocked_evidence',{})
req(lb.get('validation_cycle')==2 and lb.get('workflow_run')==35392233659 and lb.get('job_id')==105755393521 and lb.get('artifact_id')==10566446188 and lb.get('artifact_sha256')=='23e45810ba579c997a6c6c3ab46e34d53fd8f2360713cc8f38dae353ea7f8e3d' and lb.get('blocked_by')=='kirigami' and lb.get('package_attempted') is False,'KQuickCharts latest BLOCKED evidence mismatch')
vi=kir.get('last_validation_incident',{})
req(vi.get('validation_cycle')==2 and vi.get('workflow_run')==35392233659 and vi.get('job_id')==105753009458 and vi.get('artifact_id')==10565524699 and vi.get('artifact_sha256')=='b5676f429fcc10d57676e8d489ab651e5aadafffebbaccd6febf7c97cad3c3f5' and vi.get('rootfs_sha256')=='93928deec54c2410944410c4bb52eaab8b70723fea50271f51aa3cc0b70d8384' and vi.get('classification')=='INFRA' and vi.get('package_state_effect')=='none' and vi.get('symbols_remediation')=='PASS','Kirigami latest validation incident mismatch')
kp=kir.get('pass_evidence',{})
req(kp.get('validation_cycle')==3 and kp.get('workflow_run')==35398956698 and kp.get('job_id')==105774229788 and kp.get('artifact_id')==10569258322 and kp.get('artifact_sha256')=='6a008366edda84f8c285e5cf0a6b18a4b1089fc88e530d6e61b0f4f885dd7e30' and kp.get('rootfs_sha256')=='8a1e3d09d8788ad38c81cb7071f7149c114f3582ee3c59d489114c3b81497a35' and kp.get('tests')=='44/44 PASS' and kp.get('lintian')=='PASS-errors' and kp.get('apt_check')=='PASS' and kp.get('qml_import_smoke')=='PASS' and kp.get('consumer_smoke')=='PASS','Kirigami retained PASS evidence mismatch')
qf=quick.get('last_failure_evidence',{})
req(qf.get('validation_cycle')==7 and qf.get('workflow_run')==35406143858 and qf.get('job_id')==105797738652 and qf.get('artifact_id')==10572841006 and qf.get('artifact_sha256')=='87c84de4c44bcf7bf6dfad958e85ea755dd34ae014dd85508c250e596b4b4563' and qf.get('rootfs_sha256')=='bc109e0dd164e30611fa519db43aef659eba2346b1a3f3a1b8e5ce61a3aead92' and qf.get('tests')=='8/8 PASS' and qf.get('lintian')=='PASS-errors' and qf.get('dh_qmldeps')=='PASS' and qf.get('abi_contract')=='PASS' and qf.get('apt_check')=='PASS' and qf.get('qml_import_smoke')=='PASS' and qf.get('stage')=='consumer-smoke' and qf.get('kirigami_predecessor_version')=='6.30.0-0supralinux2' and qf.get('cause')=='libquickcharts-dev-missing-exported-ECM-development-dependency','KQuickCharts attempt-3 failure evidence mismatch')
qvi=quick.get('last_validation_incident',{})
req(qvi.get('validation_cycle')==8 and qvi.get('workflow_run')==35407208676 and qvi.get('job_id')==105800564563 and qvi.get('artifact_id')==10573097334 and qvi.get('artifact_sha256')=='e3a40dbc16fe346de109582dcec98ec5e2818f005288d2c7fbcedbfea4ada7da' and qvi.get('rootfs_sha256')=='db1fd86f47064825deb19738d30b339cb0032529be210e978a907fed2a5fc538' and qvi.get('classification')=='INFRA' and qvi.get('package_state_effect')=='none' and qvi.get('stage')=='consumer-smoke' and qvi.get('package_build')=='successful' and qvi.get('tests')=='8/8 PASS' and qvi.get('lintian')=='PASS-errors' and qvi.get('dh_qmldeps')=='PASS' and qvi.get('abi_contract')=='PASS' and qvi.get('apt_check')=='PASS' and qvi.get('qml_import_smoke')=='PASS' and qvi.get('kirigami_predecessor_version')=='6.30.0-0supralinux2' and qvi.get('ecm_predecessor_version')=='6.30.0-0supralinux3' and qvi.get('upstream_exported_cmake_targets')==['KF6::QuickCharts'] and qvi.get('cause')=='consumer-harness-required-nonexported-QuickChartsControls-CMake-target','KQuickCharts validation-cycle-8 infrastructure evidence mismatch')
qp=quick.get('pass_evidence',{})
req(qp.get('validation_cycle')==9 and qp.get('workflow_run')==35409521636 and qp.get('job_id')==105806202814 and qp.get('artifact_id')==10573605864 and qp.get('artifact_sha256')=='dc233607ea647780580405b49e8b12855af5aaaf3b2d2bfea50c75fe7ed91780' and qp.get('rootfs_sha256')=='b1e79e0fbc11672c017acc812efa74116f1681a56596deb87f0f770b47e3d01d' and qp.get('tests')=='8/8 PASS' and qp.get('lintian')=='PASS-errors' and qp.get('dh_qmldeps')=='PASS' and qp.get('abi_contract')=='PASS' and qp.get('apt_check')=='PASS' and qp.get('qml_import_smoke')=='PASS' and qp.get('consumer_smoke')=='PASS' and qp.get('kirigami_predecessor_version')=='6.30.0-0supralinux2' and qp.get('ecm_predecessor_version')=='6.30.0-0supralinux3' and qp.get('abi_exports')=={'QuickCharts':381,'QuickChartsControls':1},'KQuickCharts retained PASS evidence mismatch')
qrem=quick.get('symbols_remediation',{})
req(qrem.get('policy')=='optional=templinst|arch=!riscv64' and qrem.get('symbols_file')=='libquickcharts1.symbols' and qrem.get('baseline_sha256')=='ed06cd19136bc5a1bfb10fb7e5c93070fdb4f76ca81f8536243666297e8193e6' and qrem.get('result_sha256')=='f1ba9c4d179d7dc3638f82fe5879c6ecea43455f520eff686aad508c4e32702e' and qrem.get('changed_symbols')==2 and qrem.get('minimum_version')=='6.0.0','KQuickCharts symbols-remediation metadata mismatch')
qabi={x.get('surface'):x for x in quick.get('abi_contracts',[])}
req(qabi.get('QuickCharts',{}).get('reference_required_export_count_amd64')==382 and qabi.get('QuickCharts',{}).get('effective_required_export_count_amd64')==380,'KQuickCharts effective ABI floor mismatch')
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
quick_pkg=ROOT/'packages/kde/kquickcharts/debian'; qdelta=quick_pkg/'apply-symbols-delta.py'
req(qdelta.is_file(),'KQuickCharts symbols-delta helper missing')
qdelta_txt=text(qdelta); quick_control=text(quick_pkg/'control'); quick_rules=text(quick_pkg/'rules')
for token in ('ed06cd19136bc5a1bfb10fb7e5c93070fdb4f76ca81f8536243666297e8193e6','f1ba9c4d179d7dc3638f82fe5879c6ecea43455f520eff686aad508c4e32702e','optional=templinst|arch=!riscv64','_ZTISt15_Sp_counted_ptrIP10QQuickItem','_ZTVSt15_Sp_counted_ptrIP10QQuickItem'):
 req(token in qdelta_txt,f'KQuickCharts symbols-delta helper missing {token}')
req('python3:any' in quick_control,'KQuickCharts delta helper requires python3:any Build-Depends')
req('qml6-module-org-kde-kirigami (>= 6.30.0~)' in quick_control,'KQuickCharts dh_qmldeps requires retained Kirigami QML package in Build-Depends')
req('libkirigami-dev' not in quick_control,'KQuickCharts must not gain a Kirigami Framework development Build-Depends')
quick_dev=quick_control.split('Package: libquickcharts-dev',1)[1].split('\nPackage:',1)[0]
req('extra-cmake-modules (>= 6.30.0~)' in quick_dev,'KQuickCharts development package must carry exported ECM 6.30 dependency')
req('override_dh_makeshlibs:' in quick_rules and 'python3 debian/apply-symbols-delta.py' in quick_rules,'KQuickCharts rules do not apply reviewed symbols delta before dh_makeshlibs')
if c['nodes']['kirigami']['upstream_defaults']!={'BUILD_SHARED_LIBS':'ON','DESKTOP_ENABLED':'ON','BUILD_EXAMPLES':'OFF','UBUNTU_TOUCH':'OFF','USE_DBUS':'ON','BUILD_TESTING':'ON'}: errors.append('Kirigami upstream defaults mismatch')
if c['nodes']['kquickcharts']['upstream_defaults']!={'BUILD_SHARED_LIBS':'ON','BUILD_EXAMPLES':'OFF','BUILD_TESTING':'ON'}: errors.append('KQuickCharts upstream defaults mismatch')
kp=c['nodes']['kquickcharts'].get('package_validation_dependencies',[])
req(len(kp)==1 and kp[0].get('node')=='kirigami' and kp[0].get('kind')=='qml-runtime-closure' and kp[0].get('not_kde_framework_build_dependency') is True and kp[0].get('required_during_dh_qmldeps') is True and kp[0].get('dependency_class')=='debian-packaging-qml-metadata' and kp[0].get('state')=='retained-PASS-available','QuickCharts Kirigami package-validation dependency mismatch')
req(c['nodes']['kirigami'].get('package_validation_dependencies')==[],'Kirigami must have no package-validation predecessor')
inc=exact(a.get('validation_incidents',{}).get('kirigami',[]),1,'Kirigami validation-incident ledger')
qinc=exact(a.get('validation_incidents',{}).get('kquickcharts',[]),3,'KQuickCharts validation-incident ledger')
x=inc[0]
req(x.get('validation_cycle')==2 and x.get('package_version')=='6.30.0-0supralinux2' and x.get('commit')=='b6adeee8259414fe6711b3b7143f735330a42f6a' and x.get('workflow_run')==35392233659 and x.get('job_id')==105753009458 and x.get('artifact_id')==10565524699 and x.get('artifact_sha256')=='b5676f429fcc10d57676e8d489ab651e5aadafffebbaccd6febf7c97cad3c3f5' and x.get('rootfs_sha256')=='93928deec54c2410944410c4bb52eaab8b70723fea50271f51aa3cc0b70d8384' and x.get('classification')=='INFRA' and x.get('package_state_effect')=='none' and x.get('stage')=='consumer-smoke' and x.get('tests')=='44/44 PASS' and x.get('lintian')=='PASS-errors' and x.get('symbols_remediation')=='PASS','Kirigami validation-cycle-2 infrastructure evidence mismatch')
x=qinc[0]
req(x.get('validation_cycle')==5 and x.get('package_version')=='6.30.0-0supralinux3' and x.get('commit')=='90b6a7536efc224a9e45999524485df5e2f3ca1c' and x.get('workflow_run')==35403143944 and x.get('job_id')==105787263585 and x.get('artifact_id')==10570704785 and x.get('artifact_sha256')=='7ddc766a2664c0af20fd7e265afc396ad5a0e210bc101bf151272c5ff0ff799a' and x.get('rootfs_sha256')=='b6f02804169e2347e6c4e11adfbd799887c02e238961ad5e0be76fa621644720' and x.get('classification')=='INFRA' and x.get('package_state_effect')=='none' and x.get('stage')=='abi-contract' and x.get('package_build')=='successful' and x.get('tests')=='8/8 PASS' and x.get('lintian')=='PASS-errors' and x.get('dh_qmldeps')=='PASS' and x.get('symbols_remediation')=='PASS','KQuickCharts validation-cycle-5 infrastructure evidence mismatch')
x=qinc[1]
req(x.get('validation_cycle')==6 and x.get('package_version')=='6.30.0-0supralinux3' and x.get('commit')=='c2b25ba797d20e9963af8823bb023436d7a2ef34' and x.get('workflow_run')==35403658149 and x.get('job_id')==105790735337 and x.get('artifact_id')==10570804457 and x.get('artifact_sha256')=='8ba90bdf3514dc89e1d5ffac82c285ed089d9b8e038dee3c3cddf676b9f519f6' and x.get('rootfs_sha256')=='7b207b2d11d7fbbba430714ac49b8216a7d8c738d1e88a7a456b31fbe38e6b9d' and x.get('classification')=='INFRA' and x.get('package_state_effect')=='none' and x.get('stage')=='abi-contract' and x.get('package_build')=='successful' and x.get('tests')=='8/8 PASS' and x.get('lintian')=='PASS-errors' and x.get('dh_qmldeps')=='PASS' and x.get('symbols_remediation')=='PASS' and x.get('generated_exports')==381 and x.get('reference_required_export_count_amd64')==382 and x.get('effective_required_export_count_amd64')==380,'KQuickCharts validation-cycle-6 infrastructure evidence mismatch')
x=qinc[2]
req(x.get('validation_cycle')==8 and x.get('package_version')=='6.30.0-0supralinux4' and x.get('commit')=='2694b415c0785418692223d6f7564c825f97eddd' and x.get('workflow_run')==35407208676 and x.get('job_id')==105800564563 and x.get('artifact_id')==10573097334 and x.get('artifact_sha256')=='e3a40dbc16fe346de109582dcec98ec5e2818f005288d2c7fbcedbfea4ada7da' and x.get('rootfs_sha256')=='db1fd86f47064825deb19738d30b339cb0032529be210e978a907fed2a5fc538' and x.get('classification')=='INFRA' and x.get('package_state_effect')=='none' and x.get('stage')=='consumer-smoke' and x.get('package_build')=='successful' and x.get('tests')=='8/8 PASS' and x.get('lintian')=='PASS-errors' and x.get('dh_qmldeps')=='PASS' and x.get('abi_contract')=='PASS' and x.get('apt_check')=='PASS' and x.get('qml_import_smoke')=='PASS' and x.get('kirigami_predecessor_version')=='6.30.0-0supralinux2' and x.get('ecm_predecessor_version')=='6.30.0-0supralinux3' and x.get('upstream_exported_cmake_targets')==['KF6::QuickCharts'],'KQuickCharts validation-cycle-8 infrastructure evidence mismatch')
ka=exact(a.get('attempts',{}).get('kirigami',[]),2,'Kirigami real-attempt ledger')
qa=exact(a.get('attempts',{}).get('kquickcharts',[]),4,'KQuickCharts real-attempt ledger')
x=ka[0]
req(x.get('attempt')==1 and x.get('package_version')=='6.30.0-0supralinux1' and x.get('commit')=='67a6558513a82d4a1b4426a9b705eafdadbd3bf4' and x.get('workflow_run')==35389030840 and x.get('job_id')==105742841430 and x.get('artifact_id')==10565625878 and x.get('artifact_sha256')=='58b5bc72f81cdd26ea368cf810d1e1727fbdfc521203fe889bca005aa2f9aca8' and x.get('rootfs_sha256')=='445ce98267d53ec58a98bed3ee74343f04f2465bdccf258efa95e709551ff7b1' and x.get('result')=='FAIL' and x.get('stage')=='sbuild' and x.get('tests')=='44/44 PASS','Kirigami attempt-1 evidence mismatch')
x=ka[1]
req(x.get('attempt')==2 and x.get('validation_cycle')==3 and x.get('package_version')=='6.30.0-0supralinux2' and x.get('commit')=='25af7164a76a925f27814aabe1986727a53d49bf' and x.get('workflow_run')==35398956698 and x.get('job_id')==105774229788 and x.get('artifact_id')==10569258322 and x.get('artifact_sha256')=='6a008366edda84f8c285e5cf0a6b18a4b1089fc88e530d6e61b0f4f885dd7e30' and x.get('rootfs_sha256')=='8a1e3d09d8788ad38c81cb7071f7149c114f3582ee3c59d489114c3b81497a35' and x.get('result')=='PASS' and x.get('stage')=='complete' and x.get('tests')=='44/44 PASS' and x.get('downstream_eligible') is True,'Kirigami attempt-2 PASS evidence mismatch')
x=qa[0]
req(x.get('attempt')==1 and x.get('validation_cycle')==3 and x.get('package_version')=='6.30.0-0supralinux1' and x.get('commit')=='25af7164a76a925f27814aabe1986727a53d49bf' and x.get('workflow_run')==35398956698 and x.get('job_id')==105776448807 and x.get('artifact_id')==10570203712 and x.get('artifact_sha256')=='1f4a4a65e3e534d000b0507ff583f8ef657eb5836d0db840ef405d5ab501f12e' and x.get('rootfs_sha256')=='7da69856573c2d320f7e8a345d53fff793c39e0e8fe1e0e144bed73fcf3765d2' and x.get('result')=='FAIL' and x.get('stage')=='sbuild' and x.get('tests')=='8/8 PASS' and x.get('kirigami_predecessor_version')=='6.30.0-0supralinux2','KQuickCharts attempt-1 evidence mismatch')
x=qa[1]
req(x.get('attempt')==2 and x.get('validation_cycle')==4 and x.get('package_version')=='6.30.0-0supralinux2' and x.get('commit')=='ecf2e73ff7bc65e0deb321974cec35fcb8190250' and x.get('workflow_run')==35400585402 and x.get('job_id')==105779442087 and x.get('artifact_id')==10570720119 and x.get('artifact_sha256')=='edbcef8faf5801ae9a5c95b59270f7726a2abbbc1a5268d994816bf731eb7066' and x.get('rootfs_sha256')=='413b2fabd4248a9a11a4ec47792873c4c730a9c8c4aa15336f73be4acc79bec8' and x.get('result')=='FAIL' and x.get('stage')=='sbuild' and x.get('tests')=='8/8 PASS' and x.get('kirigami_predecessor_version')=='6.30.0-0supralinux2' and x.get('symbols_remediation')=='PASS','KQuickCharts attempt-2 evidence mismatch')
x=qa[2]
req(x.get('attempt')==3 and x.get('validation_cycle')==7 and x.get('package_version')=='6.30.0-0supralinux3' and x.get('commit')=='bf3b3f856ef8844707bcaedba475a8fadafb46fe' and x.get('workflow_run')==35406143858 and x.get('job_id')==105797738652 and x.get('artifact_id')==10572841006 and x.get('artifact_sha256')=='87c84de4c44bcf7bf6dfad958e85ea755dd34ae014dd85508c250e596b4b4563' and x.get('rootfs_sha256')=='bc109e0dd164e30611fa519db43aef659eba2346b1a3f3a1b8e5ce61a3aead92' and x.get('result')=='FAIL' and x.get('stage')=='consumer-smoke' and x.get('tests')=='8/8 PASS' and x.get('lintian')=='PASS-errors' and x.get('dh_qmldeps')=='PASS' and x.get('abi_contract')=='PASS' and x.get('apt_check')=='PASS' and x.get('qml_import_smoke')=='PASS' and x.get('kirigami_predecessor_version')=='6.30.0-0supralinux2','KQuickCharts attempt-3 evidence mismatch')
x=qa[3]
req(x.get('attempt')==4 and x.get('validation_cycle')==9 and x.get('package_version')=='6.30.0-0supralinux4' and x.get('commit')=='43adf80f4a16a848f1ca7ea77fc608585ddb6345' and x.get('workflow_run')==35409521636 and x.get('job_id')==105806202814 and x.get('artifact_id')==10573605864 and x.get('artifact_sha256')=='dc233607ea647780580405b49e8b12855af5aaaf3b2d2bfea50c75fe7ed91780' and x.get('rootfs_sha256')=='b1e79e0fbc11672c017acc812efa74116f1681a56596deb87f0f770b47e3d01d' and x.get('result')=='PASS' and x.get('stage')=='complete' and x.get('tests')=='8/8 PASS' and x.get('lintian')=='PASS-errors' and x.get('dh_qmldeps')=='PASS' and x.get('abi_contract')=='PASS' and x.get('apt_check')=='PASS' and x.get('qml_import_smoke')=='PASS' and x.get('consumer_smoke')=='PASS' and x.get('kirigami_predecessor_version')=='6.30.0-0supralinux2' and x.get('ecm_predecessor_version')=='6.30.0-0supralinux3' and x.get('downstream_eligible') is True,'KQuickCharts attempt-4 PASS evidence mismatch')
req(a.get('blocked_events',{}).get('kirigami')==[],'Kirigami BLOCKED ledger must stay empty')
blocked=exact(a.get('blocked_events',{}).get('kquickcharts',[]),2,'KQuickCharts BLOCKED ledger')
x=blocked[0]
req(x.get('validation_cycle')==1 and x.get('commit')=='67a6558513a82d4a1b4426a9b705eafdadbd3bf4' and x.get('workflow_run')==35389030840 and x.get('job_id')==105745672521 and x.get('artifact_id')==10565780756 and x.get('artifact_sha256')=='118afc6b702b4ec9fee050898fcbc381f5beaf2131013b619973c85e81f27ef8' and x.get('result')=='BLOCKED' and x.get('blocked_by')=='kirigami' and x.get('package_attempted') is False,'KQuickCharts cycle-1 BLOCKED evidence mismatch')
x=blocked[1]
req(x.get('validation_cycle')==2 and x.get('commit')=='b6adeee8259414fe6711b3b7143f735330a42f6a' and x.get('workflow_run')==35392233659 and x.get('job_id')==105755393521 and x.get('artifact_id')==10566446188 and x.get('artifact_sha256')=='23e45810ba579c997a6c6c3ab46e34d53fd8f2360713cc8f38dae353ea7f8e3d' and x.get('result')=='BLOCKED' and x.get('blocked_by')=='kirigami' and x.get('package_attempted') is False,'KQuickCharts cycle-2 BLOCKED evidence mismatch')
tier=js(ROOT/'manifests/kde-frameworks-tier1.json'); nodes={x['id']:x for x in tier['nodes']}
ce=c.get('closure_evidence',{})
rp=ce.get('repository_policy',{}); pc=ce.get('pr_ci',{}); ss=ce.get('scope_skips',{}).get('kirigami',{})
req(rp.get('workflow_run')==35409521508 and rp.get('job_id')==105806142849 and rp.get('result')=='PASS','Batch 10 closure Repository Policy evidence mismatch')
req(pc.get('workflow_run')==35409521636 and pc.get('commit')=='43adf80f4a16a848f1ca7ea77fc608585ddb6345' and pc.get('result')=='PASS','Batch 10 closure PR CI evidence mismatch')
req(ss.get('job_id')==105806169640 and ss.get('result')=='scope-skipped-retained-PASS','Batch 10 Kirigami closure scope-skip evidence mismatch')
rv=c.get('ci_acceleration_revalidation',{})
req(rv.get('commit')=='43e729ff573b15ac5dd97e50ecca6656f2b50576' and rv.get('classification')=='infrastructure-revalidation' and rv.get('counts_as_package_attempt') is False and rv.get('package_state_effect')=='none','Batch 10 CI acceleration revalidation identity mismatch')
req(rv.get('repository_policy',{}).get('workflow_run')==35414683680 and rv.get('repository_policy',{}).get('job_id')==105820857530 and rv.get('repository_policy',{}).get('result')=='PASS','Batch 10 CI acceleration Repository Policy evidence mismatch')
req(rv.get('pr_ci',{}).get('workflow_run')==35414683979 and rv.get('pr_ci',{}).get('result')=='PASS','Batch 10 CI acceleration PR CI evidence mismatch')
rkn=rv.get('nodes',{}).get('kirigami',{}); rqn=rv.get('nodes',{}).get('kquickcharts',{})
req(rkn.get('job_id')==105820877778 and rkn.get('artifact_id')==10574863862 and rkn.get('artifact_sha256')=='712a4a0edeb388d510c93b1d20346282066063b2328e6b6bbd8b57784e5e8c93' and rkn.get('source_contract_audit')=='PASS' and rkn.get('artifact_contract_audit')=='PASS','Kirigami contract-audit revalidation evidence mismatch')
req(rqn.get('job_id')==105822092851 and rqn.get('artifact_id')==10575119063 and rqn.get('artifact_sha256')=='63c9fdb60e2427a9437788b4f34d8757a5ff98e4f695a9b0c8042d55dbd2bfdd' and rqn.get('source_contract_audit')=='PASS' and rqn.get('artifact_contract_audit')=='PASS','KQuickCharts contract-audit revalidation evidence mismatch')
for node in ('kirigami','kquickcharts'):
 can=nodes[node]; pkgcan=can.get('packaging',{}); camp=c['nodes'][node]; pe=camp.get('pass_evidence',{})
 req(can.get('state')=='PASS' and pkgcan.get('state')=='PASS',f'{node}: canonical state must be promoted PASS')
 req(pkgcan.get('package_version')==camp.get('package_version') and pkgcan.get('downstream_eligible') is True and pkgcan.get('attempt_ledger')=='manifests/kde-tier1-package-batch10-attempts.json',f'{node}: canonical packaging promotion mismatch')
 req(pkgcan.get('claim')=='hosted-clean-package-preflight' and pkgcan.get('authoritative') is False,f'{node}: canonical hosted PASS claim mismatch')
 canon_passes=[x for x in pkgcan.get('evidence',[]) if isinstance(x,dict) and x.get('result')=='PASS']
 req(len(canon_passes)==1,f'{node}: canonical promotion must retain exactly one current PASS')
 if canon_passes:
  cp=canon_passes[0]
  req(cp.get('workflow_run')==pe.get('workflow_run') and cp.get('job_id')==pe.get('job_id') and cp.get('artifact_id')==pe.get('artifact_id') and cp.get('artifact_sha256')==pe.get('artifact_sha256') and cp.get('tests')==pe.get('tests'),f'{node}: canonical retained PASS evidence mismatch')
  req(cp.get('lintian')=='PASS-errors' and cp.get('consumer_smoke')=='PASS' and cp.get('apt_check')=='PASS' and cp.get('qml_import_smoke')=='PASS',f'{node}: canonical PASS gates mismatch')
  req(cp.get('abi_sonames')==[a['soname'] for a in camp.get('abi_contracts',[])],f'{node}: canonical ABI SONAME evidence mismatch')
  req(cp.get('ecm_predecessor')=='6.30.0-0supralinux3',f'{node}: canonical ECM predecessor mismatch')
  req(isinstance(cp.get('files'),dict) and cp.get('files') and cp.get('files',{}).get('rootfs_sha256')==pe.get('rootfs_sha256'),f'{node}: canonical retained file/rootfs hashes missing')
req(c.get('canonical_promotion')=={'status':'promoted','tier1':'27 PASS / 2 pending / 0 current FAIL / 0 BLOCKED','dag_nodes':['kirigami','kquickcharts']},'Batch 10 canonical promotion snapshot mismatch')
pre=c.get('promotion_precheck',{})
req(pre.get('repository_policy',{}).get('workflow_run')==35440818501 and pre.get('repository_policy',{}).get('job_id')==105891164984 and pre.get('repository_policy',{}).get('result')=='PASS','Batch 10 promotion precheck Repository Policy mismatch')
req(pre.get('pr_ci',{}).get('workflow_run')==35440818686 and pre.get('pr_ci',{}).get('commit')=='9051539d50e5a2ada41a6975add6c5a6497e6b3e' and pre.get('pr_ci',{}).get('result')=='PASS','Batch 10 promotion precheck PR CI mismatch')
incidents=c.get('promotion_validation_incidents',[])
req(len(incidents)==1,'Batch 10 promotion validation incident ledger mismatch')
if len(incidents)==1:
 inc=incidents[0]
 req(inc.get('workflow_run')==35472599190 and inc.get('job_id')==105976179351 and inc.get('commit')=='3c7be6b7b3ea5853c483333f8c1b0fed25120413','Batch 10 promotion validation incident identity mismatch')
 req(inc.get('classification')=='INFRA' and inc.get('package_state_effect')=='none' and inc.get('package_attempted') is False,'Batch 10 promotion validation incident semantics mismatch')
 req(inc.get('cause')=='validator-exact-dict-rejected-preserved-promoted-snapshot-note','Batch 10 promotion validation incident cause mismatch')
prv=pre.get('revalidation',{})
req(prv.get('classification')=='infrastructure-revalidation' and prv.get('counts_as_package_attempt') is False and prv.get('package_state_effect')=='none','Batch 10 promotion revalidation semantics mismatch')
req(prv.get('nodes',{}).get('kirigami',{}).get('job_id')==105891183786 and prv.get('nodes',{}).get('kirigami',{}).get('artifact_id')==10583642308 and prv.get('nodes',{}).get('kirigami',{}).get('artifact_sha256')=='a3fa47927d42dd605f78b4dc4913025311eed88ea807249da0b29653bd7ac0cb','Batch 10 promotion Kirigami revalidation mismatch')
req(prv.get('nodes',{}).get('kquickcharts',{}).get('job_id')==105892252854 and prv.get('nodes',{}).get('kquickcharts',{}).get('artifact_id')==10583429116 and prv.get('nodes',{}).get('kquickcharts',{}).get('artifact_sha256')=='13a7d0ac50f03b9471305fd3b7f056ffaa5e0640a6332ed228bde2c087b87180','Batch 10 promotion KQuickCharts revalidation mismatch')
runner=text(ROOT/'scripts/run-kde-tier1-package-batch10-preflight.sh'); scope=text(ROOT/'scripts/kde-tier1-package-batch10-needed.sh'); workflow=text(ROOT/'.github/workflows/kde-tier1-package-batch10.yml'); audit=ROOT/'scripts/audit-kde-development-contract.py'
req(audit.is_file(),'KDE development contract audit helper missing')
audit_txt=text(audit)
for token in ('find_dependency','*Targets.cmake','required_during_dh_qmldeps','known_provider_checks','packaged_cmake_targets','required_qml_modules'):
 req(token in audit_txt,f'KDE development contract audit missing {token}')
req("rglob(abi['soname'])" in runner and "rglob(abi['soname']+'.*')" not in runner,'Batch 10 ABI harness must resolve the exact packaged SONAME payload')
req("abi.get('effective_required_export_count_amd64',abi['reference_required_export_count_amd64'])" in runner,'Batch 10 ABI harness must honor reviewed effective required-export floors')
req('INSTALL_DEBS+=("${KIRIGAMI_DEBS[@]}" "${ECM_DEB}")' in runner,'KQuickCharts consumer closure must install retained ECM with local packages')
req('QuickCharts resolved non-SupraLINUX ECM development provider' in runner and "dpkg-query -W -f='${Version}' extra-cmake-modules" in runner,'KQuickCharts consumer closure must verify exact retained ECM provider')
for token in ('reference_required_export_count_amd64','abi-reference-counts.txt','0supralinux','qmlimportscanner','KIRIGAMI_ARTIFACT_DIR','qml6-module-org-kde-kirigami','source-development-contract','development-contract','audit-kde-development-contract.py','consumer-smoke','sbuild --verbose'):
 req(token in runner,f'Batch10 runner missing {token}')
req("grep -R -Eq 'QT_QML_NO_CACHEGEN=ON|BUILD_QCH=ON" not in runner,'Batch10 runner must not recursively scan documentation for behavior overrides')
req('dh_auto_test.*\\|\\|[[:space:]]*true' in runner,'Batch10 runner must explicitly guard test-command suppression')
req('packages/kde/${NODE}/*' in scope,'Batch10 selector must rebuild the selected node package tree')
req('packages/kde/kirigami/*' in scope,'Batch10 selector must propagate Kirigami package changes to KQuickCharts')
req('scripts/audit-kde-development-contract.py' in scope,'Batch10 selector must revalidate nodes when the shared development-contract audit changes')
req('last_validation_incident' in scope and 'last_blocked_evidence' in scope,'Batch10 selector must ignore historical validation/BLOCKED result evidence')
req('package_validation_dependencies' in json.dumps(c['nodes']['kquickcharts']),'Batch10 campaign must retain package-validation dependency metadata')
for token in ('needs: kirigami-package',"state':'BLOCKED",'Download current-run Kirigami PASS artifact','Download retained Kirigami PASS artifact','needs.kirigami-package.outputs.built'):
 req(token in workflow,f'Batch10 workflow missing {token}')
kir_consumer=text(ROOT/'packages/kde/kirigami/consumer/CMakeLists.txt')
req('find_package(KF6KirigamiPlatform 6.30 REQUIRED CONFIG)' in kir_consumer and 'KF6::KirigamiPlatform' in kir_consumer,'Kirigami consumer must use the installed KF6KirigamiPlatform package config and official target')
req('find_package(KF6 6.30' not in kir_consumer,'Kirigami consumer must not request nonexistent KF6 umbrella config')
qc_cmake=text(ROOT/'packages/kde/kquickcharts/consumer/CMakeLists.txt'); qc_cpp=text(ROOT/'packages/kde/kquickcharts/consumer/main.cpp')
req('find_package(KF6QuickCharts 6.30 REQUIRED CONFIG)' in qc_cmake and 'KF6::QuickCharts' in qc_cmake and 'KF6::QuickChartsControls' not in qc_cmake and 'qml_register_types_org_kde_quickcharts' in qc_cpp and 'qml_register_types_org_kde_quickcharts_controls' not in qc_cpp,'QuickCharts consumer must use only the upstream-exported KF6::QuickCharts target; controls remain QML/runtime validated')
router=text(ROOT/'.github/workflows/pr-ci-router.yml'); policy=text(ROOT/'.github/workflows/repository-policy.yml')
req('kde-tier1-package-batch10.yml' in router,'PR CI router missing Batch10 reusable workflow')
req('test-kde-tier1-package-batch10-scope.sh' in policy and 'validate_kde_tier1_package_batch10.py' in policy,'Repository Policy missing Batch10 checks')
g=js(ROOT/'manifests/kde-tier1-global-discovery.json'); lane=g['lanes']['qml-multisurface']
req(lane.get('status')=='completed' and lane.get('nodes')==[] and lane.get('runner')=='scripts/run-kde-tier1-package-batch10-preflight.sh' and lane.get('workflow')=='.github/workflows/kde-tier1-package-batch10.yml','global discovery Batch10 lane not completed')
req(set(g.get('nodes',{}))=={'kuserfeedback','prison'},'post-Batch10 discovery set mismatch')
snap=g.get('promoted_snapshot',{})
req((snap.get('pass'),snap.get('pending'),snap.get('current_fail'),snap.get('blocked'))==(27,2,0,0),'post-Batch10 promoted snapshot mismatch')
req(bool(snap.get('note')),'post-Batch10 promoted snapshot must preserve historical-semantics note')
doc=text(ROOT/'docs/kde-tier1-package-batch10.md')
for token in ('25 PASS / 4 pending','DIAG_PASS','10464419377','10463808939','package_validation_dependency','BLOCKED','35398956698','10569258322','10570203712','35400585402','10570720119','35403143944','10570704785','35403658149','10570804457','35406143858','10572841006','35407208676','10573097334','35409521508','35409521636','105806202814','10573605864','dc233607ea647780580405b49e8b12855af5aaaf3b2d2bfea50c75fe7ed91780','b1e79e0fbc11672c017acc812efa74116f1681a56596deb87f0f770b47e3d01d','6.30.0-0supralinux4','consumer-smoke','extra-cmake-modules','KF6QuickChartsConfig.cmake','effective_required_export_count_amd64','44/44 PASS','8/8 PASS','optional=templinst|arch=!riscv64','KF6::KirigamiPlatform','qml6-module-org-kde-kirigami','27 PASS / 2 pending','35440818501','35440818686','105891183786','105892252854','35472599190','105976179351','promoted_snapshot.note'):
 req(token in doc,f'Batch10 documentation missing {token}')
if errors:
 print('\n'.join(f'ERROR: {e}' for e in errors),file=sys.stderr); raise SystemExit(1)
print('KDE Tier 1 Batch 10 canonical closure validation: PASS')
print('Nodes: kirigami retained PASS; kquickcharts retained PASS; campaign 2/2 PASS')
print('Canonical state: 27 PASS / 2 pending / 0 current FAIL / 0 BLOCKED; QML/multisurface lane completed')
