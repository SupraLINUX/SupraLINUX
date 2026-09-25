# KDE Tier 3 — KIO Round 13 build-tree/process diagnostic

Status: **definition pending diagnostic evidence**.

Round 12 proved that Ubuntu 26.04 + Qt 6.10.2 + the retained Breeze 6.30 provider resolve `unknown`, `inode-directory` and `folder-red` correctly in isolated probes, including the `QStandardPaths` sequences used by the two failing KIO tests. The remaining delta therefore belongs to the real KIO build-tree/test-process context.

Round 13 is diagnostic-only. No new KIO revision is allocated, no source remediation is defined, no upstream test is changed or suppressed, and no Debian package is built.

## Reproduction model

The workflow consumes the exact KIO source materialization used for `6.30.0-0supralinux7`:

- artifact `10839162922`;
- SHA-256 `ffd7fb48d855b4788b3659ed083c0652cd2fefd6290428d46c768267198fef4c`.

It derives the entire predecessor/provider closure from the canonical Level 1 manifest and verifies every artifact SHA before use. Those packages are exposed through a temporary local APT repository on a clean Ubuntu 26.04 runner.

The materialized source is extracted unchanged. Its Debian `override_dh_auto_configure` is used to reproduce the exact adapted CMake definition, but only CMake targets `kdirmodeltest` and `knewfilemenutest` are compiled. The workflow does not invoke `dpkg-buildpackage` or `sbuild`.

## Variants

The original test binaries are then executed under:

1. CTest with the Attempt 7 wrapper;
2. direct execution with `HOME`, `KDECI_PLATFORM_PATH`, `QT_PLUGIN_PATH=<build>/bin`, XCB and Breeze exactly set;
3. the same execution without `QT_PLUGIN_PATH`;
4. the same execution without `KDECI_PLATFORM_PATH`;
5. the same execution with explicit `XDG_DATA_DIRS=/usr/local/share:/usr/share`.

An additional exact run uses `QT_DEBUG_PLUGINS=1` and `strace -f -e trace=file` for both test binaries. This records whether the process actually opens Breeze's `index.theme` and the relevant icon payloads.

The diagnostic does not assume which variant will recover. It records the two primary Attempt 7 signatures: empty `icon2.name()` in KDirModel and empty `iconLabel.iconName` in KNewFileMenu.

If the exact host build-tree reproduces and one environment removal recovers both tests, that delta becomes the next remediation candidate. If the host build-tree does not reproduce at all, the remaining scope is specifically the `sbuild/unshare` chroot used by canonical Level 1.

Canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED** and `execution_authorized=false`.

Next gate: `tier3-round13-kio-build-tree-diagnostic-evidence`.

## Infrastructure attempt 1

Workflow `36131672792`, job `108060121271`, on commit `35bdba0d35836eabb53e96675e0b3767d30b0de3` did **not** reach the KIO build-tree experiment. It failed at the local APT repository stage because the repository lived below the GitHub workspace home and the APT sandbox user `_apt` could not traverse/read that path.

The uploaded failure artifact is `10862700232`, SHA-256 `b6ff8d87f036ad227b440ac256b8d600fbb1e5e61773e1a69a1624a861dd724a`. This attempt is classified **INFRA_FAIL** and supplies no diagnostic evidence about KIO itself.

Repository Policy for that commit also stopped at ShellCheck because of three runner-only lint issues. Those issues do not alter the Round 13 diagnostic design.

The corrected runner uses a world-traversable repository under `/tmp/supralinux-round13-repo`, materializes both `Packages` and `Packages.gz`, and preserves provider-version evidence while satisfying ShellCheck. Round 13 remains `definition-pending-diagnostic`.

## Infrastructure attempt 2

Workflow `36134433836`, job `108069000227`, on commit `f406f157e361c4561e112f64ae58617d52f8d842` also produced no KIO diagnostic result. Artifact `10862348959`, SHA-256 `73c954e57ee368506b226167a70e2048b2c0de18330a85cef3e7171691ad99d9`, is retained as infrastructure evidence only.

The previous repair accidentally truncated the provider-download/local-repository block and left an incomplete `while IFS=` statement. Both ShellCheck and Bash therefore failed before provider installation or KIO configuration.

The runner now restores the full block and obtains the tab separator through `printf`, avoiding shell ANSI-C quoting in the generated script. Round 13 remains `definition-pending-diagnostic`; no package or canonical state changed.
