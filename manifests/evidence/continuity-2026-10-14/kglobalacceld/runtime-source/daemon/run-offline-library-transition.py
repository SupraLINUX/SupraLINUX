#!/usr/bin/env python3
"""Execute reviewed frozen-provider controls in a zero-NIC diagnostic guest."""
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

payload = Path(__file__).resolve().parent
plan = json.loads((payload/'runtime-plan.json').read_text())
out = Path(sys.argv[1]).resolve()
assert str(out) == '/var/tmp/supra-offline-diagnostic'
owned = payload/'project/.work'
config = owned/'runtime-config.json'
result = {'schema': 1, 'state': 'INFRA_INVALID', 'scope': plan['scope'],
          'package_attempt_consumed': False, 'canonical_effect': 'none',
          'compatibility_transition_admitted': False, 'checks': {}, 'phases': {}}

def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()

def save():
    (out/'result.json').write_text(json.dumps(result, indent=2)+'\n')

try:
    assert sorted(p.name for p in Path('/sys/class/net').iterdir()) == ['lo']
    release = Path('/etc/os-release').read_text()
    assert 'VERSION_ID="26.04"' in release and 'VERSION_CODENAME=resolute' in release
    assert subprocess.check_output(['systemd-detect-virt'], text=True).strip() == 'kvm'
    mount = next(line for line in Path('/proc/mounts').read_text().splitlines()
                 if line.split()[1] == str(payload))
    assert 'ro' in mount.split()[3].split(',')
    for rel, digest in plan['critical_inputs'].items():
        assert sha(payload/rel) == digest, 'Frozen input mismatch: '+rel
    result['checks']['frozen_critical_inputs'] = 'PASS'
    alias = Path(plan['original_work_prefix'])
    assert not alias.exists() and not alias.is_symlink()
    alias.parent.mkdir(parents=True, exist_ok=True)
    alias.symlink_to(owned)
    # Only this disposable guest gets the authenticated X server compiler.
    xkb = Path('/usr/bin/xkbcomp')
    if xkb.exists() or xkb.is_symlink():
        result['checks']['replaced_guest_xkbcomp_sha256'] = sha(xkb)
        xkb.rename('/usr/bin/xkbcomp.supra-diagnostic-original')
    xkb.symlink_to(owned/'fixture-inputs/usr/bin/xkbcomp')
    driver = out/'native-driver'
    driver.mkdir()
    for rel in plan['native_driver_files']:
        source = owned/'kglobalacceld-diagnostic-build-20261010/build2'/rel
        target = driver/rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert sha(source) == sha(target)
    cfg = json.loads(config.read_text())
    system_deps = {}
    for item in plan['loader_checks']:
        environment = os.environ.copy()
        environment['LD_LIBRARY_PATH'] = ':'.join(cfg['phases'][item['phase']]['LD_LIBRARY_PATH'])
        probe = subprocess.run(['/usr/bin/ldd',str(owned/item['path'])], env=environment,
                               capture_output=True, text=True, timeout=30)
        logfile = out/('loader-'+item['name']+'.log')
        logfile.write_text(probe.stdout+probe.stderr)
        assert probe.returncode==0 and 'not found' not in probe.stdout+probe.stderr, 'Guest loader prerequisite: '+item['name']
        for found in re.findall(r'(?:=> )?(/[^\s]+)', probe.stdout):
            path = Path(found)
            if path.is_file() and not path.resolve().is_relative_to(payload):
                system_deps[str(path)] = sha(path)
    (out/'guest-system-library-inputs.json').write_text(json.dumps(system_deps,indent=2)+'\n')
    result['checks']['guest_loader_prerequisites'] = 'PASS'
    environment = os.environ.copy()
    environment['PATH'] = str(owned/'fixture-tools')+':/usr/bin:/bin'
    for step in plan['steps']:
        name = step['name']
        fixture = out/('fixture-'+name)
        arguments = [v.replace('{OUTPUT}',str(out)).replace('{DRIVER}',str(driver)) for v in step['arguments']]
        command = ['/usr/bin/python3',str(owned/'run-private.py'),step['kind'],
                   str(owned/'launch-owned-library-process.py'),str(fixture),
                   '--config',str(config),'--phase',step['phase'],'--',*arguments]
        with (out/(name+'-stdout.log')).open('w') as stdout, (out/(name+'-stderr.log')).open('w') as stderr:
            run = subprocess.run(command, env=environment, stdout=stdout, stderr=stderr, timeout=660)
        outcome = 'PASS' if run.returncode==0 else 'FAIL'
        if step.get('negative_symbol'):
            observed = (fixture/'client-stderr').read_text() if (fixture/'client-stderr').exists() else ''
            outcome = 'EXPECTED_ABI_INCOMPATIBILITY' if run.returncode!=0 and step['negative_symbol'] in observed else 'UNEXPECTED_NEGATIVE_CONTROL'
        result['phases'][name] = {'state': outcome,'wrapper_exit_code':run.returncode,
                                 'phase':step['phase'], 'fixture_result':str(fixture)}
        save()
        if step.get('baseline_required') and outcome!='PASS':
            result['state'] = 'BASELINE_CONTROL_FAIL'
            raise RuntimeError('Baseline control failed; dependent candidate execution withheld: '+name)
    for rel, digest in plan['critical_inputs'].items():
        assert sha(payload/rel) == digest
    result['checks']['frozen_inputs_after_execution'] = 'PASS'
    required = [v['state']=='PASS' for k,v in result['phases'].items() if not k.startswith('negative-')]
    result['state'] = 'SCOPED_DIAGNOSTIC_PASS' if all(required) else 'SCOPED_DIAGNOSTIC_FAIL'
except Exception as error:
    result['error'] = str(error)
finally:
    save()
print(json.dumps({'state':result['state'],'phases':result['phases'],'canonical_effect':'none'}))
raise SystemExit(0 if result['state']=='SCOPED_DIAGNOSTIC_PASS' else 1)
