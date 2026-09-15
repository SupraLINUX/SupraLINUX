#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CAMPAIGN=ROOT/'manifests/kde-tier1-package-campaign-batch5.json'
TIER1=ROOT/'manifests/kde-frameworks-tier1.json'
DEPS=ROOT/'manifests/kde-frameworks-tier1-dependencies.json'
DAG=ROOT/'manifests/kde-dag.json'
WORKFLOW=ROOT/'.github/workflows/kde-tier1-package-batch5.yml'
POLICY=ROOT/'.github/workflows/repository-policy.yml'
RUNNER=ROOT/'scripts/run-kde-tier1-package-batch5-preflight.sh'
SCOPE=ROOT/'scripts/kde-tier1-package-batch5-needed.sh'
DOC=ROOT/'docs/kde-tier1-package-batch5.md'
STATUS=ROOT/'docs/status/2026-09-15-batch5.md'
PROVIDER_DOC=ROOT/'docs/decisions/modemmanager-provider-2026-09-15.md'
DEPENDENCY_DOC=ROOT/'docs/kde-tier1-dependencies.md'
errors=[]
def req(v,m):
    if not v: errors.append(m)
def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def text(p):
    req(p.exists(),f'missing {p.relative_to(ROOT)}')
    return p.read_text(encoding='utf-8') if p.exists() else ''

EXPECTED={
 'kidletime':{'source':'22873204292ddb757e5a0a57004c57debe1285cd0fd4e796d07e9de2402e60c3','blob':'3617fd79358beaea36d862483b8b4947eef30508','symbols':'1ae402305be324fc97b61bb099d3c6e001ec2bfc8eaf2ae09f1cd69eafbe914c','copyright':'1afa9e5366e809877f085a8918ac733de4935be71be1aee3ff785362aee2bd0b','runtime':'libkf6idletime6','soname':'libKF6IdleTime.so.6','cmake':'KF6IdleTime','target':'KF6::IdleTime','packages':['libkf6idletime-dev','libkf6idletime-doc','libkf6idletime6']},
 'modemmanager-qt':{'source':'d7c4106dc130729fdfd435abaeaf85039a874fc18563a41755e14f7ea174ae21','blob':'1c253781f61fe39608b7d102a9359ca2f9afb1b0','symbols':'70c9ebc08c99174f022c3b4b38ed4cde4a8725f0a2f8ea04a09371132312d6f2','copyright':'6863209ef5575d5ac62b9e77d9ee6ee7a4c06e05622cb9671499686696c4605d','runtime':'libkf6modemmanagerqt6','soname':'libKF6ModemManagerQt.so.6','cmake':'KF6ModemManagerQt','target':'KF6::ModemManagerQt','packages':['libkf6modemmanagerqt-dev','libkf6modemmanagerqt-doc','libkf6modemmanagerqt6']},
 'networkmanager-qt':{'source':'f6ba5f54d413ea0b2642207a6ebd0803e7cb8392b91fcf8a1679fd0c21062865','blob':'be28b0b1092c3b64a4561fcb28f0dbf811e6a939','symbols':'324a154e35a6dab6c2ab10c5857517a20253d7d65f279294a62e7ced3c8ebfaa','copyright':'c6d6d851fc0ac1e99ab9d5535159213b3ba4a7deff6a4239f76e59fb51316e1e','runtime':'libkf6networkmanagerqt6','soname':'libKF6NetworkManagerQt.so.6','cmake':'KF6NetworkManagerQt','target':'KF6::NetworkManagerQt','packages':['libkf6networkmanagerqt-dev','libkf6networkmanagerqt-doc','libkf6networkmanagerqt6','qml6-module-org-kde-networkmanager']},
}

