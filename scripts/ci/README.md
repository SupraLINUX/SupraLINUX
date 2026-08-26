# Aurora CI helpers

These scripts implement the current Aurora validation layers.

- `build-packages.sh` builds the current SupraLINUX development DEB packages without signing them.
- `validate-apt-resolution.sh` verifies that the local package set resolves on Ubuntu 26.04 and that the default SupraLINUX Snap policy prevents Snap components from becoming installable candidates.
- `validate-clean-rootfs.sh` creates an isolated Ubuntu 26.04 `debootstrap` rootfs, installs the SupraLINUX policy/base/desktop packages for real, runs `apt-get check`, verifies required desktop integration packages are installed, and rejects Ubuntu Desktop, Kubuntu Desktop, GNOME Shell and Snap components.

The CI scripts must remain non-destructive with respect to the runner host. Dependency validation should use APT simulation unless a test explicitly requires an isolated disposable environment. Real package installation is therefore confined to the disposable clean rootfs rather than the GitHub runner host.
