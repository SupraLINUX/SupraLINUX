# KDE stable dependency DAG

Status: **ECM root PASS; 22 Frameworks Tier 1 PASS; 7 Tier 1 pending; 0 current FAIL; 0 BLOCKED**

Last reviewed: **2026-09-18**

## Authority

KDE upstream stable define el desktop y sus requisitos.

Ubuntu 26.04 es plataforma, proveedor y objetivo de compatibilidad.

Un packaging de otra distribución sólo aporta referencia técnica.

No selecciona la versión KDE de SupraLINUX.

Snapshot seleccionado:

- Plasma 6.7.5;
- KDE Frameworks 6.30.0;
- KDE Gear 26.08.1;
- KDE-selected Qt series 6.10;
- Ubuntu Resolute Qt 6.10.2: hosted preflight PASS;
- final Qt provider certification: pending.

Ubuntu 26.04 currently carries `extra-cmake-modules` 6.24.0-0ubuntu1.

Eso es una **technical packaging reference only**.

KDE upstream 6.30.0 sigue siendo autoridad para ECM.

## Semántica DAG

- `PASS`: el gate definido fue intentado y completado.
- `FAIL`: el nodo fue intentado y falló por causa propia.
- `BLOCKED`: no se intenta porque un predecesor requerido está FAIL.
- `pending`: todavía no se intentó.

`BLOCKED` is never counted as `FAIL`.

Los FAIL históricos permanecen como evidencia tras un PASS posterior.

Un hosted PASS no sustituye la prueba KVM/JIT autoritativa.

Los tests de sistema y compatibilidad siguen siendo gates separados.

## Extra CMake Modules 6.30.0 — PASS

Source SHA-256 `22c9f7ff930dae7329faebf2942d2424f4a298c43bb3f11e217be6b12f227f6e`.

Paquete validado `extra-cmake-modules 6.30.0-0supralinux3`.

### Historial

1. `6.30.0-0supralinux1`.
   Run `34689672632`.
   Artifact `10296512341`.
   SHA-256 `d47ac7361106ceb5f04729c1a3dcb4103b30255684e5b3f53b833edd6d4f6558`.
   Resultado **FAIL** en `dh_auto_test`.
   `BUILD_TESTING=OFF` eliminó el target Ninja esperado.

2. `6.30.0-0supralinux2`.
   Run `34690027788`.
   Job `103543538213`.
   Artifact `10296517706`.
   SHA-256 `89ef0003fd8282965a4c253bcd0150b8f040fe134ca0385d1365cd8c31808239`.
   Resultado **FAIL** en consumer smoke.
   También reveló findings de packaging.
   El consumer Qt carecía de `qtpaths6`.

3. `6.30.0-0supralinux3`.
   Run `34694951158`.
   Job `103556722010`.
   Artifact `10298635300`.
   SHA-256 `181ea1434e803453d61d345a28adeba5ad9cee09a7c93948c6ce3ef1214984ff`.
   Resultado **PASS**.

La revisión PASS hace fatal `lintian --fail-on error`.

También incorpora metadata requerida y `qtpaths6` al consumer.

`.deb` SHA-256 `ba544c482df73ec162ceb08543d23e2e3f9af3e309e42b16a51c83966081692f`.

El ECM hosted preflight no afirma ejecutar toda la upstream test suite.

La upstream test suite completa sigue como **separate gate** de calidad.

## Tier 1 PASS

### Attica

`6.30.0-0supralinux2`.

Run `34706416753`.

Artifact `10301851297`.

Artifact SHA-256 `f1ed135e9d5a25e6773957b2e52817fba03280293249f54257efc4e18304de27`.

Tests `6/6` PASS.

Consumer smoke PASS.

### Batch 1 — 3/3 PASS

Los tres nodos dependen sólo de ECM PASS.

- KCodecs `6.30.0-0supralinux4`: PASS.
- KDBusAddons `6.30.0-0supralinux3`: PASS.
- ThreadWeaver `6.30.0-0supralinux3`: PASS.

KCodecs usa Debian 6.28 como referencia técnica de símbolos.

Quince símbolos internos toolchain tienen mínimo upstream `6.30.0`.

No usan una revisión Debian como mínimo ABI.

### Batch 2 — 3/3 PASS

Workflow final `34884764702`.

