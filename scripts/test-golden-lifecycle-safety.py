#!/usr/bin/env python3
"""Check lifecycle refusal and cleanup without starting a hypervisor."""

import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest


SOURCE = Path(__file__).with_name("check-golden-preparation-lifecycle.sh")


class LifecycleSafety(unittest.TestCase):
    def test_network_overrides_rejected_before_host_commands(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            scripts = root / "scripts"
            scripts.mkdir()
            candidate = scripts / SOURCE.name
            candidate.write_bytes(SOURCE.read_bytes())
            trace = root / "host-actions"
            tools = root / "tools"
            tools.mkdir()
            sentinel = "#!/bin/bash\nprintf 'called\\n' >> \"$FIXTURE_TRACE\"\nexit 77\n"
            for name in ("chgrp", "chmod", "id", "jq", "qemu-img", "sha256sum",
                         "stat", "sudo", "timeout", "virsh", "virt-cat", "virt-install"):
                tool = tools / name
                tool.write_text(sentinel)
                tool.chmod(0o755)
            (scripts / "check-kvm-host.sh").write_text(sentinel)
            (scripts / "check-kvm-host.sh").chmod(0o755)
            env = os.environ.copy()
            env.update(PATH=str(tools) + ":" + env["PATH"], FIXTURE_TRACE=str(trace))
            for network in ("default", "supralinux-private", "home-lan"):
                with self.subTest(network=network):
                    env["SUPRALINUX_LIBVIRT_NETWORK"] = network
                    result = subprocess.run(["/bin/bash", str(candidate)], env=env,
                                            capture_output=True, text=True, timeout=5)
                    self.assertEqual(result.returncode, 2, result.stderr)
                    self.assertFalse(trace.exists(), "Host command ran before refusal")

    def exercise_cleanup(self, original_exit=0, foreign=False, outside=False, retained=False):
        source = SOURCE.read_text()
        cleanup = source[source.index("cleanup() {"):source.index("trap cleanup EXIT")]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            state = root / "state"
            state.mkdir()
            build = (root if outside else state) / "owned-build"
            build.mkdir()
            overlay = build / "lifecycle-work.qcow2"
            overlay.write_bytes(b"owned writable overlay")
            evidence = root / "evidence"
            evidence.mkdir()
            log = evidence / "captured-log"
            log.write_bytes(b"preserved evidence")
            golden = root / "signed-source.img"
            golden.write_bytes(b"preserved source")
            vm = root / "fake-vm-present"
            vm.touch()
            trace = root / "hypervisor-actions"
            tools = root / "tools"
            tools.mkdir()
            name = "unrelated-vm" if foreign else "supralinux-golden-lifecycle-fixture"
            fake = tools / "virsh"
            fake.write_text("#!" + sys.executable + "\n" + '''
import os
from pathlib import Path
import sys
args = sys.argv[1:]
assert args[:2] == ['--connect', 'test:///fixture']
assert args[-1] == os.environ['FIXTURE_VM_NAME']
with Path(os.environ['FIXTURE_TRACE']).open('a') as f:
    f.write(' '.join(args[2:]) + '\\n')
vm = Path(os.environ['FIXTURE_VM_FILE'])
action = args[2]
if action == 'dumpxml': print('<domain/>')
elif action == 'domstate': print('running')
elif action == 'destroy': pass
elif action == 'undefine':
    if os.environ['FIXTURE_RETAIN_DOMAIN'] == '1': raise SystemExit(1)
    vm.unlink()
elif action == 'dominfo': raise SystemExit(0 if vm.exists() else 1)
else: raise AssertionError(action)
''')
            fake.chmod(0o755)
            values = {"VM_DEFINED": "1", "VM_NAME": name, "BUILD_DIR": str(build),
                      "STATE_ROOT": str(state), "EVIDENCE_DIR": str(evidence),
                      "WORK_DISK": str(overlay), "LIBVIRT_URI": "test:///fixture"}
            harness = root / "harness.sh"
            harness.write_text("\n".join(k + "=" + shlex.quote(v) for k, v in values.items())
                               + "\n" + cleanup + "\n(exit " + str(original_exit) + ")\ncleanup\n")
            env = os.environ.copy()
            env.update(PATH=str(tools) + ":" + env["PATH"], FIXTURE_VM_NAME=name,
                       FIXTURE_VM_FILE=str(vm), FIXTURE_TRACE=str(trace),
                       FIXTURE_RETAIN_DOMAIN="1" if retained else "0")
            result = subprocess.run(["/bin/bash", str(harness)], env=env,
                                    capture_output=True, text=True, timeout=5)
            self.assertEqual(golden.read_bytes(), b"preserved source")
            self.assertEqual(log.read_bytes(), b"preserved evidence")
            if foreign or outside:
                self.assertEqual(result.returncode, 1)
                self.assertTrue(vm.exists())
                self.assertTrue(overlay.exists())
                self.assertFalse(trace.exists(), "Foreign cleanup reached the hypervisor")
            elif retained:
                self.assertEqual(result.returncode, 1)
                self.assertTrue(vm.exists())
                self.assertTrue(overlay.exists(), "Disk was deleted while domain still existed")
            else:
                self.assertEqual(result.returncode, original_exit, result.stderr)
                self.assertFalse(vm.exists())
                self.assertFalse(build.exists())

    def test_success_removes_owned_vm_and_overlay(self):
        self.exercise_cleanup()

    def test_failure_preserves_original_exit_and_evidence(self):
        self.exercise_cleanup(original_exit=7)

    def test_foreign_vm_refused_before_hypervisor(self):
        self.exercise_cleanup(foreign=True)

    def test_foreign_directory_refused_before_hypervisor(self):
        self.exercise_cleanup(outside=True)

    def test_retained_vm_preserves_writable_overlay(self):
        self.exercise_cleanup(retained=True)


if __name__ == "__main__":
    unittest.main()
