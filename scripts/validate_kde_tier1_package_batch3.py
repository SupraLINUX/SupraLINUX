#!/usr/bin/env python3
from __future__ import annotations
import hashlib, json, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CAMPAIGN = ROOT / 'manifests/kde-tier1-package-campaign-batch3.json'
TIER1 = ROOT / 'manifests/kde-frameworks-tier1.json'
DAG = ROOT / 'manifests/kde-dag.json'
DOC = ROOT / 'docs/kde-tier1-package-batch3.md'
WORKFLOW = ROOT / '.github/workflows/kde-tier1-package-batch3.yml'
RUNNER = ROOT / 'scripts/run-kde-tier1-package-batch3-preflight.sh'
SCOPE = ROOT / 'scripts/kde-tier1-package-batch3-needed.sh'
EXPECTED = {
    'kitemmodels': {
        'state': 'PASS', 'version': '6.30.0-0supralinux1',
        'source': 'f807e5b37aa913d2563ee1a21b2bce7d34495f32f38c7f35f16262d736bdfd55',
        'symbols': 'd9cbc25df40c2ea378cb8e3e77dafcea63a7b542315dc90498cb27f087db1c1e',
        'runtime': 'libkf6itemmodels6', 'soname': 'libKF6ItemModels.so.6',
        'build': ['dh-sequence-qmldeps', 'qt6-base-dev (>= 6.9.0~)', 'qt6-declarative-dev (>= 6.9.0~)', 'qt6-tools-dev (>= 6.9.0~)'],
        'artifact': 10369501432, 'artifact_sha256': 'b806eaf27f733c1a2b5cc1d108ca442fef673b6dc0a53cfc5fff38abd2bf6732',
    },
    'bluez-qt': {
        'state': 'remediation-pending-build', 'version': '6.30.0-0supralinux2',
        'source': 'f5045b14a6c689bbfded9437582f943dd4f8f74537085ab6115bcacdea2110d8',
        'symbols': 'b72bea28842160da234b3bbab7975623616cd58f3e522b1e5d8705a279eef4f7',
        'runtime': 'libkf6bluezqt6', 'soname': 'libKF6BluezQt.so.6',
        'build': ['dh-sequence-qmldeps', 'dbus-daemon <!nocheck>', 'python3', 'qt6-base-dev (>= 6.9.0~)', 'qt6-declarative-dev (>= 6.9.0~)', 'qt6-tools-dev (>= 6.9.0~)'],
        'artifact': 10369725265, 'artifact_sha256': 'ab85b1c2eeef6bf2dc9d622d6695b95427cca6e246ac13a0f825034e9e63d195',
    },
    'kplotting': {
        'state': 'PASS', 'version': '6.30.0-0supralinux1',
        'source': 'f5a67be85c21665e052371301889443196b9de5b3927aff353a3d3e27730dd11',
        'symbols': 'de5fddb29e85c05edefee280b2acf547d285318e6334b63b4a58527f59260cdb',
        'runtime': 'libkf6plotting6', 'soname': 'libKF6Plotting.so.6',
        'build': ['qt6-base-dev (>= 6.9.0~)', 'qt6-tools-dev (>= 6.9.0~)'],
        'artifact': 10369086459, 'artifact_sha256': 'f4c4f7425e582b5001fdffced34d045dc46152074422bd2bcf994e544bb96bb8',
    },
}
errors: list[str] = []

def req(value: bool, message: str) -> None:
    if not value:
        errors.append(message)

def load(path: Path):
    return json.loads(path.read_text())

def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

c = load(CAMPAIGN)
tier = {x['id']: x for x in load(TIER1)['nodes']}
dag = load(DAG)['nodes']
req(c.get('schema') == 1, 'schema')
req(c.get('authority') == 'kde-upstream', 'authority')
req(c.get('frameworks_series') == '6.30.0', 'Frameworks')
req(c.get('batch') == 'tier1-batch-3', 'batch')
req(c.get('state') == 'remediation-pending-build', 'Batch 3 remediation state')
req(c.get('selected_nodes') == list(EXPECTED), 'selected nodes')
req(c['selection_rationale']['deferred'].get('kconfig', '').startswith('Deferred because KConfig exports multiple ABI'), 'KConfig deferral rationale')
req(c['shared_predecessors']['extra_cmake_modules']['version'] == '6.30.0-0supralinux3', 'ECM')
req(c['shared_packaging_inputs']['documentation_policy']['qch_enabled'] is False, 'QCH policy')
req(c['shared_packaging_inputs']['lintian_policy']['source_and_changes_required'] is True, 'Lintian policy')

