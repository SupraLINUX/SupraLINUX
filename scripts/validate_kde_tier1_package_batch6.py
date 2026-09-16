#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/'manifests/kde-tier1-package-campaign-batch6.json'; TIER1=ROOT/'manifests/kde-frameworks-tier1.json'; DEPS=ROOT/'manifests/kde-frameworks-tier1-dependencies.json'; DAG=ROOT/'manifests/kde-dag.json'
WORKFLOW=ROOT/'.github/workflows/kde-tier1-package-batch6.yml'; POLICY=ROOT/'.github/workflows/repository-policy.yml'; RUNNER=ROOT/'scripts/run-kde-tier1-package-batch6-preflight.sh'; SCOPE=ROOT/'scripts/kde-tier1-package-batch6-needed.sh'
DOC=ROOT/'docs/kde-tier1-package-batch6.md'; STATUS=ROOT/'docs/status/2026-09-15-batch6.md'; CURRENT=ROOT/'docs/status/2026-09-15.md'; DEP_DOC=ROOT/'docs/kde-tier1-dependencies.md'
E={
'kwindowsystem':{'source':'639a501b877446b19905399d27e2be2b6ebb0bb481abe3209dc4d535a12e12ca','blob':'e8317948e1df27330ceddf45bf418aa2a02bde5b','symbols':'8aa9d83d65633f470c6c6f0e8f7f00bd56750d904bfeb465e514fc9fa70aa595','copyright':'872a164a55eda5b800588294d0686a94843225ff88579b90451ce41ee515b8a4','key':'5a0228357021204326d88472f29689b0ba25b29cd9ea4c97dab898a0aa4614d8','runtime':'libkf6windowsystem6','soname':'libKF6WindowSystem.so.6','cmake':'KF6WindowSystem','target':'KF6::WindowSystem','packages':['libkf6windowsystem-data','libkf6windowsystem-dev','libkf6windowsystem-doc','libkf6windowsystem6','qml6-module-org-kde-kwindowsystem']},
'solid':{'source':'bdbfdc9f26b87e12b951097825af2956f2dee3f14c701d780277b69701f2c74e','blob':'65681c1db745cd52a547659f1b778fa42bb3cb52','symbols':'4928d196746e4f497733ab7052eea5bf1b219013fb58c6aa4c52284f6e0eb419','copyright':'17c41b7829d7497ddbd06d84c02a9e158cb00ce6f933619184917dc5af61199b','key':'86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d','runtime':'libkf6solid6','soname':'libKF6Solid.so.6','cmake':'KF6Solid','target':'KF6::Solid','packages':['libkf6solid-bin','libkf6solid-data','libkf6solid-dev','libkf6solid-doc','libkf6solid6']}}
errs=[]
def req(v,m):
 if not v: errs.append(m)
