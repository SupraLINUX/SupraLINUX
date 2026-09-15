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
 n=c['nodes'][node]; req(n['state']=='remediation-pending-build' and n['last_result']=='FAIL' and n['downstream_eligible'] is False,f'{node}: remediation state'); req(n['package_version']=='6.30.0-0supralinux2',f'{node}: revision'); req(n['source_sha256']==e['source'],f'{node}: source'); req(n['root_cmake_blob']==e['blob'],f'{node}: CMake blob'); req(n['symbols']['sha256']==e['symbols'],f'{node}: symbols'); req(n['copyright']['sha256']==e['copyright'],f'{node}: copyright'); req(n['signing_key']['sha256']==e['key'],f'{node}: key hash'); req(n['signing_key']['signer_fingerprint']=='90A968ACA84537CC27B99EAF2C8DF587A6D4AAC1',f'{node}: signer'); req(n['runtime_package']==e['runtime'] and n['soname']==e['soname'],f'{node}: ABI'); req(n['cmake_package']==e['cmake'] and n['cmake_target']==e['target'],f'{node}: CMake consumer'); req([x['name'] for x in n['binary_contracts']]==e['packages'],f'{node}: package list'); req(len(n.get('evidence',[]))==1 and n['evidence'][0].get('result')=='FAIL',f'{node}: retained -1 FAIL evidence')
 req(deps['metadata'][node]['ref']=='v6.30.0' and deps['metadata'][node]['root_cmake_blob']==e['blob'],f'{node}: dependency upstream pin'); req(tier[node]['state']=='pending' and tier[node]['packaging']['state']=='pending',f'{node}: canonical Tier1 remains pending'); req(node not in dag,f'{node}: open batch not promoted into DAG')
 deb=ROOT/'packages/kde'/node/'debian'; control=txt(deb/'control'); rules=txt(deb/'rules'); readme=txt(deb/'README.source'); req((deb/'changelog').read_text().startswith(f"{n['source_package']} (6.30.0-0supralinux2) resolute;"),f'{node}: changelog'); req('-DBUILD_QCH=OFF' in rules,f'{node}: QCH common profile'); req('Debian 6.28.0 baseline' in readme,f'{node}: provenance'); req(txt(deb/'source/format')=='3.0 (quilt)\n',f'{node}: source format'); req(sha(deb/'upstream/signing-key.asc')==e['key'],f'{node}: retained key bytes'); req(e['symbols'] in txt(deb/(n['symbols']['file']+'.reference.meta')),f'{node}: symbols provenance'); req(e['copyright'] in txt(deb/'copyright.reference'),f'{node}: copyright provenance'); req(f'find_package({e["cmake"]} 6.30 REQUIRED)' in txt(ROOT/'packages/kde'/node/'consumer/CMakeLists.txt'),f'{node}: consumer'); req(e['soname'] in txt(ROOT/'packages/kde'/node/'consumer/main.cpp'),f'{node}: dlopen')
for token in ('dh-sequence-qmldeps','qt6-base-private-dev (>= 6.9.0~)','qt6-declarative-dev (>= 6.9.0~)','qt6-wayland-dev (>= 6.9.0~)','wayland-protocols (>= 1.46~)','plasma-wayland-protocols','weston [linux-any] <!nocheck>','xvfb <!nocheck>'):
 req(token in txt(ROOT/'packages/kde/kwindowsystem/debian/control'),f'kwindowsystem missing {token}')
req('xvfb-run -a dh_auto_test -Skf6' in txt(ROOT/'packages/kde/kwindowsystem/debian/rules'),'kwindowsystem tests enabled via Xvfb')
for token in ('bison (>= 2:3.0~)','flex','libmount-dev','libudev-dev','libimobiledevice-dev','libplist-dev','dbus-daemon <!nocheck>'):
 req(token in txt(ROOT/'packages/kde/solid/debian/control'),f'solid missing {token}')
req('dbus-run-session dh_auto_test -Skf6' in txt(ROOT/'packages/kde/solid/debian/rules'),'solid tests enabled in D-Bus session'); req('UDEV_DISABLED' not in txt(ROOT/'packages/kde/solid/debian/rules'),'Solid udev default must remain enabled'); req('BUILD_DEVICE_BACKEND_hal' not in txt(ROOT/'packages/kde/solid/debian/rules'),'do not carry distro-only HAL override')

kw=c['nodes']['kwindowsystem']; so=c['nodes']['solid']
kev=kw['evidence'][0]; sev=so['evidence'][0]
req(kev.get('workflow_run')==35034742520 and kev.get('job_id')==104601176595 and kev.get('artifact_id')==10422598658,'kwindowsystem: -1 evidence ids')
req(kev.get('artifact_sha256')=='cc38c90312b6e73b2dc338712c391af96664cdd2a342d16f2a163bce67c1be1b','kwindowsystem: -1 artifact hash')
req('xcb/xfixes.h' in kev.get('cause','') and 'libxcb-xfixes0-dev' in kev.get('cause',''),'kwindowsystem: -1 root cause')
req('libxcb-xfixes0-dev' in txt(ROOT/'packages/kde/kwindowsystem/debian/control'),'kwindowsystem: remediation provider')
req('libxcb-xfixes0-dev' in kw.get('build_profile_tokens',[]),'kwindowsystem: remediation manifest provider')
req(kw.get('remediation',{}).get('candidate_package_version')=='6.30.0-0supralinux2','kwindowsystem: remediation revision')
req(sev.get('workflow_run')==35034742520 and sev.get('job_id')==104601176254 and sev.get('artifact_id')==10422873422,'solid: -1 evidence ids')
req(sev.get('artifact_sha256')=='135a63a6855bed690e6bbdbf67dc924b5dbd8bd304f0a78c84920927772e15a0','solid: -1 artifact hash')
req(sev.get('tests')=='5/5 PASS' and '_ZSt19piecewise_construct@Base' in sev.get('cause',''),'solid: -1 test/root cause')
rem=so.get('remediation',{})
req(rem.get('candidate_package_version')=='6.30.0-0supralinux2','solid: remediation revision')
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
req('KWindowSystem' in txt(DOC) and 'Solid' in txt(DOC) and 'prepared' in txt(DOC).lower(),'Batch6 documentation'); req('multi-library' in txt(DOC) and 'Python bindings' in txt(DOC),'deferral rationale')
if errs:
 for e in errs: print('ERROR:',e,file=sys.stderr)
 raise SystemExit(1)
print('KDE Tier 1 Batch 6 remediation validation: PASS')
print('Selected: kwindowsystem, solid')
print('Canonical state remains: 16 PASS / 13 pending / 0 current FAIL / 0 BLOCKED')
