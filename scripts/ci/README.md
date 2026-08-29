# Aurora CI helpers

These scripts implement the current Aurora validation layers.

## KDE Stack Qualification

- `validate-kde-stack-source-manifests.sh` validates the pinned official Plasma/Frameworks source manifests.
- `validate-kde-stack-roots.py` verifies that every direct `supralinux-desktop` Depends/Recommends root is classified against the candidate release sets or the Ubuntu/Gear policy boundary.
- `prepare-kde-stack-apt-metadata.sh` prepares isolated snapshot-only APT metadata: Resolute binary+source metadata and Stonking source-only metadata.
- `generate-kde-build-closure.py` is the canonical provider-aware strict KSQ-0 transitive Build-Depends resolver. Certification does not use an allow-unresolved mode.
- `audit-kde-stack-source-selections.sh` verifies exact external source inputs, pinned hashes and the certified `kwallet-pam` PAM packaging invariants.
- `validate-kwallet-pam-installation.sh [rootfs]` is the downstream package-installation contract for the rebuilt KWallet PAM package. It requires `pam_kwallet5.so` to be registered in both `common-session` and `common-auth`. It is intended for KSQ-1/KSQ-3 after the candidate binary exists.

Canonical KSQ-0 evidence is documented in `docs/validation/AURORA_KSQ_0_ACCEPTANCE.md` and override ownership in `docs/KDE_STACK_OVERRIDES.md`.

## Historical/current product validation helpers

- `build-packages.sh` builds the current SupraLINUX development DEB packages without signing them.
- `validate-apt-resolution.sh` verifies that the local package set resolves on Ubuntu 26.04 and that the default SupraLINUX Snap policy prevents Snap components from becoming installable candidates.
- `validate-clean-rootfs.sh` creates an isolated Ubuntu 26.04 `debootstrap` rootfs, installs the SupraLINUX policy/base/desktop packages for real, runs `apt-get check`, verifies required desktop integration packages are installed, and rejects Ubuntu Desktop, Kubuntu Desktop, GNOME Shell and Snap components.

The CI scripts must remain non-destructive with respect to the runner host. Dependency validation should use isolated APT state or simulation unless a test explicitly requires an isolated disposable environment. Real product package installation is confined to disposable rootfs/VM environments rather than the GitHub runner host.
