# KDE Frameworks 6.30 — Tier 1 package Batch 2

Status: **first real attempt complete: 0 PASS, 3 FAIL; revision 2 remediation prepared**

Batch 2 contains three independent Tier 1 nodes: **KTextTemplate**, **KArchive** and **KHolidays**. KDE upstream 6.30.0 remains the source/build authority. Ubuntu Resolute is the direct compatibility/provider target; Debian sid packaging is a technical reference only.

## First real attempt

Workflow run `34720201713` attempted all three nodes independently from commit `5edf71b390088a551af81e7fc7e8d87a8378104f`. All three are real own-cause **FAIL**, not BLOCKED.

- **KTextTemplate `6.30.0-0supralinux1`** — job `103624554096`, artifact `10306265683`, SHA-256 `c164640037e564a43479daaa740f55c0f7578d977a7c38bfeb691fbd6b88544a`. Configure/build/install completed and **10/10 autotests PASS**. `dh_makeshlibs` then failed at `dpkg-gensymbols`.
- **KArchive `6.30.0-0supralinux1`** — job `103624554004`, artifact `10305889632`, SHA-256 `1850a0a6dd7f267870fda83f17f5990f806ec76ae8fe810144557c46af532d01`. `dh_auto_configure` failed before tests because ECM requires **Qt6::LinguistTools** for translation installation.
- **KHolidays `6.30.0-0supralinux1`** — job `103624554109`, artifact `10305513311`, SHA-256 `522257440d6e04563162178dd3d3ab3ae658dc56c129dcf7f482fef8219bb0dc`. It failed at the same configure-time `Qt6::LinguistTools` requirement before tests.

KArchive and KHolidays did not reach autotests, symbols, Lintian or consumer smoke. KTextTemplate did not reach the external Lintian/consumer gates because `sbuild` stopped at symbols.

## Remediation revision 2

All three are prepared as `6.30.0-0supralinux2`, but remain canonical FAIL until a real retry passes.

For **KArchive** and **KHolidays**, `qt6-tools-dev (>= 6.5.0~)` is added strictly as the Ubuntu provider of the Qt LinguistTools component required by KDE ECM. KDE/ECM determines the need; Ubuntu merely supplies the compatible Qt implementation.

For **KTextTemplate**, the retained Debian 6.28 symbols file remains the hash-pinned starting point. A reviewed package-local patch is then applied and the resulting symbols file must hash to `e5c0e999ec374102a6b6693fa70f55f4b12bf38eed2013c573e765a521cf0585` before source-package assembly. The review accounts for upstream's scriptable-tags plugin split, treats compiler/Qt template emissions as optional, treats the inline `Exception` vtable as optional, and adds the new binary-compatible `Filter` constructor/context API at minimum upstream version `6.30.0`.

The three `-doc` package descriptions are corrected: QDoc is outside the default Frameworks build profile, so these packages are compatibility placeholders rather than claims that QCH documentation was built.

## State semantics

Current canonical Tier 1 state is **4 PASS, 22 pending, 3 FAIL, 0 BLOCKED**. The three FAIL nodes do not block the other Tier 1 nodes because Tier 1 Frameworks depend only on ECM/Qt/third-party inputs, not on one another. Revision 2 may become PASS only after a real clean-package retry.