def load(p): return json.loads(p.read_text())
def txt(p):
 req(p.exists(),f'missing {p.relative_to(ROOT)}'); return p.read_text() if p.exists() else ''
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
c=load(CAMPAIGN); tier={n['id']:n for n in load(TIER1)['nodes']}; deps=load(DEPS); dag=load(DAG)['nodes']
req(c.get('schema')==1,'schema'); req(c.get('authority')=='kde-upstream','authority'); req(c.get('frameworks_series')=='6.30.0','series'); req(c.get('batch')=='tier1-batch-6','batch'); req(c.get('state')=='remediation-pending-build','batch remediation state'); req(c.get('selected_nodes')==list(E),'selected nodes')
req(c.get('canonical_snapshot')=={'state':'unpromoted-open-batch','tier1':'16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED'},'canonical snapshot must remain unpromoted')
sp=c['shared_predecessors']; req(sp['extra_cmake_modules']['state']=='PASS' and sp['extra_cmake_modules']['artifact_id']==10298635300,'ECM PASS'); req(sp['packaging_trees']['artifact_id']==10301938362,'packaging reference'); req(sp['dependency_provider']['workflow_run']==35012023822 and sp['dependency_provider']['artifact_id']==10414525047,'provider evidence')
for node,e in E.items():
 n=c['nodes'][node]; req(n['source_sha256']==e['source'],f'{node}: source'); req(n['root_cmake_blob']==e['blob'],f'{node}: CMake blob'); req(n['symbols']['sha256']==e['symbols'],f'{node}: symbols'); req(n['copyright']['sha256']==e['copyright'],f'{node}: copyright'); req(n['signing_key']['sha256']==e['key'],f'{node}: key hash'); req(n['signing_key']['signer_fingerprint']=='90A968ACA84537CC27B99EAF2C8DF587A6D4AAC1',f'{node}: signer'); req(n['runtime_package']==e['runtime'] and n['soname']==e['soname'],f'{node}: ABI'); req(n['cmake_package']==e['cmake'] and n['cmake_target']==e['target'],f'{node}: CMake consumer'); req([x['name'] for x in n['binary_contracts']]==e['packages'],f'{node}: package list')
 req(deps['metadata'][node]['ref']=='v6.30.0' and deps['metadata'][node]['root_cmake_blob']==e['blob'],f'{node}: dependency upstream pin'); req(tier[node]['state']=='pending' and tier[node]['packaging']['state']=='pending',f'{node}: canonical Tier1 remains pending'); req(node not in dag,f'{node}: open batch not promoted into DAG')
 deb=ROOT/'packages/kde'/node/'debian'; control=txt(deb/'control'); rules=txt(deb/'rules'); readme=txt(deb/'README.source'); req((deb/'changelog').read_text().startswith(f"{n['source_package']} ({n['package_version']}) resolute;"),f'{node}: changelog'); req('-DBUILD_QCH=OFF' in rules,f'{node}: QCH common profile'); req('Debian 6.28.0 baseline' in readme,f'{node}: provenance'); req(txt(deb/'source/format')=='3.0 (quilt)\n',f'{node}: source format'); req(sha(deb/'upstream/signing-key.asc')==e['key'],f'{node}: retained key bytes'); req(e['symbols'] in txt(deb/(n['symbols']['file']+'.reference.meta')),f'{node}: symbols provenance'); req(e['copyright'] in txt(deb/'copyright.reference'),f'{node}: copyright provenance'); req(f'find_package({e["cmake"]} 6.30 REQUIRED)' in txt(ROOT/'packages/kde'/node/'consumer/CMakeLists.txt'),f'{node}: consumer'); req(e['soname'] in txt(ROOT/'packages/kde'/node/'consumer/main.cpp'),f'{node}: dlopen')
for token in ('dh-sequence-qmldeps','qt6-base-private-dev (>= 6.9.0~)','qt6-declarative-dev (>= 6.9.0~)','qt6-wayland-dev (>= 6.9.0~)','wayland-protocols (>= 1.46~)','plasma-wayland-protocols','weston [linux-any] <!nocheck>','openbox <!nocheck>','x11-utils <!nocheck>','xvfb <!nocheck>'):
 req(token in txt(ROOT/'packages/kde/kwindowsystem/debian/control'),f'kwindowsystem missing {token}')
req('xvfb-run -a debian/run-tests-with-openbox.sh' in txt(ROOT/'packages/kde/kwindowsystem/debian/rules'),'kwindowsystem tests enabled via Xvfb+OpenBox')
fixture=ROOT/'packages/kde/kwindowsystem/debian/run-tests-with-openbox.sh'; req(fixture.exists() and fixture.stat().st_mode & 0o111,'kwindowsystem OpenBox fixture executable'); ft=txt(fixture); req('openbox --sm-disable' in ft and '_NET_SUPPORTING_WM_CHECK' in ft and 'dh_auto_test -Skf6 --no-parallel' in ft,'kwindowsystem OpenBox fixture + serial test contract')
for token in ('bison (>= 2:3.0~)','flex','libmount-dev','libudev-dev','libimobiledevice-dev','libplist-dev','dbus-daemon <!nocheck>'):
 req(token in txt(ROOT/'packages/kde/solid/debian/control'),f'solid missing {token}')
req('dbus-run-session dh_auto_test -Skf6' in txt(ROOT/'packages/kde/solid/debian/rules'),'solid tests enabled in D-Bus session'); req('UDEV_DISABLED' not in txt(ROOT/'packages/kde/solid/debian/rules'),'Solid udev default must remain enabled'); req('BUILD_DEVICE_BACKEND_hal' not in txt(ROOT/'packages/kde/solid/debian/rules'),'do not carry distro-only HAL override')