Commit `e0f4e7c48dcf7541538eb919374a3f4b6c293b75`.

- KTextTemplate `6.30.0-0supralinux3`.
  Job `104112549851`.
  Artifact `10363863115`.
  SHA-256 `7b9d0390ed90c882f4b7ad1993924e722bfb7ad35238c2ced52bbd5809555bc9`.
  Tests `10/10` PASS.
  SONAME `libKF6TextTemplate.so.6`.
  Consumer smoke PASS.

- KArchive `6.30.0-0supralinux4`.
  Job `104112549742`.
  Artifact `10364726750`.
  SHA-256 `0fcd8722eddf40995152df200aa576a3ff1234b8135c52e59a66f05dbc8eeb3e`.
  Tests `5/5` PASS.
  SONAME `libKF6Archive.so.6`.
  Consumer smoke PASS.

- KHolidays `6.30.0-0supralinux4`.
  Job `104112549858`.
  Artifact `10364169061`.
  SHA-256 `62186f3d6d0c856fed7b055ae917ceec0b6cdf216b37b93e22126bf3ebc8f37a`.
  Tests `8/8` PASS.
  SONAME `libKF6Holidays.so.6`.
  Consumer smoke PASS.

Todos superaron Lintian contra source y binary evidence.

Todos son downstream elegibles en el lane hosted.

### Batch 3 — 3/3 PASS

KItemModels y KPlotting conservaron sus PASS reales del primer intento de Batch 3.

- KItemModels `6.30.0-0supralinux1`.
  Run `34896417969`.
  Job `104151531993`.
  Artifact `10369501432`.
  SHA-256 `b806eaf27f733c1a2b5cc1d108ca442fef673b6dc0a53cfc5fff38abd2bf6732`.
  Tests `13/13` PASS.
  SONAME `libKF6ItemModels.so.6`.
  Consumer smoke PASS.

- KPlotting `6.30.0-0supralinux1`.
  Run `34896417969`.
  Job `104151532320`.
  Artifact `10369086459`.
  SHA-256 `f4c4f7425e582b5001fdffced34d045dc46152074422bd2bcf994e544bb96bb8`.
  Tests `5/5` PASS.
  SONAME `libKF6Plotting.so.6`.
  Consumer smoke PASS.

BluezQt attempt 1 `6.30.0-0supralinux1` permanece como FAIL histórico real de Lintian/symbols después de `18/18` tests PASS.

La remediación revisada marca `_ZSt19piecewise_construct@Base` como `(optional=toolchain)` con mínimo upstream `6.30.0`, sin modificar el resto del baseline público Debian 6.28.

BluezQt `6.30.0-0supralinux2` quedó PASS real:

- Run `34945979836`.
- Job `104305337324`.
- Artifact `10387429776`.
- SHA-256 `db8a3718a31eaae00d5f9fbdb60014dfeb1faf1c2bc84a88f9ab0d9bffec07ed`.
- Tests `18/18` PASS.
- Lintian error gate PASS.
- SONAME `libKF6BluezQt.so.6` PASS.
- Consumer smoke PASS.

Los tres nodos de Batch 3 son downstream elegibles en el lane hosted.

### Batch 4 — 3/3 PASS

KItemViews conservó su PASS real del primer intento. KGlobalAccel y KSyntaxHighlighting conservaron sus FAIL `-1` y pasaron tras una revisión de packaging `-2`.

- KItemViews `6.30.0-0supralinux1`.
  Run `34999449194`.
  Job `104483912528`.
  Artifact `10409267184`.
  SHA-256 `7e34fa7ede21510cf6829448e7b45a5c2832aaf9ac2719b9cb4125d23b593e55`.
  Tests `2/2` PASS.
  SONAME `libKF6ItemViews.so.6`.
  Consumer smoke PASS.

- KGlobalAccel attempt 1 `6.30.0-0supralinux1`.
  Run `34999449194`.
  Job `104483912661`.
  Artifact `10408264332`.
  SHA-256 `1b7564f211967d1be8b61a96bc2a67389c6164f566e54dad79682d37a33bf6e5`.
  Resultado **FAIL** en `dh_auto_configure`/CMake antes de tests.
  ECM `ECMPoQmTools` requería Qt 6 `LinguistTools`, pero faltaba `qt6-tools-dev` en Build-Depends.

