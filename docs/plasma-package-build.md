# Authoritative Plasma package builds

`manifests/kde-plasma-package-build.json` records each individually reviewed
packaging overlay, its exact input hashes, binary identities and current scope.
The reusable preparation/build scripts consume that contract. The controlled
`ci:plasma-package-build` label starts one reviewed node on one disposable JIT
runner. Ordinary PR CI validates the contract without reopening materialization.

The initial node is Breeze GRUB 6.7.5. Its resources require only debhelper to
package, so this sample uses the certified clean golden image. It does not need
the Frameworks milestone or a Qt transition. The other 33 Level 0 nodes remain
locked for individual packaging review. For example, KDecoration's Ubuntu rules
currently suppress `dh_auto_test`; that requires review before its admission.

The runner rechecks KDE's detached signature and frozen source/packaging hashes,
creates a source package, builds in a fresh resolute sbuild/unshare rootfs with
updates/security enabled, checks binary version/architecture, runs lintian and
runs substantive autopkgtests in nested QEMU with KVM required. The testbed first
installs Ubuntu's current package; APT then upgrades it to the candidate. Tests
check all installed resources against signed upstream, PNG/font structure,
image/font references, version precedence and APT dependency consistency.
PNG CRCs and all content/rendering chunks remain exact; only the `tIME` timestamp
may change through Debian's reproducibility normalization. Other resources keep
their exact upstream byte hashes.

This gate does not certify graphical GRUB rendering, theme activation, the whole
Plasma stack or a release. Breeze GRUB only installs resources; selecting the
default boot theme belongs to later distro integration. A PASS must retain the
source, binaries, `.changes`, `.buildinfo`, logs and result independently of
Actions expiry before admitting the evidence. Failed infrastructure remains
separate from package/test failure. Final merge/publication require their gates.

## First package closure

Breeze GRUB `6.7.5-0supralinux1` passed clean sbuild, lintian and both
autopkgtests on the authoritative KVM runner in
[run 37232072978](https://github.com/SupraLINUX/SupraLINUX/actions/runs/37232072978).
APT upgraded Ubuntu's `6.6.4-0ubuntu1` package without removing packages. The
artifact, complete source closure, binaries, buildinfo, changes and logs are
retained locally by digest; restoration from an empty cache passed without
GitHub. The archive contains one unique binary package plus the identical copy
used by autopkgtest. Off-host backup has not been verified.

The earlier runner variable collision remains `INFRA_INVALID`; the strict PNG
timestamp comparison remains `FAIL`. Their original evidence and artifacts are
preserved. Neither result was rewritten as PASS. The final package contract
records all three Attempts and binds the PASS to its exact source commit,
workflow/job, packaging hashes and host evidence seal.

The other 33 Level 0 nodes still require individual review. The captured Ubuntu
reference inventory in `manifests/evidence/plasma/level0-packaging-inventory.json`
lists 13 test-step overrides and no autopkgtest control files; it is advisory
inventory and does not admit any package.