c=load(CAMPAIGN); tier={n['id']:n for n in load(TIER1)['nodes']}; deps=load(DEPS); dag=load(DAG)['nodes']
req(c.get('schema')==1,'campaign schema')
req(c.get('authority')=='kde-upstream','KDE authority')
req(c.get('frameworks_series')=='6.30.0','Frameworks series')
req(c.get('batch')=='tier1-batch-5','batch id')
req(c.get('state')=='open-remediation','open remediation state')
req(c.get('selected_nodes')==list(EXPECTED),'selected node order')
req(c.get('canonical_snapshot',{}).get('tier1')=='13 PASS / 16 pending / 0 current FAIL / 0 BLOCKED','canonical snapshot')
req(c.get('canonical_snapshot',{}).get('state')=='unpromoted-open-batch','must remain unpromoted')
sp=c['shared_predecessors']
req(sp['extra_cmake_modules']['state']=='PASS' and sp['extra_cmake_modules']['artifact_id']==10298635300,'retained ECM PASS')
req(sp['packaging_trees']['artifact_id']==10301938362,'retained packaging-tree artifact')
prov=sp['dependency_provider']
req(prov=={'status':'PASS','workflow_run':35012023822,'job_id':104526071758,'commit':'48fd01bfa7b254b5e5c8447b3d609f76a91f786f','artifact_id':10414525047,'artifact_sha256':'db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a','authoritative':False,'claim':'provider-availability-only'},'provider revalidation evidence')
req(c['shared_packaging_inputs']['documentation_policy']['qch_enabled'] is False,'QCH policy')
req(c['shared_packaging_inputs']['signing_key']['sha256']=='86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d','signing key hash')

for node,e in EXPECTED.items():
    n=c['nodes'][node]
    if node in ('kidletime','networkmanager-qt'):
        req(n['state']=='PASS',f'{node}: package-ledger PASS state')
        req(n['last_result']=='PASS' and n['downstream_eligible'] is True,f'{node}: retained PASS/downstream state')
        req(n['package_version']=='6.30.0-0supralinux1',f'{node}: PASS revision')
    elif node=='modemmanager-qt':
        req(n['state']=='remediation-pending-build',f'{node}: remediation state')
        req(n['last_result']=='FAIL' and n['downstream_eligible'] is False,f'{node}: retained FAIL state')
        req(n['package_version']=='6.30.0-0supralinux3',f'{node}: remediation revision')
    req(n['source_sha256']==e['source'],f'{node}: source SHA')
    req(n['root_cmake_blob']==e['blob'],f'{node}: root CMake blob')
    req(n['runtime_package']==e['runtime'],f'{node}: runtime')
    req(n['soname']==e['soname'],f'{node}: SONAME')
    req(n['cmake_package']==e['cmake'] and n['cmake_target']==e['target'],f'{node}: CMake contract')
    req(n['symbols']['sha256']==e['symbols'],f'{node}: symbols reference hash')
    req(n['copyright']['sha256']==e['copyright'],f'{node}: copyright reference hash')
    req([x['name'] for x in n['binary_contracts']]==e['packages'],f'{node}: binary package contract')
    req(deps['metadata'][node]['ref']=='v6.30.0' and deps['metadata'][node]['root_cmake_blob']==e['blob'],f'{node}: upstream metadata pin')
    req(tier[node]['state']=='pending',f'{node}: canonical Tier 1 must remain pending')
    req(node not in dag,f'{node}: open batch must not be promoted into canonical DAG')
    deb=ROOT/'packages/kde'/node/'debian'
    control=text(deb/'control'); rules=text(deb/'rules'); changelog=text(deb/'changelog'); readme=text(deb/'README.source')
    req(changelog.startswith(f"{n['source_package']} ({n['package_version']}) resolute;"),f'{node}: changelog revision')
    for token in ('debhelper-compat (= 13)','dh-sequence-kf6','dh-sequence-pkgkde-symbolshelper','cmake (>= 3.29~)','extra-cmake-modules (>= 6.30.0~)','qt6-tools-dev (>= 6.9.0~)'):
        req(token in control,f'{node}: missing control token {token}')
    req('-DBUILD_QCH=OFF' in rules,f'{node}: QCH disabled only by common profile')
    req('Debian 6.28.0 baseline' in readme,f'{node}: reference provenance')
    req(text(deb/'source/format')=='3.0 (quilt)\n',f'{node}: source format')
    key=deb/'upstream/signing-key.asc'; req(key.exists(),f'{node}: signing key missing')
    if key.exists(): req(sha(key)=='86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d',f'{node}: signing key digest')
    sref=text(deb/(n['symbols']['file']+'.reference')); cref=text(deb/'copyright.reference')
    req(e['symbols'] in sref and 'artifact_id=10301938362' in sref,f'{node}: symbols provenance')
    req(e['copyright'] in cref and 'artifact_id=10301938362' in cref,f'{node}: copyright provenance')
    consumer=text(ROOT/'packages/kde'/node/'consumer/CMakeLists.txt'); main=text(ROOT/'packages/kde'/node/'consumer/main.cpp')
    req(f"find_package({e['cmake']} 6.30 REQUIRED)" in consumer and e['target'] in consumer,f'{node}: consumer CMake')
    req(e['soname'] in main and 'dlopen' in main,f'{node}: runtime consumer')