- KGlobalAccel `6.30.0-0supralinux2`.
  Run `35006477086`.
  Job `104507372240`.
  Artifact `10412320520`.
  SHA-256 `cb8143633cf15745a235937ea55ee096cb094cc96da3bd1fc39dc914f3acb3b1`.
  Tests `1/1` PASS.
  Lintian error gate PASS.
  SONAME `libKF6GlobalAccel.so.6` PASS.
  Consumer smoke PASS.

- KSyntaxHighlighting attempt 1 `6.30.0-0supralinux1`.
  Run `34999449194`.
  Job `104483912313`.
  Artifact `10408154532`.
  SHA-256 `8601077898fcba1ea5708fbd4e5a1c0d877825f969b8b39999d7d6bf131fbfe4`.
  Resultado **FAIL** en `dh_auto_configure`/CMake antes de tests por la misma dependencia `LinguistTools` no provista.

- KSyntaxHighlighting `6.30.0-0supralinux2`.
  Run `35006477086`.
  Job `104507371855`.
  Artifact `10411888269`.
  SHA-256 `1ec0d1e7d046b1393fbb299c9a6fec7e85ee4ac59ed5deafa0c777ead67c0b5f`.
  Tests `8/8` PASS.
  Lintian error gate PASS.
  SONAME `libKF6SyntaxHighlighting.so.6` PASS.
  Consumer smoke PASS.

La remediación de ambos paquetes añade `qt6-tools-dev (>= 6.9.0~)` y no cambia KDE source ni ABI baseline. KItemViews fue scope-skipped en run `35006477086` y no se reconstruyó innecesariamente.

Los tres nodos de Batch 4 son downstream elegibles en el lane hosted.

## Incidentes de infraestructura

Run `34716761551` seleccionó dos nodos ya PASS incorrectamente.

KDBusAddons job `103615297686` abortó antes de source build.

Artifact `10305410248`.

SHA-256 `ce17097096841a500ce8b2e4f24171253b91ba1dce4a6560d0107d626eb32b1a`.

ThreadWeaver job `103615297757` abortó antes de source build.

Artifact `10304955612`.

SHA-256 `79e5393b892ae1ee3fb9a19c21e2f41bb691c7c55bf40487bb2d5de7c42fc507`.

Estos abortos no crean FAIL de paquetes.

Run `34884049556` reveló otro fallo del harness.

El gate Lintian reforzado no preservaba `.ddeb` referenciados.

Los paquetes ya habían completado build, tests y consumer smoke.

El incidente tampoco crea FAIL de paquetes.

Commit `e0f4e7c48dcf7541538eb919374a3f4b6c293b75` corrige el gate.

Run `34884764702` valida la corrección.

Repository Policy run `34945979830`, job `104305336760`, reveló un falso positivo del validator Batch 3.

La búsqueda textual encontraba `override_dh_makeshlibs:` antes de la invocación real `dh_makeshlibs` y concluía incorrectamente que el symbols transform estaba fuera de orden.

El packaging BluezQt ya tenía el orden correcto: primero `python3 debian/apply-symbols-delta.py`, después la invocación real `dh_makeshlibs`.

El validator ahora distingue target e invocación real. Este incidente no crea FAIL de Framework.

El validator inicial de Batch 4 en el commit `209f6234cbd94d0b4e02df509b25ae5a6e0922fd` asumió que los nodos seleccionados ya estaban en el DAG canónico y lanzó `KeyError: 'kitemviews'`.

La corrección separa evidencia de campaña abierta y promoción canónica; Repository Policy run `35006476864` pasó con esa frontera corregida. El incidente no crea FAIL de Framework.

### ECM closure scope incident

El commit de cierre Batch 4 `037b16b7954593641041953fa4a9452f819de314` disparó innecesariamente el ECM package preflight porque el selector anterior trataba `manifests/kde-dag.json` y `docs/kde-dag.md` como inputs de build. El runner ECM no consume ninguno de esos archivos.

Run `35009710506`, job `104518322483`, terminó PASS y generó artifact `10413246489`, SHA-256 `19f8ce8e17be9efab705df0a8974d89ef90ddcd06f5a9c53745f40ad227dcff4`.

Clasificación: `infrastructure-scope-selection`; `package_state_effect=none`. No reemplaza el PASS canónico ECM `6.30.0-0supralinux3`, no crea una nueva revisión y no se usa para promocionar estado.