kw=c['nodes']['kwindowsystem']; so=c['nodes']['solid']
req(kw['state']=='remediation-pending-build' and kw['last_result']=='FAIL' and kw['downstream_eligible'] is False,'kwindowsystem: remediation state')
req(kw['package_version']=='6.30.0-0supralinux4','kwindowsystem: revision -4')
req(len(kw.get('evidence',[]))==3 and [x.get('result') for x in kw['evidence']]==['FAIL','FAIL','FAIL'],'kwindowsystem: three retained FAIL attempts')
kev1,kev2,kev3=kw['evidence']
req(kev1.get('workflow_run')==35034742520 and kev1.get('job_id')==104601176595 and kev1.get('artifact_id')==10422598658,'kwindowsystem: -1 evidence ids')
req(kev1.get('artifact_sha256')=='cc38c90312b6e73b2dc338712c391af96664cdd2a342d16f2a163bce67c1be1b','kwindowsystem: -1 artifact hash')
req('xcb/xfixes.h' in kev1.get('cause','') and 'libxcb-xfixes0-dev' in kev1.get('cause',''),'kwindowsystem: -1 root cause')
req(kev2.get('workflow_run')==35038057329 and kev2.get('job_id')==104611513304 and kev2.get('artifact_id')==10424431374,'kwindowsystem: -2 evidence ids')
req(kev2.get('artifact_sha256')=='7b47be8422970fd10c1f67ef450f05bcff9f6086f7f188cd5f91bfcf3c082904','kwindowsystem: -2 artifact hash')
req(kev2.get('tests')=='11/14 CTest suites PASS' and 'OpenBox' in kev2.get('cause',''),'kwindowsystem: -2 fixture root cause')
req(kev3.get('workflow_run')==35040999577 and kev3.get('job_id')==104620609155 and kev3.get('artifact_id')==10425162919,'kwindowsystem: -3 evidence ids')
req(kev3.get('commit')=='0da3238a528893a28e624d89014dc82dea3d8e9d' and kev3.get('attempted_package_version')=='6.30.0-0supralinux3','kwindowsystem: -3 commit/revision')
req(kev3.get('artifact_sha256')=='58481311a264849cbe78c166fcfd2e174d95bc56e04e32be9cab7efed3a2b9dc','kwindowsystem: -3 artifact hash')
req(kev3.get('tests')=='12/14 CTest suites PASS' and kev3.get('failure_substage')=='autotest/X11-shared-display-parallelism','kwindowsystem: -3 test/substage evidence')
req('parallel=4' in kev3.get('cause','') and 'same Xvfb/OpenBox' in kev3.get('cause',''),'kwindowsystem: -3 shared-X11-state cause')
req('libxcb-xfixes0-dev' in txt(ROOT/'packages/kde/kwindowsystem/debian/control'),'kwindowsystem: provider remediation retained')
req('openbox <!nocheck>' in txt(ROOT/'packages/kde/kwindowsystem/debian/control') and 'x11-utils <!nocheck>' in txt(ROOT/'packages/kde/kwindowsystem/debian/control'),'kwindowsystem: NETWM fixture dependencies')
req(all(x in kw.get('build_profile_tokens',[]) for x in ('libxcb-xfixes0-dev','openbox <!nocheck>','x11-utils <!nocheck>')),'kwindowsystem: fixture manifest tokens')
req(kw.get('remediation',{}).get('candidate_package_version')=='6.30.0-0supralinux4','kwindowsystem: remediation revision -4')
req(kw.get('remediation',{}).get('status')=='remediation-pending-build' and kw.get('remediation',{}).get('source_change') is False,'kwindowsystem: remediation state/source')
req(any('--no-parallel' in x for x in kw.get('remediation',{}).get('changes',[])),'kwindowsystem: serial test remediation documented')
req(any('no test exclusions' in x for x in kw.get('remediation',{}).get('changes',[])),'kwindowsystem: tests remain enabled')

