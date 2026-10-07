#!/usr/bin/env python3
"""Regression checks for source admission and substantive theme validation."""
import copy
import hashlib
import importlib.machinery
import json
import os
import pty
import re
import select
import shlex
import subprocess
import struct
import zlib
import tempfile
import termios
import time
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
testing = importlib.machinery.SourceFileLoader("testing", str(ROOT / "scripts/plasma-package-testing.py")).load_module()
prepare = importlib.machinery.SourceFileLoader("prepare", str(ROOT / "scripts/prepare-plasma-package.py")).load_module()
resources = importlib.machinery.SourceFileLoader("resources", str(ROOT / "packages/plasma/breeze-grub/debian/tests/theme-resources")).load_module()
sounds = importlib.machinery.SourceFileLoader("sounds", str(ROOT / "packages/plasma/ocean-sound-theme/debian/tests/sound-resources")).load_module()
wallpapers = importlib.machinery.SourceFileLoader("wallpapers", str(ROOT / "packages/plasma/plasma-workspace-wallpapers/debian/tests/wallpaper-resources")).load_module()
admission = importlib.machinery.SourceFileLoader("admission", str(ROOT / "scripts/admit-reviewed-plasma-level0-package.py")).load_module()


class InputAdmission(unittest.TestCase):
    def test_https_testbed_transport_preserves_ubuntu_signing_and_other_origins(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'etc/ssl/certs').mkdir(parents=True)
            (root/'etc/ssl/certs/ca-certificates.crt').write_bytes(b'fixture trust data')
            sources = root/'etc/apt/sources.list.d'
            sources.mkdir(parents=True)
            original = (b'Types: deb\r\nURIs: http://archive.ubuntu.com/ubuntu\r\n'
                        b'Suites: resolute resolute-updates\r\n'
                        b'Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg\r\n')
            (sources/'ubuntu.sources').write_bytes(original)
            other = (b'deb http://security.ubuntu.com/ubuntu/ resolute-security main\n'
                     b'deb https://archive.ubuntu.com/ubuntu resolute main\n'
                     b'deb http://example.org/ubuntu resolute main\n'
                     b'deb http://archive.ubuntu.com/ubuntu-other resolute main\n')
            (sources/'mixed.list').write_bytes(other)
            self.assertEqual(testing.configure_ubuntu_apt_https(root),
                             ['etc/apt/sources.list.d/mixed.list', 'etc/apt/sources.list.d/ubuntu.sources'])
            self.assertEqual((sources/'ubuntu.sources').read_bytes(), original.replace(b'http:', b'https:'))
            self.assertEqual((sources/'mixed.list').read_bytes(),
                             other.replace(b'http://security.ubuntu.com/ubuntu/', b'https://security.ubuntu.com/ubuntu/'))
            self.assertEqual(testing.configure_ubuntu_apt_https(root), [])

    def test_https_testbed_transport_rejects_missing_trust_and_escaping_sources(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)/'root'
            (root/'etc/apt').mkdir(parents=True)
            sources = root/'etc/apt/sources.list'
            original = b'deb http://archive.ubuntu.com/ubuntu resolute main\n'
            sources.write_bytes(original)
            with self.assertRaisesRegex(AssertionError, 'trust store is missing'):
                testing.configure_ubuntu_apt_https(root)
            self.assertEqual(sources.read_bytes(), original)
            (root/'etc/ssl/certs').mkdir(parents=True)
            (root/'etc/ssl/certs/ca-certificates.crt').write_bytes(b'fixture trust data')
            outside = Path(directory)/'outside.list'
            outside.write_bytes(original)
            sources.unlink()
            sources.symlink_to(outside)
            with self.assertRaisesRegex(AssertionError, 'escapes the disposable testbed'):
                testing.configure_ubuntu_apt_https(root)
            self.assertEqual(outside.read_bytes(), original)

    def test_https_setup_executes_before_apt_on_bounded_serial_lines(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'etc/ssl/certs').mkdir(parents=True)
            (root/'etc/ssl/certs/ca-certificates.crt').write_bytes(b'fixture trust data')
            (root/'etc/apt').mkdir()
            source = root/'etc/apt/sources.list'
            source.write_bytes(b'deb http://archive.ubuntu.com/ubuntu resolute main\n')
            record = {'ubuntu_baseline_package': 'baseline-fixture', 'version': '2.0'}
            commands = testing.setup_commands(root, record, https_transport=True)
            subprocess.run(['bash', '-n'], input=commands, text=True, check=True)
            self.assertLess(commands.index('configure_ubuntu_apt_https(Path'), commands.index('apt-get update'))
            self.assertLess(max(len(line.encode()) for line in ('sh -ec '+shlex.quote(commands)).splitlines()), 1024)
            # Execute the actual generated preamble against this disposable fixture only.
            preamble = commands.split('apt-get update', 1)[0].replace('Path("/")', 'Path('+repr(str(root))+')')
            subprocess.run(['bash', '-ec', preamble], capture_output=True, text=True, check=True)
            self.assertEqual(source.read_bytes(), b'deb https://archive.ubuntu.com/ubuntu resolute main\n')
            self.assertNotIn('configure_ubuntu_apt_https', testing.setup_commands(root, record))

    def test_supplementary_admission_rejects_authority_reference_and_scope_drift(self):
        node = 'plasma-wayland-protocols'
        record = copy.deepcopy(json.loads((ROOT/'manifests/kde-plasma-package-build.json').read_text())['nodes'][node])
        record.update(state='build-pending',attempts=[])
        level = json.loads((ROOT/'manifests/kde-plasma-level0.json').read_text())
        material = {item['node']:item for item in json.loads((ROOT/'manifests/evidence/kde-plasma-level0-materialization-result.json').read_text())['nodes']}
        packaging = ROOT/record['packaging_path']
        admission.check(node,record,packaging,level,material)
        for key,value in [('upstream_sha256','0'*64),('upstream_url','https://unreviewed.invalid/source'),
                          ('signature_sha256','0'*64),('signing_fingerprint','0'*40),
                          ('packaging_reference_sha256','0'*64),('packaging_reference_version','1.22.0-1'),
                          ('signing_key_path','packages/plasma/other/key.asc'),('source_scope','plasma-level0'),
                          ('version','1.20.0-1'),('binary_packages',{'unexpected':'amd64'})]:
            bad=copy.deepcopy(record);bad[key]=value
            with self.subTest(key=key),self.assertRaises((AssertionError,ValueError,subprocess.CalledProcessError)):
                admission.check(node,bad,packaging,level,material)
        bad_level=copy.deepcopy(level);bad_level['selected_nodes'].append(node)
        with self.assertRaisesRegex(AssertionError,'must not impersonate'):
            admission.check(node,record,packaging,bad_level,material)

    def test_review_admission_rejects_source_binary_and_path_drift(self):
        node='plasma-workspace-wallpapers'
        record=copy.deepcopy(json.loads((ROOT/'manifests/kde-plasma-package-build.json').read_text())['nodes'][node])
        record.update(state='build-pending',attempts=[])
        level=json.loads((ROOT/'manifests/kde-plasma-level0.json').read_text())
        material={item['node']:item for item in json.loads((ROOT/'manifests/evidence/kde-plasma-level0-materialization-result.json').read_text())['nodes']}
        packaging=ROOT/record['packaging_path']
        admission.check(node,record,packaging,level,material)
        for key,value in [('upstream_sha256','0'*64),('upstream_url','https://unreviewed.invalid/source'),
                          ('packaging_path','../outside'),('binary_packages',{'unexpected':'amd64'}),
                          ('packaging_review','REVIEW_REQUIRED')]:
            bad=copy.deepcopy(record);bad[key]=value
            with self.subTest(key=key),self.assertRaises(AssertionError):
                admission.check(node,bad,packaging,level,material)

    def test_wallpaper_png_date_normalization_preserves_pixels_and_other_metadata(self):
        def chunk(tag,data):
            return struct.pack('>I',len(data))+tag+data+struct.pack('>I',zlib.crc32(tag+data)&0xffffffff)
        def png(date,title='signed author',pixel=b'\0\0\0\xff'):
            return (b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',1,1,8,6,0,0,0))+
                    chunk(b'tEXt',b'date:create\0'+date.encode())+chunk(b'tEXt',b'date:modify\0'+date.encode())+
                    chunk(b'tEXt',b'Author\0'+title.encode())+chunk(b'IDAT',zlib.compress(b'\0'+pixel))+chunk(b'IEND',b''))
        original = wallpapers.resource_hash(png('2020-09-11T22:08:25+02:00'),'test.png')
        self.assertEqual(original,wallpapers.resource_hash(png('2026-10-05T00:00:00-00:00'),'test.png'))
        self.assertNotEqual(original,wallpapers.resource_hash(png('2026-10-05T00:00:00Z',title='changed author'),'test.png'))
        self.assertNotEqual(original,wallpapers.resource_hash(png('2026-10-05T00:00:00Z',pixel=b'\xff\0\0\xff'),'test.png'))
        for date in ['not-a-date','2026-99-05T00:00:00Z','2026-10-05']:
            with self.subTest(date=date),self.assertRaises((AssertionError,ValueError)):
                wallpapers.resource_hash(png(date),'test.png')
        broken = bytearray(png('2026-10-05T00:00:00Z'));broken[-1] ^= 1
        with self.assertRaisesRegex(AssertionError,'Invalid PNG CRC'):
            wallpapers.resource_hash(bytes(broken),'test.png')

    def test_sound_alias_target_change_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "alias.oga").symlink_to("outside.oga")
            with self.assertRaisesRegex(AssertionError, "alias target changed"):
                sounds.verify(root, {"alias.oga": {"symlink": "original.oga"}})

    def test_broken_sound_alias_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "alias.oga").symlink_to("missing.oga")
            with self.assertRaisesRegex(AssertionError, "broken or escapes"):
                sounds.verify(root, {"alias.oga": {"symlink": "missing.oga"}})

    def test_png_timestamp_change_only_is_allowed(self):
        def chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xffffffff)
        def png(year, pixel):
            return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) +
                    chunk(b"tIME", struct.pack(">H5B", year, 1, 1, 0, 0, 0)) +
                    chunk(b"IDAT", zlib.compress(b"\0" + pixel)) + chunk(b"IEND", b""))
        original = resources.resource_hash(png(2016, b"\0\0\0\xff"), "test.png")
        self.assertEqual(original, resources.resource_hash(png(2026, b"\0\0\0\xff"), "test.png"))
        self.assertNotEqual(original, resources.resource_hash(png(2026, b"\xff\0\0\xff"), "test.png"))
        damaged = bytearray(png(2026, b"\0\0\0\xff")); damaged[-1] ^= 1
        with self.assertRaisesRegex(AssertionError, "Invalid PNG CRC"):
            resources.resource_hash(bytes(damaged), "test.png")

    def test_upgrade_setup_keeps_reviewed_candidate(self):
        record = json.loads((ROOT / "manifests/kde-plasma-package-build.json").read_text())["nodes"]["breeze-grub"]
        output = testing.setup_commands(ROOT, record)
        comparison = next(line for line in output.splitlines() if line.startswith("dpkg --compare-versions"))
        self.assertEqual(shlex.split(comparison)[2], record["version"])
        self.assertIn('plasma-package-testing.py" setup "${NODE}',
                      (ROOT / "scripts/run-authoritative-plasma-package.sh").read_text())

    def test_upstream_suite_cannot_pass_with_missing_or_failed_tests(self):
        record = {"upstream_tests": ["first", "second"]}
        log = "1/2 Test #1: first ..... Passed 0.01 sec\n2/2 Test #2: second ..... Passed 0.02 sec\n100% tests passed, 0 tests failed out of 2"
        self.assertEqual(testing.upstream_test_result(record, log)["state"], "PASS")
        for broken in [log.replace("Passed", "Failed", 1), log.replace("second", "wrong"),
                       log.replace("out of 2", "out of 1")]:
            with self.subTest(broken=broken), self.assertRaises(AssertionError):
                testing.upstream_test_result(record, broken)

    def test_additional_ecm_tests_are_accounted_for(self):
        record = {"upstream_tests": ["decoration"]}
        log = "1/2 Test #1: appstreamtest ..... Passed 0.01 sec\n2/2 Test #2: decoration ..... Passed 0.01 sec\n100% tests passed, 0 tests failed out of 2"
        result = testing.upstream_test_result(record, log)
        self.assertEqual(result["executed_tests"], ["appstreamtest", "decoration"])
        with self.assertRaises(AssertionError):
            testing.upstream_test_result(record, log.replace("appstreamtest ..... Passed", "appstreamtest ..... Failed"))
        with self.assertRaises(AssertionError):
            testing.upstream_test_result(record, log.replace("out of 2", "out of 1"))

    def test_baseline_setup_rejects_changed_or_unreviewed_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package/tests").mkdir(parents=True)
            setup = root / "package/tests/setup"
            setup.write_text("#!/bin/sh\nprintf 'fixture\\n'\n")
            record = {"ubuntu_baseline_package": "baseline-fixture", "version": "4:6.7.5-0supralinux1",
                      "packaging_path": "package", "baseline_setup_script": "tests/setup",
                      "packaging_sha256": {"tests/setup": hashlib.sha256(setup.read_bytes()).hexdigest()}}
            commands = testing.setup_commands(root, record)
            subprocess.run(["bash", "-n"], input=commands, text=True, check=True)
            self.assertIn("base64 --decode", commands)
            for path in ["../outside", "/absolute", "control"]:
                bad = copy.deepcopy(record); bad["baseline_setup_script"] = path
                with self.subTest(path=path), self.assertRaises(AssertionError):
                    testing.setup_commands(root, bad)
            setup.write_text("changed")
            with self.assertRaisesRegex(AssertionError, "Setup inputs changed"):
                testing.setup_commands(root, record)

    def test_reviewed_baseline_tree_preserves_relative_files_and_rejects_drift(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);tests=root/'package/tests';(tests/'client').mkdir(parents=True);(root/'bin').mkdir()
            for name,body in [('apt-get','exit 0'),('dpkg','exit 0'),('dpkg-query',"printf '1.0'")]:
                path=root/'bin'/name;path.write_text('#!/bin/sh\n'+body+'\n');path.chmod(0o755)
            marker=root/'marker';setup=tests/'setup';fixture=tests/'client/value'
            setup.write_text('#!/bin/sh\nset -eu\ntest -x "$0"\ncat "$(dirname "$0")/client/value" > '+shlex.quote(str(marker))+'\n')
            fixture.write_text('reviewed sibling fixture\n'+'transport fixture '*300)
            record={'ubuntu_baseline_package':'baseline-fixture','version':'2.0','packaging_path':'package','baseline_setup_script':'tests/setup','baseline_setup_payload':'reviewed-tests-tree','required_executable_files':['tests/setup'],'packaging_sha256':{'tests/setup':hashlib.sha256(setup.read_bytes()).hexdigest(),'tests/client/value':hashlib.sha256(fixture.read_bytes()).hexdigest()}}
            original=testing.setup_commands(root,record)
            baseline={'inputs_sha256':{'package/'+name:digest for name,digest in record['packaging_sha256'].items()}}
            testing.verify_baseline_input_hashes(record,baseline)
            bad_baseline=copy.deepcopy(baseline)
            bad_baseline['inputs_sha256']['package/tests/client/value']='0'*64
            with self.assertRaisesRegex(AssertionError,'reviewed input mismatch'):
                testing.verify_baseline_input_hashes(record,bad_baseline)
            self.assertEqual(original,testing.setup_commands(root,record))
            self.assertLess(max(len(line.encode()) for line in original.splitlines()),512)
            commands=original.replace('/var/tmp/supralinux-ubuntu-package-version',str(root/'version'))
            env=os.environ.copy();env['PATH']=str(root/'bin')+':'+env['PATH']
            subprocess.run(['bash','-ec',commands],env=env,check=True,capture_output=True,text=True)
            self.assertEqual(marker.read_bytes(),fixture.read_bytes())
            for value in ['unknown-payload-format']:
                bad=copy.deepcopy(record);bad['baseline_setup_payload']=value
                with self.assertRaisesRegex(AssertionError,'Unknown baseline'):
                    testing.setup_commands(root,bad)
            for name in ['tests/../outside','tests/client/../../outside']:
                bad=copy.deepcopy(record);bad['packaging_sha256'][name]='0'*64
                with self.subTest(path=name),self.assertRaises(AssertionError):testing.setup_commands(root,bad)
            fixture.write_text('changed')
            with self.assertRaisesRegex(AssertionError,'tree inputs changed'):testing.setup_commands(root,record)
            outside=root/'outside';outside.write_text('outside');fixture.unlink();fixture.symlink_to(outside)
            record['packaging_sha256']['tests/client/value']=hashlib.sha256(outside.read_bytes()).hexdigest()
            with self.assertRaisesRegex(AssertionError,'escapes reviewed tree'):testing.setup_commands(root,record)

    def test_large_baseline_survives_canonical_serial_terminal_and_rejects_corruption(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "package/tests").mkdir(parents=True)
            (root / "bin").mkdir()
            for name, body in [('apt-get', 'exit 0'), ('dpkg', 'exit 0'), ('dpkg-query', "printf '1.0'")]:
                executable = root / 'bin' / name
                executable.write_text('#!/bin/sh\n' + body + '\n')
                executable.chmod(0o755)
            marker = root / 'marker'
            script = root / 'package/tests/setup'
            script.write_text('#!/bin/sh\n# ' + 'transport-fixture ' * 230 + '\n' +
                              f"printf 'complete-script\\n' > {shlex.quote(str(marker))}\n")
            record = {'ubuntu_baseline_package': 'baseline-fixture', 'version': '2.0', 'packaging_path': 'package',
                      'baseline_setup_script': 'tests/setup',
                      'packaging_sha256': {'tests/setup': hashlib.sha256(script.read_bytes()).hexdigest()}}
            setup = testing.setup_commands(root, record).replace('/var/tmp/supralinux-ubuntu-package-version', str(root / 'version'))
            self.assertGreater(script.stat().st_size, 4096)
            self.assertLess(max(len(line.encode()) for line in setup.splitlines()), 512)
            environment = os.environ.copy()
            environment['PATH'] = str(root / 'bin') + ':' + environment['PATH']
            master, slave = pty.openpty()
            attributes = termios.tcgetattr(slave)
            attributes[3] &= ~termios.ECHO
            termios.tcsetattr(slave, termios.TCSANOW, attributes)
            child = subprocess.Popen(['/bin/sh', '-i'], stdin=slave, stdout=slave, stderr=slave,
                                     env=environment, start_new_session=True)
            os.close(slave)
            os.set_blocking(master, False)
            status = root / 'status'
            wire = ('sh -ec ' + shlex.quote(setup) + '; printf "%s" "$?" > ' + shlex.quote(str(status)) + '\n').encode()
            self.assertLess(max(len(line) for line in wire.splitlines()), 1024)
            offset, deadline = 0, time.monotonic() + 10
            try:
                while time.monotonic() < deadline and not status.exists():
                    readable, writable, _ = select.select([master], [master] if offset < len(wire) else [], [], .05)
                    if writable:
                        offset += os.write(master, wire[offset:offset + 1024])
                    if readable:
                        try:
                            os.read(master, 8192)
                        except (BlockingIOError, OSError):
                            pass
                self.assertTrue(status.exists(), 'Serial transport timed out')
                self.assertEqual(status.read_text(), '0')
                self.assertEqual(marker.read_text(), 'complete-script\n')
            finally:
                child.kill()
                child.wait()
                os.close(master)
            marker.unlink()
            corrupted = setup.replace('IyEv', 'eCEv', 1)
            self.assertNotEqual(corrupted, setup)
            result = subprocess.run(['sh', '-ec', corrupted], env=environment, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('FAILED', result.stdout)
            self.assertFalse(marker.exists(), 'Corrupted setup was executed')

    def test_changed_packaging_rejected(self):
        original = prepare.packaging_hashes
        try:
            prepare.packaging_hashes = lambda path: {"changed": "bad"}
            with self.assertRaisesRegex(AssertionError, "Packaging inputs changed"):
                prepare.contract("breeze-grub")
        finally:
            prepare.packaging_hashes = original

    def test_unreviewed_source_rejected(self):
        original = prepare.json.loads
        def changed(payload):
            result = original(payload)
            if result.get("role") == "reviewed-plasma-package-build":
                result = copy.deepcopy(result)
                result["nodes"]["breeze-grub"]["packaging_review"] = "REVIEW_REQUIRED"
            return result
        try:
            prepare.json.loads = changed
            with self.assertRaisesRegex(AssertionError, "individual review"):
                prepare.contract("breeze-grub")
        finally:
            prepare.json.loads = original

    def test_corrupt_installed_resource_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            theme = Path(directory)
            (theme / "theme.txt").write_text("corrupt")
            with self.assertRaisesRegex(AssertionError, "differs from signed upstream"):
                resources.verify(theme, {"theme.txt": "0" * 64})

    def test_extra_installed_resource_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            theme = Path(directory)
            (theme / "unexpected.png").write_bytes(b"unexpected")
            with self.assertRaisesRegex(AssertionError, "resource set changed"):
                resources.verify(theme, {})


if __name__ == "__main__":
    unittest.main()