for n, e in EXPECTED.items():
    x = c['nodes'][n]
    req(x['state'] == e['state'], f'{n}: state')
    req(x['package_version'] == e['version'], f'{n}: revision')
    req(x['source_sha256'] == e['source'], f'{n}: source')
    req(x['symbols']['sha256'] == e['symbols'], f'{n}: symbols')
    req(x['symbols']['tree_provider'] == 'debian', f'{n}: symbols provider')
    req(x['runtime_package'] == e['runtime'], f'{n}: runtime')
    req(x['soname'] == e['soname'], f'{n}: soname')
    req(bool(x['evidence']), f'{n}: attempt evidence required')
    req(x['evidence'][0]['workflow_run'] == 34896417969, f'{n}: run evidence')
    req(x['evidence'][0]['artifact_id'] == e['artifact'], f'{n}: artifact id')
    req(x['evidence'][0]['artifact_sha256'] == e['artifact_sha256'], f'{n}: artifact sha256')
    d = ROOT / 'packages/kde' / n / 'debian'
    control = (d / 'control').read_text()
    rules = (d / 'rules').read_text()
    readme = (d / 'README.source').read_text()
    docinstall = (d / x['documentation_package'].replace('-doc', '-doc.install')).read_text()
    consumer = (ROOT / 'packages/kde' / n / 'consumer/CMakeLists.txt').read_text()
    main = (ROOT / 'packages/kde' / n / 'consumer/main.cpp').read_text()
    for tok in ['debhelper-compat (= 13)', 'dh-sequence-kf6', 'dh-sequence-pkgkde-symbolshelper', 'cmake (>= 3.29~)', 'extra-cmake-modules (>= 6.30.0~)', *e['build']]:
        req(tok in control, f'{n}: missing {tok}')
    req('Standards-Version: 4.7.3' in control, f'{n}: standards')
    req('documentation compatibility package' in control, f'{n}: doc desc')
    req('does not ship QCH documentation files' in control, f'{n}: QCH truth')
    req('Intentionally empty' in docinstall, f'{n}: empty doc install')
    req('-DBUILD_QCH=OFF' in rules, f'{n}: QCH disabled')
    req('dh_auto_test' in rules, f'{n}: tests enabled')
    req('KDE Frameworks 6.30.0 is the source/build authority' in readme, f'{n}: authority doc')
    req(sha(d / 'upstream/signing-key.asc') == '86b56008ff74b4473b0d6ad9f01ca5e40e9ff951bc9be1ff362ce97e396ca17d', f'{n}: key')
    req(x['cmake_package'] in consumer and x['cmake_target'] in consumer, f'{n}: cmake consumer')
    req(e['soname'] in main and 'dlopen' in main, f'{n}: runtime consumer')
    req(tier[n]['state'] == 'pending' and tier[n]['packaging'] == {'state': 'pending'}, f'{n}: canonical state must remain pending until Batch 3 closes')
    dag_node = dag.get(n)
    req(dag_node is None or dag_node.get('state') == 'pending', f'{n}: DAG must remain pending until Batch 3 closes')

bluez = c['nodes']['bluez-qt']
override = bluez['symbols'].get('reviewed_override', {})
req(bluez['last_result'] == 'FAIL' and bluez['downstream_eligible'] is False, 'bluez-qt: FAIL must remain non-eligible before remediation build')
req(bluez['evidence'][0].get('tests') == '18/18 PASS', 'bluez-qt: preserve passing upstream tests from fail attempt')
req(bluez['evidence'][0].get('failure_substage') == 'lintian', 'bluez-qt: failure substage')
req(override.get('method') == 'deterministic-transform', 'bluez-qt: reviewed symbols transform')
req(override.get('file_sha256') == '6e7f4a36c5b5b71c80728c23da82180af0772b4d9abf2f3feb834ffda0007565', 'bluez-qt: transform sha')
req(override.get('result_sha256') == '0fd10c9d93b303fa48aa5cd66aaf4727fbc27f4b784926f5ce5f8d20606bf37a', 'bluez-qt: reviewed symbols result sha')
transform = ROOT / 'packages/kde/bluez-qt/debian/apply-symbols-delta.py'
req(transform.exists(), 'bluez-qt: transform missing')
if transform.exists():
    req(sha(transform) == override.get('file_sha256'), 'bluez-qt: transform file hash mismatch')
bluez_rules = (ROOT / 'packages/kde/bluez-qt/debian/rules').read_text()
req('python3 debian/apply-symbols-delta.py' in bluez_rules, 'bluez-qt: transform must run before dh_makeshlibs')
req(bluez_rules.find('python3 debian/apply-symbols-delta.py') < bluez_rules.find('dh_makeshlibs'), 'bluez-qt: symbols transform order')

for n in ('kitemmodels', 'kplotting'):
    x = c['nodes'][n]
    req(x['last_result'] == 'PASS' and x['downstream_eligible'] is True, f'{n}: retained PASS evidence')

runner = RUNNER.read_text(); workflow = WORKFLOW.read_text(); scope = SCOPE.read_text(); doc = DOC.read_text()
for tok in ["-name '*.ddeb'", 'lintian --fail-on error "${DSC}" "${CHANGES[0]}"', 'Lintian:[[:space:]]+fail', 'dpkg-source -b', '--chroot-mode=unshare', 'consumer-smoke']:
    req(tok in runner, f'runner missing {tok}')
for tok in ['fail-fast: false', 'max-parallel: 3', 'kitemmodels', 'bluez-qt', 'kplotting', 'run-kde-tier1-package-batch3-preflight.sh']:
    req(tok in workflow, f'workflow missing {tok}')
req('kde-tier1-package-campaign-batch3.json' in scope, 'scope campaign')
req('KConfig' in doc and 'multi-library' in doc, 'docs KConfig deferral')
req('KItemModels' in doc and '13/13' in doc and 'KPlotting' in doc and '5/5' in doc, 'docs PASS evidence')
req('18/18' in doc and '_ZSt19piecewise_construct' in doc, 'docs BluezQt FAIL evidence')
req('7 PASS / 22 pending / 0 current FAIL / 0 BLOCKED' in doc, 'docs canonical pre-closure state')

if errors:
    for e in errors:
        print('ERROR:', e, file=sys.stderr)
    raise SystemExit(1)
print('KDE Tier 1 Batch 3 remediation validation: PASS')
print('KItemModels/KPlotting retained PASS; BluezQt 6.30.0-0supralinux2 remediation pending; canonical Tier 1 remains 7 PASS / 22 pending until batch closure.')
