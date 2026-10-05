#!/usr/bin/env python3
"""Derive a clean Ubuntu buildd tarball without preinstalling package SDKs."""
import argparse
import datetime
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SUITES = ['resolute', 'resolute-updates', 'resolute-security']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def derive(base, expected_sha, output, mirror):
    assert base.resolve() != output.resolve(), 'Never mutate the immutable base'
    assert not output.exists(), 'Refusing to replace an existing derived rootfs'
    assert sha(base) == expected_sha, 'Bare rootfs digest mismatch'
    url = urlsplit(mirror)
    assert url.scheme in {'http', 'https'} and url.netloc == 'archive.ubuntu.com' and url.path.rstrip('/') == '/ubuntu'
    assert not url.query and not url.fragment, 'Unexpected Ubuntu mirror'
    sources = ''.join(f'deb [signed-by=/usr/share/keyrings/ubuntu-archive-keyring.gpg] {mirror.rstrip("/")} {suite} main universe\n' for suite in SUITES)
    with tarfile.open(base) as archive:
        members = {member.name.removeprefix('./'):member for member in archive}
        def read(name):
            member = members[name]
            assert member.isfile(), f'Expected regular rootfs metadata: {name}'
            return archive.extractfile(member).read()
        release = dict(line.split('=',1) for line in read('usr/lib/os-release').decode().splitlines() if '=' in line)
        assert release['ID'] == 'ubuntu' and release['VERSION_ID'].strip('"') == '26.04'
        assert release['VERSION_CODENAME'] == 'resolute'
        installed = []
        for stanza in read('var/lib/dpkg/status').decode().split('\n\n'):
            fields = dict(line.split(': ',1) for line in stanza.splitlines() if ': ' in line and not line.startswith(' '))
            if fields.get('Status') == 'install ok installed':
                installed.append({'package':fields['Package'], 'version':fields['Version'], 'architecture':fields['Architecture']})
        assert installed and all(item['architecture'] in {'amd64', 'all'} for item in installed)
        forbidden = [item['package'] for item in installed if re.match(r'^(libkf6|kf6-|qt6-|libqt6|qml6-|extra-cmake-modules$|cmake$|debhelper)',item['package'])]
        assert not forbidden, f'SDK packages preinstalled in bare rootfs: {forbidden}'
        keyring_sha = hashlib.sha256(read('usr/share/keyrings/ubuntu-archive-keyring.gpg')).hexdigest()
    # Preserve the buildd filesystem byte-for-byte; replace only APT source entries.
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary = output.with_suffix(output.suffix+'.tmp')
    try:
        with tarfile.open(base,'r|') as source, tarfile.open(temporary,'w|',format=tarfile.PAX_FORMAT) as target:
            for member in source:
                name = member.name.removeprefix('./')
                if name.startswith('etc/apt/') and name.endswith(('.list','.sources')):
                    continue
                target.addfile(member, source.extractfile(member) if member.isfile() else None)
            entry = tarfile.TarInfo('./etc/apt/sources.list')
            data = sources.encode()
            entry.size = len(data)
            entry.mode = 0o644
            target.addfile(entry,io.BytesIO(data))
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return {'state':'PASS', 'kind':'immutable-bare-milestone-rootfs-admission', 'cache_only':True,
            'base_sha256':expected_sha, 'derived_sha256':sha(output), 'base_path':str(base), 'derived_path':str(output),
            'ubuntu_archive_keyring_sha256':keyring_sha, 'mirror':mirror, 'suites':SUITES,
            'apt_sources':sources, 'installed_base_packages':sorted(installed,key=lambda item:item['package']),
            'frameworks_and_qt_sdk_preinstalled':False, 'package_attempt_consumed':False,
            'requires_sbuild_apt_update_and_distupgrade':True,
            'admitted_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node')
    parser.add_argument('--payload',type=Path,default=Path('/var/lib/supralinux/milestones/frameworks-6.30'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--mirror',default='http://archive.ubuntu.com/ubuntu')
    args = parser.parse_args()
    campaign = json.loads((ROOT/'manifests/kde-plasma-package-build.json').read_text())
    assert campaign['execution_checkpoint'] == 'frameworks-6.30-pass'
    policy = campaign['nodes'][args.node]['sbuild_rootfs_policy']
    assert policy['kind'] == 'immutable-bare-milestone' and policy['suites'] == SUITES
    provenance = dict(line.split('=',1) for line in (args.payload/'checkpoint-manifest.txt').read_text().splitlines() if '=' in line)
    assert provenance['sbuild_rootfs_sha256'] == policy['sha256']
    assert provenance['cache_only'] == 'yes' and provenance['framework_packages_preinstalled_in_sbuild_rootfs'] == 'no'
    result = derive(args.payload/'sbuild/resolute-amd64.tar',policy['sha256'],args.output,args.mirror)
    args.evidence.write_text(json.dumps(result,indent=2)+'\n')
    print(f"Bare milestone rootfs admission: PASS; {len(result['installed_base_packages'])} base packages; no Frameworks/Qt SDK")


if __name__ == '__main__':
    main()
