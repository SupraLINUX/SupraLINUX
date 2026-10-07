#!/usr/bin/env python3
"""Derive a clean Ubuntu buildd tarball without preinstalling package SDKs."""
import argparse
import datetime
import hashlib
import io
import importlib.machinery
import json
import re
import ssl
import subprocess
import tarfile
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
prepare = importlib.machinery.SourceFileLoader('package_prepare', str(ROOT/'scripts/prepare-plasma-package.py')).load_module()
SUITES = ['resolute', 'resolute-updates', 'resolute-security']


def sha(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def derive(base, expected_sha, output, mirror, tls_ca_bundle=None, tls_provider=None):
    assert base.resolve() != output.resolve(), 'Never mutate the immutable base'
    assert not output.exists(), 'Refusing to replace an existing derived rootfs'
    assert sha(base) == expected_sha, 'Bare rootfs digest mismatch'
    url = urlsplit(mirror)
    assert url.scheme in {'http', 'https'} and url.netloc == 'archive.ubuntu.com' and url.path.rstrip('/') == '/ubuntu'
    assert not url.query and not url.fragment, 'Unexpected Ubuntu mirror'
    tls_data = None
    if url.scheme == 'https':
        assert tls_ca_bundle is not None, 'HTTPS requires an explicit verified runner CA bundle'
        tls_data = tls_ca_bundle.read_bytes()
        assert tls_data, 'Empty TLS CA trust store'
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.load_verify_locations(cadata=tls_data.decode('ascii'))
        assert context.cert_store_stats()['x509_ca'] > 0, 'Empty TLS CA trust store'
    else:
        assert tls_ca_bundle is None and tls_provider is None, 'HTTP must not inject TLS trust data'
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
    # Preserve the immutable base; replace APT sources and, for HTTPS only,
    # bootstrap the runner's recorded CA data without installing any SDK.
    output.parent.mkdir(parents=True,exist_ok=True)
    temporary = output.with_suffix(output.suffix+'.tmp')
    try:
        with tarfile.open(base,'r|') as source, tarfile.open(temporary,'w|',format=tarfile.PAX_FORMAT) as target:
            for member in source:
                name = member.name.removeprefix('./')
                if name.startswith('etc/apt/') and name.endswith(('.list','.sources')):
                    continue
                if tls_data is not None and name == 'etc/ssl/certs/ca-certificates.crt':
                    continue
                target.addfile(member, source.extractfile(member) if member.isfile() else None)
            entry = tarfile.TarInfo('./etc/apt/sources.list')
            data = sources.encode()
            entry.size = len(data)
            entry.mode = 0o644
            target.addfile(entry,io.BytesIO(data))
            if tls_data is not None:
                entry = tarfile.TarInfo('./etc/ssl/certs/ca-certificates.crt')
                entry.size = len(tls_data)
                entry.mode = 0o644
                target.addfile(entry,io.BytesIO(tls_data))
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    result = {'state':'PASS', 'kind':'immutable-bare-milestone-rootfs-admission', 'cache_only':True,
            'base_sha256':expected_sha, 'derived_sha256':sha(output), 'base_path':str(base), 'derived_path':str(output),
            'ubuntu_archive_keyring_sha256':keyring_sha, 'mirror':mirror, 'suites':SUITES,
            'apt_sources':sources, 'installed_base_packages':sorted(installed,key=lambda item:item['package']),
            'frameworks_and_qt_sdk_preinstalled':False, 'package_attempt_consumed':False,
            'requires_sbuild_apt_update_and_distupgrade':True,
            'admitted_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    if tls_data is not None:
        result['tls_bootstrap'] = {'scope':'APT transport trust data only; no package preinstallation',
                                   'source_path':str(tls_ca_bundle),
                                   'sha256':hashlib.sha256(tls_data).hexdigest(),
                                   'size':len(tls_data),
                                   'provider':tls_provider,
                                   'certificate_verification_disabled':False}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('node')
    parser.add_argument('--payload',type=Path,default=Path('/var/lib/supralinux/milestones/frameworks-6.30'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--evidence',type=Path,required=True)
    parser.add_argument('--mirror',default='http://archive.ubuntu.com/ubuntu')
    parser.add_argument('--tls-ca-bundle',type=Path)
    args = parser.parse_args()
    campaign = prepare.load_campaign()
    assert campaign['execution_checkpoint'] == 'frameworks-6.30-pass'
    policy = campaign['nodes'][args.node]['sbuild_rootfs_policy']
    assert policy['kind'] == 'immutable-bare-milestone' and policy['suites'] == SUITES
    provenance = dict(line.split('=',1) for line in (args.payload/'checkpoint-manifest.txt').read_text().splitlines() if '=' in line)
    assert provenance['sbuild_rootfs_sha256'] == policy['sha256']
    assert provenance['cache_only'] == 'yes' and provenance['framework_packages_preinstalled_in_sbuild_rootfs'] == 'no'
    tls_provider = None
    if args.tls_ca_bundle is not None:
        assert args.tls_ca_bundle == Path('/etc/ssl/certs/ca-certificates.crt'), 'Use the authoritative runner trust store'
        metadata = subprocess.check_output(['dpkg-query','-W','-f=${Package}\n${source:Package}\n${Version}\n${Architecture}\n${Status}',
                                            'ca-certificates'],text=True).splitlines()
        assert len(metadata) == 5 and metadata[:2] == ['ca-certificates','ca-certificates']
        assert metadata[3:] == ['all','install ok installed']
        assert args.tls_ca_bundle.stat().st_uid == 0 and not args.tls_ca_bundle.stat().st_mode & 0o022
        tls_provider = dict(zip(['package','source_package','version','architecture','status'],metadata))
        tls_provider['authority'] = 'Ubuntu package on the admitted authoritative runner image'
    result = derive(args.payload/'sbuild/resolute-amd64.tar',policy['sha256'],args.output,args.mirror,
                    args.tls_ca_bundle,tls_provider)
    if args.tls_ca_bundle is not None:
        capture = args.evidence.parent/'rootfs-ca-certificates.crt'
        assert not capture.exists(), 'Refusing to replace retained TLS trust data'
        data = args.tls_ca_bundle.read_bytes()
        assert hashlib.sha256(data).hexdigest() == result['tls_bootstrap']['sha256'], 'TLS trust data changed during admission'
        capture.write_bytes(data)
        result['tls_bootstrap']['bundle_evidence_file'] = capture.name
    args.evidence.write_text(json.dumps(result,indent=2)+'\n')
    print(f"Bare milestone rootfs admission: PASS; {len(result['installed_base_packages'])} base packages; no Frameworks/Qt SDK")


if __name__ == '__main__':
    main()
