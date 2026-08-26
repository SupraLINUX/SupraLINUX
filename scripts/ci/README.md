# Aurora CI helpers

These scripts are the implementation behind the `Aurora package validation` GitHub Actions workflow.

- `build-packages.sh` builds the current SupraLINUX development DEB packages without signing them.
- `validate-apt-resolution.sh` verifies that the local package set resolves on Ubuntu 26.04 and that the default SupraLINUX Snap policy prevents Snap components from becoming installable candidates.

The CI scripts must remain non-destructive with respect to the runner host. Dependency validation should use APT simulation unless a test explicitly requires an isolated disposable environment.
