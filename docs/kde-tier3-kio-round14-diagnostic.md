# KDE Tier 3 — KIO Round 14 KIconThemes engine-provider diagnostic

Status: **definition pending diagnostic evidence**.

Round 13 proved that the real KIO build-tree reproduces both icon-name failures and that removing QT_PLUGIN_PATH, removing KDECI_PLATFORM_PATH, or explicitly restoring XDG_DATA_DIRS does not recover either test. Its traces also prove that Breeze metadata and the relevant Breeze payloads are reachable.

The remaining strong hypothesis is the KIconThemes icon-engine provider. Canonical KIconThemes 6.30.0-0supralinux3 contains libkf6iconthemes-bin, which installs /usr/lib/x86_64-linux-gnu/qt6/plugins/kiconthemes6/iconengines/KIconEnginePlugin.so.

The binary is only a Recommends of the KIconThemes runtime packages, so the KIO build/test environments created with --no-install-recommends omit it.

## A/B test

Round 14 intentionally changes only one variable.

A — baseline: reproduce the Round 13 build-tree with the exact KIO 6.30.0-0supralinux7 materialization and exact retained provider closure, while confirming that libkf6iconthemes-bin is not installed.

B — treatment: install only the exact retained libkf6iconthemes-bin 6.30.0-0supralinux3 package from canonical KIconThemes artifact 10731249726. The Debian package must match SHA-256 6806b7b03b3f30d21620c315118066c9c7f35714e6a12e0b3360e01cbcfaff0c.

Both phases run the original KIO build-tree binaries and the original primary upstream functions: KDirModelTest::testIcon and KNewFileMenuTest::testFolderIconCollection. After provider installation, the two complete CTest targets are also rerun. QT_DEBUG_PLUGINS is enabled for the treatment so evidence can show whether KIconEnginePlugin.so is discovered or loaded.

If baseline reproduces both empty-icon signatures and treatment makes both direct tests plus both complete CTest targets pass, the provider becomes a proven causal requirement of the KIO upstream test environment. That result would justify a separate remediation-definition gate; it would not itself change packaging.

If the provider does not recover the tests, the hypothesis is rejected and the next diagnostic must go deeper into KIconThemes/QIcon engine behavior.

No KIO revision is allocated. No source is patched, no test is suppressed, no Debian package is built, and canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**.

Next gate: tier3-round14-kio-kiconthemes-engine-provider-diagnostic-evidence.