PASS_EXPECTED={
 'kidletime':{'job':104535671033,'artifact':10414598079,'digest':'272ccad537d21905cf75a1add74e937d176c20c05c38bf967226fef4ab28b605','tests':'1/1 PASS','soname':'libKF6IdleTime.so.6'},
 'networkmanager-qt':{'job':104535671250,'artifact':10414714325,'digest':'abf927b5749b34094d2b5ee530831f64638ba116a83e8b82f925a758aa018ad4','tests':'38/38 PASS','soname':'libKF6NetworkManagerQt.so.6'},
}
for node,want in PASS_EXPECTED.items():
    evidence=c['nodes'][node].get('evidence',[])
    req(len(evidence)==1 and evidence[0].get('result')=='PASS',f'{node}: exactly one retained PASS')
    if evidence:
        ev=evidence[0]
        req(ev.get('workflow_run')==35014875475 and ev.get('job_id')==want['job'],f'{node}: PASS run/job')
        req(ev.get('commit')=='30b5dcd293527b488c88cf0a861883ee869e3ea0',f'{node}: PASS commit')
        req(ev.get('attempted_package_version')=='6.30.0-0supralinux1',f'{node}: PASS revision')
        req(ev.get('artifact_id')==want['artifact'] and ev.get('artifact_sha256')==want['digest'],f'{node}: PASS artifact')
        req(ev.get('stage')=='complete' and ev.get('tests')==want['tests'],f'{node}: PASS stage/tests')
        req(ev.get('lintian')=='PASS-errors' and ev.get('consumer_smoke')=='PASS',f'{node}: PASS gates')
        req(ev.get('abi_soname')==want['soname'] and ev.get('downstream_eligible') is True,f'{node}: PASS ABI/downstream')
    for key,digest in c['nodes'][node].get('last_pass_files',{}).items():
        req(re.fullmatch(r'^[0-9a-f]{64}',str(digest)) is not None,f'{node}: invalid retained file hash {key}')

mm=c['nodes']['modemmanager-qt']
mm_ev=mm.get('evidence',[])
req(len(mm_ev)==2 and all(ev.get('result')=='FAIL' for ev in mm_ev),'modemmanager-qt: retain exactly two historical FAIL attempts')
if len(mm_ev)>=1:
    ev=mm_ev[0]
    req(ev.get('workflow_run')==35014875475 and ev.get('job_id')==104535671188,'modemmanager-qt: -1 FAIL run/job')
    req(ev.get('commit')=='30b5dcd293527b488c88cf0a861883ee869e3ea0','modemmanager-qt: -1 FAIL commit')
    req(ev.get('attempted_package_version')=='6.30.0-0supralinux1','modemmanager-qt: -1 historical FAIL revision')
    req(ev.get('artifact_id')==10415586492 and ev.get('artifact_sha256')=='f79f98cc73f561e5750c4db7917917a043f260131af0ac19180fd835dee78af7','modemmanager-qt: -1 FAIL artifact')
    req(ev.get('failure_stage')=='sbuild' and ev.get('failure_substage')=='Lintian/symbols','modemmanager-qt: -1 FAIL stage')
    req(ev.get('tests')=='11/11 PASS','modemmanager-qt: -1 tests passed before Lintian failure')
    req('_ZSt19piecewise_construct@Base' in ev.get('cause',''),'modemmanager-qt: -1 retained root cause')