La primera remediación en commit `906d8be5094f04d03a01de035e73b6c65ea0a58a` corrigió correctamente el pathspec, pero expuso un segundo defecto del harness: el selector imprimía `run=false` y terminaba con status 0. El workflow consume el exit status, por lo que run `35010423516`, job `104520693096`, entró incorrectamente en `sbuild` aunque el delta no contenía inputs consumidos por el package lane.

Clasificación: `infrastructure-scope-selection`; `package_state_effect=none`. Ese intento no modifica la revisión canónica de ECM y cualquier artifact que produzca es no autoritativo para promoción.

El contrato corregido queda explícito y validado: `0 = rebuild`, `1 = intentional skip`, cualquier otro status es error. El selector sigue limitado a `packages/kde/extra-cmake-modules/*`, `scripts/run-kde-ecm-package-preflight.sh` y `.github/workflows/kde-ecm-package-preflight.yml`. Cambios de DAG, evidencia, documentación, validators o del propio selector deben ejecutar el workflow pero hacer scope-skip, sin `sbuild` ni artifact nuevo.

### Batch 5 — 3/3 PASS

Batch 5 promoted KIdleTime, ModemManagerQt and NetworkManagerQt.

- KIdleTime `6.30.0-0supralinux1`: run `35014875475`, job `104535671033`, artifact `10414598079`, `1/1 PASS`.
- NetworkManagerQt `6.30.0-0supralinux1`: run `35014875475`, job `104535671250`, artifact `10414714325`, `38/38 PASS`.
- ModemManagerQt retained real FAIL attempts `-1` and `-2`. Revision `6.30.0-0supralinux3` passed run `35021323444`, job `104557423664`, artifact `10417683848`, SHA-256 `42d4f804effc6e4b9148e8c01887bdce6f95f0554ac4d03295e844a861a54eb7`, with `11/11 PASS`, Lintian, SONAME and consumer smoke PASS.

El estado canónico de cada uno es ahora PASS y downstream-eligible. Los FAIL históricos de ModemManagerQt quedan como evidencia de intentos, no como estado actual.

## Estado actual

Tier 1 queda en **25 PASS, 4 pending, 0 current FAIL, 0 BLOCKED** tras la promoción canónica de Batch 9.

Sólo artifacts PASS retenidos pueden alimentar dependientes.

Hosted package-preflight sigue sin sustituir el futuro gate autoritativo KVM/JIT.

## Próxima expansión

La lane **multi-ABI** de Batch 9 está completada: `kconfig`, `ki18n` y `sonnet` son PASS canónicos y downstream-eligible. La próxima implementación se divide entre la lane **QML/multisurface** para `kirigami` y `kquickcharts`, y la lane **multi-surface/optional** para `kuserfeedback` y `prison`.

Tras Batch 9 quedan cuatro Tier 1 pendientes: `kirigami`, `kquickcharts`, `kuserfeedback` y `prison`. Se mantiene la estrategia DAG: construir todos los independientes posibles, conservar PASS, registrar FAIL reales y marcar BLOCKED sólo por predecesor FAIL.

PR #1 permanece Draft. No merge.

<!-- BATCH6-CANONICAL-CLOSURE -->
## Batch 6 canonical closure

KWindowSystem `6.30.0-0supralinux4` and Solid `6.30.0-0supralinux2` are canonical hosted-clean-package-preflight PASS and downstream-eligible. Final evidence is workflow run `35047623320`: KWindowSystem job `104640833059`, artifact `10428130399`, ZIP SHA-256 `9c35d5e228d3f8b71fb1e84863fac030bfd26a8e3c528ae718e788708db01272`, 14/14 tests PASS; Solid job `104640833295`, artifact `10427653865`, ZIP SHA-256 `cff267d012a3e103b53bd6e19757e6c3b0af7dc873f4cd166a4505f58aee8389`, 5/5 tests PASS. Both pass Lintian error gating, consumer smoke, exact local-package installation and `apt-get check`. The shared consumer-runtime closure remediation is therefore validated. Canonical Tier 1 is **18 PASS / 11 pending / 0 current FAIL / 0 BLOCKED**. Historical FAIL attempts remain retained as evidence; BLOCKED remains distinct from FAIL.


### Batch 7 — 3/3 PASS

