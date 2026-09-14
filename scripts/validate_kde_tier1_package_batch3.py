#!/usr/bin/env python3
from __future__ import annotations
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/'manifests/kde-tier1-package-campaign-batch3.json'; TIER1=ROOT/'manifests/kde-frameworks-tier1.json'; DAG=ROOT/'manifests/kde-dag.json'
DOC=ROOT/'docs/kde-tier1-package-batch3.md'; WORKFLOW=ROOT/'.github/workflows/kde-tier1-package-batch3.yml'; RUNNER=ROOT/'scripts/run-kde-tier1-package-batch3-preflight.sh'; SCOPE=ROOT/'scripts/kde-tier1-package-batch3-needed.sh'
EXPECTED={'kitemmodels':{'source':'f807e5b37aa913d2563ee1a21b2bce7d34495f32f38c7f35f16262d736bdfd55','symbols':'d9cbc25df40c2ea378cb8e3e77dafcea63a7b542315dc90498cb27f087db1c1e','runtime':'libkf6itemmodels6','soname':'libKF6ItemModels.so.6','build':['dh-sequence-qmldeps','qt6-base-dev (>= 6.9.0~)','qt6-declarative-dev (>= 6.9.0~)','qt6-tools-dev (>= 6.9.0~)']},'bluez-qt':{'source':'f5045b14a6c689bbfded9437582f943dd4f8f74537085ab6115bcacdea2110d8','symbols':'b72bea28842160da234b3bbab7975623616cd58f3e522b1e5d8705a279eef4f7','runtime':'libkf6bluezqt6','soname':'libKF6BluezQt.so.6','build':['dh-sequence-qmldeps','dbus-daemon <!nocheck>','qt6-base-dev (>= 6.9.0~)','qt6-declarative-dev (>= 6.9.0~)','qt6-tools-dev (>= 6.9.0~)']},'kplotting':{'source':'f5a67be85c21665e052371301889443196b9de5b3927aff353a3d3e27730dd11','symbols':'de5fddb29e85c05edefee280b2acf547d285318e6334b63b4a58527f59260cdb','runtime':'libkf6plotting6','soname':'libKF6Plotting.so.6','build':['qt6-base-dev (>= 6.9.0~)','qt6-tools-dev (>= 6.9.0~)']}}
errors=[]
def req(x,m):
 if not x: errors.append(m)
def load(p): return json.loads(p.read_text())
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
c=load(CAMPAIGN); tier={x['id']:x for x in load(TIER1)['nodes']}; dag=load(DAG)['nodes']
req(c.get('schema')==1,'schema'); req(c.get('authority')=='kde-upstream','authority'); req(c.get('frameworks_series')=='6.30.0','Frameworks'); req(c.get('batch')=='tier1-batch-3','batch'); req(c.get('state')=='prepared-pending-build','prepared state'); req(c.get('selected_nodes')==list(EXPECTED),'selected nodes')
req(c['selection_rationale']['deferred'].get('kconfig','').startswith('Deferred because KConfig exports multiple ABI'), 'KConfig deferral rationale')
req(c['shared_predecessors']['extra_cmake_modules']['version']=='6.30.0-0supralinux3','ECM'); req(c['shared_packaging_inputs']['documentation_policy']['qch_enabled'] is False,'QCH policy'); req(c['shared_packaging_inputs']['lintian_policy']['source_and_changes_required'] is True,'Lintian policy')
for n,e in EXPECTED.items():
 x=c['nodes'][n]; req(x['state']=='prepared-pending-build',f'{n}: prepared'); req(x['package_version']=='6.30.0-0supralinux1',f'{n}: revision'); req(x['source_sha256']==e['source'],f'{n}: source'); req(x['symbols']['sha256']==e['symbols'],f'{n}: symbols'); req(x['symbols']['tree_provider']=='debian',f'{n}: symbols provider'); req(x['runtime_package']==e['runtime'],f'{n}: runtime'); req(x['soname']==e['soname'],f'{n}: soname'); req(x['evidence']==[],f'{n}: evidence must be empty before attempt')
 d=ROOT/'packages/kde'/n/'debian'; control=(d/'control').read_text(); rules=(d/'rules').read_text(); readme=(d/'README.source').read_text(); docinstall=(d/x['documentation_package'].replace('-doc','-doc.install')).read_text(); consumer=(ROOT/'packages/kde'/n/'consumer/CMakeLists.txt').read_text(); main=(ROOT/'packages/kde'/n/'consumer/main.cpp').read_text()
 for tok in ['debhelper-compat (= 13)','dh-sequence-kf6','dh-sequence-pkgkde-symbolshelper','cmake (>= 3.29~)','extra-cmake-modules (>= 6.30.0~)',*e['build']]: req(tok in control,f'{n}: missing {tok}')
 req('Standards-Version: 4.7.3' in control,f'{n}: standards'); req('documentation compatibility package' in control,f'{n}: doc desc'); req('does not ship QCH documentation files' in control,f'{n}: QCH truth'); req('Intentionally empty' in docinstall,f'{n}: empty doc install'); req('-DBUILD_QCH=OFF' in rules,f'{n}: QCH disabled'); req('dh_auto_test' in rules,f'{n}: tests enabled'); req('KDE Frameworks 6.30.0 is the source/build authority' in readme,f'{n}: authority doc'); req(sha(d/'upstream/signing-key.asc')=='86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d',f'{n}: key'); req(x['cmake_package'] in consumer and x['cmake_target'] in consumer,f'{n}: cmake consumer'); req(e['soname'] in main and 'dlopen' in main,f'{n}: runtime consumer')
 req(tier[n]['state']=='pending' and tier[n]['packaging']=={'state':'pending'},f'{n}: canonical state must remain pending before build'); req(dag[n]['state']=='pending',f'{n}: DAG pending before build')
runner=RUNNER.read_text(); workflow=WORKFLOW.read_text(); scope=SCOPE.read_text(); doc=DOC.read_text()
for tok in ["-name '*.ddeb'",'lintian --fail-on error "${DSC}" "${CHANGES[0]}"','Lintian:[[:space:]]+fail','dpkg-source -b','--chroot-mode=unshare','consumer-smoke']: req(tok in runner,f'runner missing {tok}')
for tok in ['fail-fast: false','max-parallel: 3','kitemmodels','bluez-qt','kplotting','run-kde-tier1-package-batch3-preflight.sh']: req(tok in workflow,f'workflow missing {tok}')
req('kde-tier1-package-campaign-batch3.json' in scope,'scope campaign'); req('KConfig' in doc and 'multi-library' in doc,'docs KConfig deferral'); req('7 PASS' in doc and '22 pending' in doc,'docs canonical state')
if errors:
 for e in errors: print('ERROR:',e,file=sys.stderr)
 raise SystemExit(1)
print('KDE Tier 1 Batch 3 preparation validation: PASS')
print('Nodes: KItemModels, BluezQt, KPlotting; canonical Tier 1 remains 7 PASS / 22 pending before attempts.')
