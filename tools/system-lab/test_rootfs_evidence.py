import unittest
from rootfs_evidence import check_builder, check_target, parse_hashes, target_report


class RootfsEvidenceTests(unittest.TestCase):
    def test_console_crlf_and_lf(self):
        for sep in ("\r\n", "\n"):
            check_builder(sep.join(["SUPRA_BUILD_VM_READY", "log", "SUPRA_BUILD_VM_EXIT=0"]), "0\n")
            check_target(sep.join(["log", "SUPRA_TARGET_BOOT_READY"]))

    def test_bad_builder_or_target_markers(self):
        for console, status in (("SUPRA_BUILD_VM_EXIT=0", "0"),
                                ("SUPRA_BUILD_VM_READY\nSUPRA_BUILD_VM_EXIT=1", "0"),
                                ("SUPRA_BUILD_VM_READY\nSUPRA_BUILD_VM_EXIT=0", "1"),
                                ("SUPRA_BUILD_VM_EXIT=0\nSUPRA_BUILD_VM_READY", "0")):
            with self.subTest(console=console), self.assertRaises(ValueError):
                check_builder(console, status)
        for console in ("", "prefix SUPRA_TARGET_BOOT_READY", "SUPRA_TARGET_BOOT_READY\nSUPRA_TARGET_BOOT_READY"):
            with self.assertRaises(ValueError):
                check_target(console)

    def test_exact_relative_boot_paths(self):
        kernel = "a" * 64 + "  boot/vmlinuz-linux-lts"
        initrd = "b" * 64 + "  boot/initramfs-linux-lts.img"
        self.assertEqual(len(parse_hashes(kernel + "\n" + initrd)), 2)
        for content in (kernel, kernel + "\n" + kernel, kernel + "\n" + initrd.replace("  boot/", "  /boot/")):
            with self.assertRaises(ValueError):
                parse_hashes(content)

    def test_accelerator_is_not_conflated(self):
        marker = "SUPRA_TARGET_BOOT_READY\r\n"
        self.assertTrue(target_report(marker, "kvm")["kvm_target_boot_verified"])
        self.assertFalse(target_report(marker, "tcg")["kvm_target_boot_verified"])
        self.assertTrue(target_report(marker, "tcg")["direct_kernel_boot_verified"])
        with self.assertRaises(ValueError):
            target_report(marker, "unknown")
