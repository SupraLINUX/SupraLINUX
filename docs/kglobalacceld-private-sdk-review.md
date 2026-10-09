# KGlobalAccelD private SDK transition review

KGlobalAccelD 6.7.5-0supralinux1 remains in compatibility review after
[Attempt 1](https://github.com/SupraLINUX/SupraLINUX/actions/runs/37913147362)
on source `3809ef74c9d86d480001b9a8a989862efe44bbd7`. The clean retained-input
probe and original Ubuntu baseline passed. Compilation and all four executed
CTests passed: AppStream, migrateconfigtest, shortcutstest and allowlisttest.
The package build failed at `dh_makeshlibs`; lintian and installed candidate
tests did not run. This is an original package FAIL, with no eligible binaries.

The original symbols diff records 21 additions and ten removals. Three removed
symbols are installed KGlobalAccelD methods whose arguments change from
`QList<QKeySequence>` to `QSet<QKeySequence>`; the other seven belong to
non-installed implementation classes/helpers. Getter return types also change
while their symbol names remain unchanged. The library retains SONAME 0.

Both the original Ubuntu header and the signed 6.7.5 header explicitly declare
KGlobalAccelD private API and identify KWin as a consumer. The reviewed unchanged
Ubuntu private SDK executable therefore requires a scoped transition review.
This finding alone does not establish incompatibility of the public Frameworks
KGlobalAccel application API. Its unchanged original application client has not
yet been executed against the installed candidate.

Before resuming this package, authenticate Ubuntu reverse dependencies and
inspect their actual executable/plugin imports, including KWin. Review changed
arguments and return types, then prove the complete application and private
consumer transition in disposable KVM. Preserve public application client bytes,
legacy D-Bus coverage, source authenticity and every unaffected ABI guard.
Removing missing symbol rows or accepting a failed client cannot certify this
transition. No upstream source fork or Qt replacement has been made.

The original archive, source payload, full sbuild and baseline logs, job metadata,
symbols diff and both headers are retained. CRC/content hashes and a restore into
an empty local directory passed. VM, runner 253 and writable overlay absence were
verified independently; golden and milestone images remain preserved. There is
no off-host backup claim.

The live manifests hold this candidate outside execution scope. Independent
reviewed packages may proceed; LibKSysGuard is the next admitted input preflight.
The inspectable hold is
[`compatibility-review.json`](../manifests/evidence/plasma/kglobalacceld-attempt1/compatibility-review.json).