req(so['state']=='PASS' and so['last_result']=='PASS' and so['downstream_eligible'] is True,'solid: PASS state in open-batch ledger')
req(so['package_version']=='6.30.0-0supralinux2','solid: PASS revision')
req(len(so.get('evidence',[]))==2 and [x.get('result') for x in so['evidence']]==['FAIL','PASS'],'solid: retained FAIL plus PASS evidence')
sev1,sev2=so['evidence']
req(sev1.get('workflow_run')==35034742520 and sev1.get('job_id')==104601176254 and sev1.get('artifact_id')==10422873422,'solid: -1 evidence ids')
req(sev1.get('artifact_sha256')=='135a63a6855bed690e6bbdbf67dc924b5dbd8bd304f0a78c84920927772e15a0','solid: -1 artifact hash')
req(sev1.get('tests')=='5/5 PASS' and '_ZSt19piecewise_construct@Base' in sev1.get('cause',''),'solid: -1 test/root cause')
req(sev2.get('workflow_run')==35038057329 and sev2.get('job_id')==104611513122 and sev2.get('artifact_id')==10423914110,'solid: PASS evidence ids')
req(sev2.get('artifact_sha256')=='7cc2b15e2fa627e3cd280395e0ac48bd3658c7328d194958b872713738b97fc0','solid: PASS artifact hash')
req(sev2.get('tests')=='5/5 PASS' and sev2.get('lintian')=='PASS-errors' and sev2.get('consumer_smoke')=='PASS' and sev2.get('abi_soname')=='libKF6Solid.so.6','solid: PASS gates')
rem=so.get('remediation',{})
req(rem.get('status')=='resolved-pass' and rem.get('candidate_package_version')=='6.30.0-0supralinux2','solid: remediation resolved')
req(rem.get('symbols_baseline_sha256')=='4928d196746e4f497733ab7052eea5bf1b219013fb58c6aa4c52284f6e0eb419','solid: symbols baseline')
req(rem.get('symbols_result_sha256')=='8614c45e8a902f3c3011b8cec65680ab5152314c798a71ebec108fc50fb547d0','solid: transformed symbols hash')
transform=ROOT/'packages/kde/solid/debian/apply-symbols-delta.py'
req(transform.exists() and sha(transform)=='35fff06320bf6a5ec8db8ba5f4e062e2242f692446f3d19304602ba7147c0b70','solid: transform hash')
req('python3:any' in txt(ROOT/'packages/kde/solid/debian/control'),'solid: explicit Python build prerequisite')
req('python3:any' in so.get('build_profile_tokens',[]),'solid: Python manifest prerequisite')
req('(optional=toolchain|arch=!armhf !riscv64)_ZSt19piecewise_construct@Base 6.4.0' in txt(transform),'solid: reviewed toolchain symbol policy')
rules=txt(ROOT/'packages/kde/solid/debian/rules')
req('python3 debian/apply-symbols-delta.py' in rules and 'dh_makeshlibs' in rules,'solid: symbols transform hook')
req(rules.find('python3 debian/apply-symbols-delta.py') < rules.rfind('dh_makeshlibs'),'solid: transform must precede dh_makeshlibs')
workflow=txt(WORKFLOW); runner=txt(RUNNER); scope=txt(SCOPE); policy=txt(POLICY)
for tok in ('runs-on: ubuntu-26.04','fail-fast: false','max-parallel: 2','node: [kwindowsystem, solid]',"artifact-ids: '10298635300'","artifact-ids: '10301938362'",'scripts/kde-tier1-package-batch6-needed.sh','scripts/run-kde-tier1-package-batch6-preflight.sh'): req(tok in workflow,f'workflow missing {tok}')
for tok in ('dpkg-source -b','sbuild --verbose --chroot-mode=unshare','lintian --fail-on error','readelf -d','cmake -S "${CONSUMER_META}"','EXPECTED_PACKAGES'): req(tok in runner,f'runner missing {tok}')
for node in E: req(node in scope,f'scope missing {node}')
req('manifests/kde-tier1-package-campaign-batch6.json' in scope and 'binary_contracts' in scope and 'build_profile_tokens' in scope,'semantic scope'); req('python3 scripts/validate_kde_tier1_package_batch6.py' in policy,'repository policy validator')
for p in (DOC,STATUS,CURRENT,DEP_DOC):
 t=txt(p); req('16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED' in t,f'{p.name}: canonical counts')
req('KWindowSystem' in txt(DOC) and 'Solid' in txt(DOC) and 'fourth build pending' in txt(DOC).lower(),'Batch6 documentation'); req('multi-library' in txt(DOC) and 'Python bindings' in txt(DOC),'deferral rationale')
req('35040999577' in txt(DOC) and '10425162919' in txt(DOC) and '--no-parallel' in txt(DOC),'Batch6 third-attempt evidence/remediation docs')
if errs:
 for e in errs: print('ERROR:',e,file=sys.stderr)
 raise SystemExit(1)
print('KDE Tier 1 Batch 6 fourth-attempt preparation validation: PASS')
print('Selected: kwindowsystem, solid')
print('Canonical state remains: 16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED')
