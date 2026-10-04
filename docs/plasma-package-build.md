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

This gate does not certify graphical GRUB rendering, theme activation, the whole
Plasma stack or a release. Breeze GRUB only installs resources; selecting the
default boot theme belongs to later distro integration. A PASS must retain the
source, binaries, `.changes`, `.buildinfo`, logs and result independently of
Actions expiry before admitting the evidence. Failed infrastructure remains
separate from package/test failure. Final merge/publication require their gates.