Canonical promotion completed on 2026-09-16.

- KCalendarCore `6.30.0-0supralinux5`: run `35130213945`, job `104909057699`, artifact `10461386548`, 507/507 tests PASS.
- KCoreAddons `6.30.0-0supralinux4`: run `35122522242`, job `104883541991`, artifact `10457958023`, 34/34 tests PASS.
- KWidgetsAddons `6.30.0-0supralinux7`: run `35145607543`, job `104960718770`, artifact `10467164025`, 27/27 tests PASS.

All three pass Lintian, exact APT runtime closure and consumer smoke; Python imports pass for their enabled bindings. Historical FAIL attempts remain retained in `manifests/kde-tier1-package-batch7-attempts.json`. Canonical Tier 1 is **21 PASS / 8 pending / 0 current FAIL / 0 BLOCKED**. KGuiAddons is no longer predecessor-blocked; its local-predecessor package runner remains to be implemented.

### Batch 8 — KGuiAddons PASS

Canonical promotion completed on 2026-09-18. KGuiAddons `6.30.0-0supralinux2` is PASS and downstream-eligible from workflow run `35185562846`, job `105086774400`, artifact `10482007092`, ZIP SHA-256 `71d32ecb50f6617ba198325a552e68e995c20c9050c7ae21f6a69d5b680184ca`. The retained package evidence records `9/9 PASS`, Lintian `PASS-errors`, consumer smoke PASS, Python import PASS, APT closure PASS and SONAME `libKF6GuiAddons.so.6`.

The DAG edge remains only `extra-cmake-modules -> kguiaddons`. KCoreAddons is deliberately **not** a KGuiAddons Framework build dependency; it is retained only for the public KImageCache development/consumer surface. Historical Batch 8 attempts 1–4 remain FAIL evidence and attempt 5 is the retained PASS.

Canonical Tier 1 is now **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED**. The next implementation lane is multi-ABI: `kconfig`, `ki18n` and `sonnet`.


### Batch 9 — multi-ABI implementation ready

KConfig, KI18n and Sonnet are independently runnable peers and have no local KDE Framework predecessor beyond retained ECM. Their source diagnostic run `35138333645` remains non-promoting DIAG_PASS evidence. The Batch 9 workflow may therefore attempt all three in parallel; a real FAIL is local to that node and does not make either peer BLOCKED.

Canonical Tier 1 remains **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED** before the first Batch 9 package attempt. Promotion is a separate step after retained real PASS evidence.


### Batch 9 attempt 1 campaign state

Run `35348130023` attempted all three independent multi-ABI peers. KI18n is retained PASS; KConfig and Sonnet are real FAILs caused by reviewed ABI-symbol metadata, not predecessor failure. Therefore neither FAIL is BLOCKED and neither invalidates the KI18n PASS. KConfig/Sonnet move to `6.30.0-0supralinux2` for deterministic symbols-delta remediation. The shared runner ShellCheck-only fix causes semantic scope to revalidate all three nodes on the next run. Canonical Tier 1 remains **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED** until separate promotion.


### Batch 9 attempt 2 campaign state

Run `35354088696` revalidated all three peers because attempt 1 had changed the shared runner. KI18n remained PASS. KConfig and Sonnet remained real FAIL rather than BLOCKED, but their reviewed ABI-symbol deltas executed successfully; the only remaining failure was Lintian's direct-build-prerequisite rule for `python3`. Attempt 3 changes only those two package trees to `6.30.0-0supralinux3`, so semantic scope must rebuild KConfig/Sonnet and retain/scope-skip KI18n. Canonical Tier 1 remains **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED** until separate promotion.


### Batch 9 validation cycle 3 infrastructure classification

Run `35355395436` is not a new package FAIL for KConfig or Sonnet. Both package builds completed tests and Lintian successfully, but the shared runner compared amd64-generated export counts with retained totals containing optional and/or architecture-inapplicable symbols. KConfig ConfigCore generated 640 exports against a required amd64 baseline of 634; SonnetCore generated 255 against a required baseline of 254. The resulting job failures are retained as **INFRA / package_state_effect=none**. They do not become PASS either, because the false-negative abort prevented later runtime/QML/consumer gates from completing.

The corrected runner derives and validates the retained baseline partition and revalidates all three multi-ABI peers. Canonical Tier 1 remains **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED** until separate promotion.