if len(mm_ev)>=2:
    ev=mm_ev[1]
    req(ev.get('workflow_run')==35017509303 and ev.get('job_id')==104544555425,'modemmanager-qt: -2 FAIL run/job')
    req(ev.get('commit')=='77f4c6e9e077e12bf7063ee2f872255d397ec8c8','modemmanager-qt: -2 FAIL commit')
    req(ev.get('attempted_package_version')=='6.30.0-0supralinux2','modemmanager-qt: -2 historical FAIL revision')
    req(ev.get('artifact_id')==10416692119 and ev.get('artifact_sha256')=='2b081f989d42f6d4820b238c9e739ccb4104080ceae7a49aa49cb20305eb66d7','modemmanager-qt: -2 FAIL artifact')
    req(ev.get('failure_stage')=='sbuild' and ev.get('failure_substage')=='Lintian/build-prerequisite','modemmanager-qt: -2 FAIL stage')
    req(ev.get('tests')=='11/11 PASS' and ev.get('symbols_transform')=='PASS','modemmanager-qt: -2 tests/symbols transform evidence')
    req('python3' in ev.get('cause','') and 'rules-require-build-prerequisite' in ev.get('cause',''),'modemmanager-qt: -2 retained root cause')
rem=mm.get('remediation',{})
req(rem.get('candidate_package_version')=='6.30.0-0supralinux3' and rem.get('status')=='prepared','modemmanager-qt: remediation candidate')
req(rem.get('source_change') is False,'modemmanager-qt: remediation must not change KDE source')
req(rem.get('symbols_baseline_sha256')=='70c9ebc08c99174f022c3b4b38ed4cde4a8725f0a2f8ea04a09371132312d6f2','modemmanager-qt: baseline hash')
req(rem.get('symbols_result_sha256')=='b717475396376ac884bb3587ab2a0e898af5beb940836c45ee834758eec6820f','modemmanager-qt: transformed hash')
req(rem.get('symbols_transform_sha256')=='f468a9e752ecb79ccc05e3a7e344622f7b1e6aeae94fb71089a94f0f51d5559b','modemmanager-qt: transform hash')
req(any('python3:any' in change for change in rem.get('changes',[])),'modemmanager-qt: -3 must document explicit Python build prerequisite')

req('xvfb-run -a dh_auto_test' in text(ROOT/'packages/kde/kidletime/debian/rules'),'KIdleTime tests via Xvfb')
mm_control=text(ROOT/'packages/kde/modemmanager-qt/debian/control')
req('modemmanager-dev (>= 1.0)' in mm_control and 'libmm-glib-dev' not in mm_control,'ModemManager provider contract')
req('python3:any' in mm_control,'ModemManagerQt -3 must declare Python rules prerequisite')
mm_rules=text(ROOT/'packages/kde/modemmanager-qt/debian/rules')
req('dbus-run-session dh_auto_test -Skf6' in mm_rules,'ModemManagerQt D-Bus test session')
req('override_dh_makeshlibs:' in mm_rules and 'python3 debian/apply-symbols-delta.py' in mm_rules,'ModemManagerQt symbols remediation order')
mm_delta=ROOT/'packages/kde/modemmanager-qt/debian/apply-symbols-delta.py'
req(mm_delta.exists() and sha(mm_delta)=='f468a9e752ecb79ccc05e3a7e344622f7b1e6aeae94fb71089a94f0f51d5559b','ModemManagerQt transform script hash')
if mm_delta.exists():
    dt=text(mm_delta)
    req("BASE_SHA256 = '70c9ebc08c99174f022c3b4b38ed4cde4a8725f0a2f8ea04a09371132312d6f2'" in dt,'ModemManagerQt transform baseline lock')
    req("RESULT_SHA256 = 'b717475396376ac884bb3587ab2a0e898af5beb940836c45ee834758eec6820f'" in dt,'ModemManagerQt transform result lock')
    req('(optional=toolchain)_ZSt19piecewise_construct@Base 6.30.0' in dt,'ModemManagerQt optional toolchain symbol')
