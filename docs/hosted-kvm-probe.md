# GitHub-hosted Ubuntu 26.04 KVM capability experiment

This is an isolated experimental gate, not a KDE package Attempt or release
certificate. The workflow can run only by manual dispatch or by the exact PR
label ci:hosted-kvm-probe. Routine PR sync does not start it.

The job verifies Ubuntu 26.04 x86_64 and the /dev/kvm character device. If
GitHub's device permissions exclude the current user, it applies a user-specific
POSIX ACL only inside the ephemeral GitHub-hosted runner (never chmod a+rw,
never elevate QEMU to root, never touch the user's physical PC). The job then
runs a tiny BIOS boot sector under QEMU with explicit KVM acceleration and
host CPU passthrough. The sector emits a unique serial marker and exits via the
isa-debug-exit device. Both the marker and exit code 85 must match. No QEMU TCG
fallback, downloaded guest OS, local host access or package build is involved.

The first infrastructure diagnostic (run 38690562479 on commit e550e5f1) was
INFRA_INVALID because the hosted runner user could not read/write /dev/kvm.
Ubuntu QEMU installed successfully; no VM boot was attempted. The ACL change
was successfully applied, but the second run (38690896553 on f66ec5a2)
ended INFRA_INVALID before guest execution: QEMU rejected the read-only IDE
block node. Two infrastructure-invalid runs prohibit blind retries.

The repaired mechanism uses a writable-emulated IDE drive with snapshot=on,
so QEMU writes only to a disposable overlay, not the initial bootsector.
The third workflow first boots the same sector under explicit TCG in a
separately labeled non-KVM mechanism smoke; KVM execution cannot start if
that smoke fails. The TCG result is not a KVM PASS or release certification.

The bounded JSON evidence is retained with the exact SHA. A successful probe
only proves a tiny x86 guest actually executed under KVM on one hosted runner.
It does not validate nested Ubuntu 26.04 guest boot, autopkgtest-qemu, sbuild,
clean-room packaging, release compatibility, performance or repeatability.

If the tiny test passes, the next separate mechanism certification must boot a
verified Ubuntu 26.04 guest and exercise autopkgtest-qemu with independent
cleanup and resource bounds. Do not promote historical KVM or package PASS
evidence on the basis of this experiment. Keep the existing KVM lane canonical
until release-relevant parity is proved. GitHub-hosted artifacts alone have
finite retention and must not be treated as long-term archival storage.

Reference: https://docs.github.com/en/actions/reference/runners/github-hosted-runners
