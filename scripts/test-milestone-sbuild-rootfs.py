#!/usr/bin/env python3
"""Exercise immutable clean base admission and current APT suites."""
import importlib.machinery
import io
import ssl
import tarfile
import tempfile
import unittest
from pathlib import Path

MODULE = importlib.machinery.SourceFileLoader('rootfs', str(Path(__file__).with_name('prepare-milestone-sbuild-rootfs.py'))).load_module()


class RootfsTests(unittest.TestCase):
    def base(self, directory, version='26.04', extra=''):
        path = Path(directory)/'base.tar'
        files = {'usr/lib/os-release':f'ID=ubuntu\nVERSION_ID="{version}"\nVERSION_CODENAME=resolute\n',
                 'var/lib/dpkg/status':'Package: apt\nVersion: 3.2\nArchitecture: amd64\nStatus: install ok installed\n\n'+extra,
                 'usr/share/keyrings/ubuntu-archive-keyring.gpg':'fixture keyring',
                 'etc/apt/sources.list':'deb https://obsolete.invalid old main\n',
                 'etc/apt/sources.list.d/old.sources':'Types: deb\nURIs: https://obsolete.invalid\n',
                 'usr/bin/fixture':'unchanged base bytes'}
        with tarfile.open(path,'w') as archive:
            for name,text in files.items():
                entry = tarfile.TarInfo('./'+name)
                data = text.encode(); entry.size = len(data); entry.mode = 0o755
                archive.addfile(entry,io.BytesIO(data))
        return path,MODULE.sha(path)

    def test_clean_reuse_keeps_bytes_and_replaces_only_apt_sources(self):
        with tempfile.TemporaryDirectory() as temp:
            base,digest = self.base(temp)
            output = Path(temp)/'derived.tar'
            result = MODULE.derive(base,digest,output,'http://archive.ubuntu.com/ubuntu')
            self.assertEqual(MODULE.sha(base),digest)
            self.assertFalse(result['frameworks_and_qt_sdk_preinstalled'])
            self.assertTrue(result['requires_sbuild_apt_update_and_distupgrade'])
            with tarfile.open(output) as archive:
                self.assertNotIn('./etc/apt/sources.list.d/old.sources',archive.getnames())
                self.assertEqual(archive.extractfile('./usr/bin/fixture').read(),b'unchanged base bytes')
                sources = archive.extractfile('./etc/apt/sources.list').read().decode()
                self.assertEqual(sources,result['apt_sources'])
                for suite in MODULE.SUITES:
                    self.assertIn(' '+suite+' main universe\n',sources)
                self.assertEqual(archive.getnames().count('./etc/apt/sources.list'),1)

    def test_rejects_tampering_wrong_release_or_preinstalled_sdk(self):
        for version,extra,bad_digest in [('26.04','',True),('25.10','',False),
                ('26.04','Package: libqt6core6\nVersion: 6.10\nArchitecture: amd64\nStatus: install ok installed\n',False),
                ('26.04','Package: libkf6i18n6\nVersion: 6.30\nArchitecture: amd64\nStatus: install ok installed\n',False)]:
            with self.subTest(version=version,extra=extra), tempfile.TemporaryDirectory() as temp:
                base,digest = self.base(temp,version,extra)
                with self.assertRaises(AssertionError):
                    MODULE.derive(base,'0'*64 if bad_digest else digest,Path(temp)/'derived.tar','http://archive.ubuntu.com/ubuntu')
                self.assertFalse((Path(temp)/'derived.tar').exists())

    def test_rejects_base_mutation_and_unexpected_mirror(self):
        with tempfile.TemporaryDirectory() as temp:
            base,digest = self.base(temp)
            for output,mirror in [(base,'http://archive.ubuntu.com/ubuntu'),(Path(temp)/'derived.tar','http://evil.invalid/ubuntu')]:
                with self.assertRaises(AssertionError):
                    MODULE.derive(base,digest,output,mirror)
            self.assertEqual(MODULE.sha(base),digest)

    def test_https_bootstraps_recorded_ca_bytes_without_changing_base_or_keyring(self):
        with tempfile.TemporaryDirectory() as temp:
            base,digest = self.base(temp)
            bundle = Path(temp)/'ca.pem'
            certificate = ssl.create_default_context().get_ca_certs(binary_form=True)[0]
            bundle.write_text(ssl.DER_cert_to_PEM_cert(certificate))
            output = Path(temp)/'https.tar'
            provider = {'package':'ca-certificates','source_package':'ca-certificates','version':'fixture','architecture':'all'}
            result = MODULE.derive(base,digest,output,'https://archive.ubuntu.com/ubuntu',bundle,provider)
            self.assertEqual(MODULE.sha(base),digest)
            self.assertEqual(result['tls_bootstrap']['sha256'],MODULE.sha(bundle))
            self.assertEqual(result['tls_bootstrap']['provider'],provider)
            self.assertFalse(result['tls_bootstrap']['certificate_verification_disabled'])
            self.assertFalse(result['frameworks_and_qt_sdk_preinstalled'])
            with tarfile.open(output) as archive:
                self.assertEqual(archive.extractfile('./etc/ssl/certs/ca-certificates.crt').read(),bundle.read_bytes())
                self.assertEqual(archive.extractfile('./usr/share/keyrings/ubuntu-archive-keyring.gpg').read(),b'fixture keyring')
                self.assertEqual(archive.extractfile('./usr/bin/fixture').read(),b'unchanged base bytes')
                self.assertEqual(archive.getnames().count('./etc/ssl/certs/ca-certificates.crt'),1)
                self.assertEqual(archive.extractfile('./'+MODULE.TLS_APT_CONFIG).read(),MODULE.TLS_APT_SETTINGS.encode())
                self.assertIn('CaInfo "/etc/ssl/certs/ca-certificates.crt"',MODULE.TLS_APT_SETTINGS)
                self.assertNotIn('Verify-Peer "false"',MODULE.TLS_APT_SETTINGS)
                self.assertNotIn('Verify-Host "false"',MODULE.TLS_APT_SETTINGS)
                self.assertTrue(result['tls_bootstrap']['apt_update_requires_all_indexes'])
                self.assertIn('https://archive.ubuntu.com/ubuntu',result['apt_sources'])

    def test_https_rejects_missing_empty_or_invalid_trust_and_http_rejects_injection(self):
        with tempfile.TemporaryDirectory() as temp:
            base,digest = self.base(temp)
            bundle = Path(temp)/'ca.pem'
            for data in ['', 'untrusted non-certificate data']:
                bundle.write_text(data)
                with self.assertRaises((AssertionError,ssl.SSLError)):
                    MODULE.derive(base,digest,Path(temp)/'https.tar','https://archive.ubuntu.com/ubuntu',bundle)
                self.assertFalse((Path(temp)/'https.tar').exists())
            with self.assertRaises(AssertionError):
                MODULE.derive(base,digest,Path(temp)/'https.tar','https://archive.ubuntu.com/ubuntu')
            with self.assertRaises(AssertionError):
                MODULE.derive(base,digest,Path(temp)/'http.tar','http://archive.ubuntu.com/ubuntu',bundle)
            self.assertEqual(MODULE.sha(base),digest)


if __name__ == '__main__':
    unittest.main()
