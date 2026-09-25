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

## Diagnostic result — provider-presence hypothesis rejected

Round 14 completed successfully in workflow `36163272251`, job `108164792241`, at commit `49e27249ecaa8f7d1ba20fe38615bdc2ee11d991`. Evidence artifact `10876807762` has SHA-256 `2dda498091873a1c99a649ddb15c795130592c91100a3d97a78a608b8f531b87`.

The baseline reproduced both primary failures exactly. Installing only the exact retained `libkf6iconthemes-bin 6.30.0-0supralinux3` package did **not** recover either failure: direct execution and the complete CTest pair remained unchanged. `QT_DEBUG_PLUGINS` did not report `KIconEnginePlugin.so` loaded.

Therefore the Round 13 hypothesis is rejected in its simple form: **provider presence alone is not sufficient**. This does not show that KIconEngine is irrelevant; it shows that merely installing its plugin package does not activate it in these KIO test processes.

Round 12 had `QIcon::themeName()=breeze` with `QIcon::fallbackThemeName()=hicolor` and preserved icon names. KIconThemes startup calls `BreezeIcons::initIcons()`, which registers the Breeze resource and changes an empty/hicolor fallback to `breeze`. The next diagnostic isolates that state change before returning to packaging.

Round 14 remains non-promoting. KIO stays `6.30.0-0supralinux7` FAIL/downstream-ineligible, no `-8` exists, and canonical state remains **12 PASS / 1 pending / 1 current FAIL / 6 BLOCKED**.

Next gate: **`tier3-round15-kio-breeze-icons-init-state-diagnostic-definition`**.