### Batch 9 validation cycle 4 package state

Run `35358920602` validates the architecture-aware runner correction. KI18n and Sonnet are retained PASS and downstream-eligible inside the campaign. KConfig is a real package FAIL at `consumer-smoke`, after all predecessor, source, test, Lintian, ABI, package-install and QML-import gates passed. The failure is local to KConfig and does not BLOCK or invalidate either peer.

The KConfig consumer failure shows that `libkf6config-dev` must pull the provider for the exported `Qt6Qml >= 6.9.0` CMake dependency. KConfig moves to `6.30.0-0supralinux4`; KI18n/Sonnet remain unchanged PASS. Canonical Tier 1 remains **22 PASS / 7 pending / 0 current FAIL / 0 BLOCKED** until separate promotion.


### Batch 9 validation cycle 5 — 3/3 retained PASS

Run `35360530830` rebuilt only KConfig after the consumer-development dependency remediation. KI18n and Sonnet scope-skipped and retain their independent cycle-4 PASS evidence. KConfig `6.30.0-0supralinux4` passed job `105650448776`, artifact `10554715051`, SHA-256 `bd36a8288c1c36fa2ae1a83d685a816cc1077fc576b59a23951972ddcbdd835e`, rootfs `cf14256f216dd3ec9a67a7bca3bd46e8624391ffe40b2c08567dc1fe90a4b9e3`, with `90/90` tests and all Lintian/ABI/APT/QML/consumer gates PASS.

The multi-ABI campaign is now **3/3 PASS retained**. This evidence does not itself mutate canonical DAG state; KConfig, KI18n and Sonnet remain canonical pending until the dedicated promotion commit. Historical FAIL and INFRA evidence is retained.


### Batch 9 — canonical closure

KConfig `6.30.0-0supralinux4`, KI18n `6.30.0-0supralinux1` and Sonnet `6.30.0-0supralinux3` are now canonical PASS/downstream-eligible DAG nodes, each depending only on retained ECM at the Framework build-DAG level. Final package evidence remains the retained Batch 9 PASS artifacts; promotion itself rebuilt nothing.

Final promotion precheck Repository Policy run `35365719747`, job `105667583358`, passed. PR CI scope-skipped KConfig job `105667619494`, KI18n job `105667619517` and Sonnet job `105667619509`.

Canonical Tier 1 is **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**. Historical Batch 9 FAIL attempts and infrastructure incidents remain retained separately.


### Batch 10 — QML/multisurface implementation ready

Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED**. Kirigami is the first runnable package node in Batch 10. KQuickCharts has no upstream KDE Framework build edge to Kirigami, but its complete package/QML runtime gate requires a retained Kirigami SupraLINUX PASS. This ordering is tracked separately from the KDE build DAG.

If Kirigami is attempted and FAILs, KQuickCharts is not attempted and is recorded BLOCKED for package validation. If Kirigami passes, its artifact feeds KQuickCharts runtime/QML validation. Historical DIAG_PASS evidence remains non-promoting.

### Batch 10 cycle 1

PR CI `35389030840` confirms the DAG semantics in practice: Kirigami attempt 1 is a real package FAIL, while KQuickCharts is BLOCKED and unattempted because its package-validation predecessor did not PASS. The remediation changes only Kirigami packaging/evidence; no KDE Framework build edge or canonical DAG dependency changes. Canonical Tier 1 remains **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until successful package evidence is separately promoted.

### Batch 10 cycle 2

Run `35392233659` did not create a second Kirigami package FAIL. The package reached consumer validation after all earlier gates passed; the final failure came from a wrong CMake package name in the repository harness. It is an infrastructure validation incident with no package-state effect.

KQuickCharts again remained BLOCKED/unattempted because the Kirigami validation job did not finish PASS. No DAG edge changes.

### Batch 10 cycle 3

Kirigami now has retained PASS evidence from run `35398956698`. KQuickCharts was therefore unblocked and attempted for the first time, then failed locally at its own retained symbols contract after `8/8` tests PASS.

This changes operational campaign state only: Kirigami is retained PASS, KQuickCharts is remediation-pending-build at `6.30.0-0supralinux2`. The canonical DAG remains unchanged at **25 PASS / 4 pending / 0 current FAIL / 0 BLOCKED** until the separate Batch 10 promotion.