nm_control=text(ROOT/'packages/kde/networkmanager-qt/debian/control'); nm_rules=text(ROOT/'packages/kde/networkmanager-qt/debian/rules')
for tok in ('dh-sequence-qmldeps','libglib2.0-dev','libnm-dev (>= 1.4.0~)','qt6-declarative-dev (>= 6.9.0~)','Package: qml6-module-org-kde-networkmanager'):
    req(tok in nm_control,f'NetworkManagerQt missing {tok}')
for test in ('managertest','settingstest','activeconnectiontest'):
    req(test in nm_rules,f'NetworkManagerQt must document isolated-service exclusion {test}')
req('ARGS+=' in nm_rules and 'dh_auto_test' in nm_rules,'NetworkManagerQt test exclusion must not disable whole suite')

workflow=text(WORKFLOW); runner=text(RUNNER); scope=text(SCOPE); policy=text(POLICY)
for tok in ('runs-on: ubuntu-26.04','fail-fast: false','max-parallel: 3','node: [kidletime, modemmanager-qt, networkmanager-qt]','artifact-ids: \'10298635300\'','artifact-ids: \'10301938362\'','scripts/kde-tier1-package-batch5-needed.sh','scripts/run-kde-tier1-package-batch5-preflight.sh'):
    req(tok in workflow,f'workflow missing {tok}')
req('ubuntu-latest' not in workflow and 'pull_request_target' not in workflow,'workflow unsafe/ambiguous runner trigger')
for tok in ('dpkg-source -b','sbuild --verbose --chroot-mode=unshare','lintian --fail-on error','readelf -d','cmake -S "${CONSUMER_META}"','modemmanager-dev','libnm-dev','libglib2.0-dev','EXPECTED_PACKAGES'):
    req(tok in runner,f'runner missing {tok}')
for node in EXPECTED:
    req(node in scope,f'scope missing {node}')
req('manifests/kde-tier1-package-campaign-batch5.json' in scope and 'binary_contracts' in scope and 'build_profile_tokens' in scope,'scope campaign fingerprint')
req('python3 scripts/validate_kde_tier1_package_batch5.py' in policy,'Repository Policy must execute Batch 5 validator')

for p in (DOC,STATUS,PROVIDER_DOC,DEPENDENCY_DOC):
    t=text(p)
    req('35012023822' in t and '10414525047' in t and 'db6868402b08bca82241d07980e158639a2f2fc64c4a5ab595fa58846361cb4a' in t,f'{p.name}: current provider evidence')
req('open remediation; 2 package PASS, 1 remediation pending' in text(DOC),'Batch 5 document open-remediation state')
req('35014875475' in text(DOC) and '10414598079' in text(DOC) and '10414714325' in text(DOC) and '10415586492' in text(DOC),'Batch 5 document first-attempt evidence')
req('b717475396376ac884bb3587ab2a0e898af5beb940836c45ee834758eec6820f' in text(DOC),'Batch 5 document remediation hash')
req('13 PASS / 16 pending / 0 current FAIL / 0 BLOCKED' in text(DOC),'Batch 5 canonical count')

if errors:
    for x in errors:
        print('ERROR:',x,file=sys.stderr)
    raise SystemExit(1)
print('KDE Tier 1 Batch 5 open-remediation validation: PASS')
print('Selected: kidletime, modemmanager-qt, networkmanager-qt')
print('Canonical state remains: 13 PASS / 16 pending / 0 current FAIL / 0 BLOCKED')
