# KDE Frameworks 6.30 — Tier 1 package Batch 2

Status: **PASS — 3/3 hosted clean-package preflight**

Last reviewed: **2026-09-14**

KDE Frameworks 6.30.0 sigue siendo la autoridad upstream.

Ubuntu Resolute sigue siendo proveedor y objetivo de compatibilidad.

ECM `6.30.0-0supralinux3` sigue siendo el predecesor PASS.

Este Batch 2 no constituye todavía prueba KVM/JIT autoritativa.

## Nodos promovidos

- `KTextTemplate 6.30.0-0supralinux3`: **PASS**.
- `KArchive 6.30.0-0supralinux4`: **PASS**.
- `KHolidays 6.30.0-0supralinux4`: **PASS**.

Los tres nodos son `downstream_eligible=true` para campañas hosted posteriores.

No conviertas `SKIPPED` en `PASS`.

Conserva los FAIL históricos después de una revisión posterior PASS.

## Campaña final

Usa workflow `34884764702`.

Usa commit `e0f4e7c48dcf7541538eb919374a3f4b6c293b75`.

El workflow ejecutó realmente los tres nodos.

### KTextTemplate

Usa job `104112549851`.

Usa artifact `10363863115`.

Usa artifact SHA-256 `7b9d0390ed90c882f4b7ad1993924e722bfb7ad35238c2ced52bbd5809555bc9`.

Conserva `10/10` tests PASS.

Conserva Lintian sin errores.

Conserva consumer smoke PASS.

Conserva SONAME `libKF6TextTemplate.so.6`.

### KArchive

Usa job `104112549742`.

Usa artifact `10364726750`.

Usa artifact SHA-256 `0fcd8722eddf40995152df200aa576a3ff1234b8135c52e59a66f05dbc8eeb3e`.

Conserva `5/5` tests PASS.

Conserva Lintian sin errores.

Conserva consumer smoke PASS.

Conserva SONAME `libKF6Archive.so.6`.

### KHolidays

Usa job `104112549858`.

Usa artifact `10364169061`.

Usa artifact SHA-256 `62186f3d6d0c856fed7b055ae917ceec0b6cdf216b37b93e22126bf3ebc8f37a`.

Conserva `8/8` tests PASS.

Conserva Lintian sin errores.

Conserva consumer smoke PASS.

Conserva SONAME `libKF6Holidays.so.6`.

## Historia KTextTemplate

Workflow `34720201713` produjo FAIL en `dpkg-gensymbols`.

Sus `10/10` tests habían pasado antes del fallo.

KDE 6.30 añadió tres símbolos públicos `Filter`.

KDE 6.30 dejó de exportar símbolos internos del plugin principal.

La transformación ABI permanece determinística y versionada.

Workflow `34776524481` validó la revisión `-0supralinux2`.

Ese PASS queda como evidencia histórica.

## Historia KArchive

Workflow `34720201713` falló por `Qt6::LinguistTools` ausente.

Añade `qt6-tools-dev` como proveedor técnico del requisito KDE.

Ubuntu no se convierte por ello en autoridad sobre Qt.

Workflow `34776389758` alcanzó `5/5` tests PASS.

Ese intento falló porque `KF6Archive.pc` no estaba empaquetado.

Workflow `34834818877` falló en el consumer smoke.

El probe usaba `<KArchive/KZip>` incorrectamente.

El include correcto es `<KZip>`.

Workflow `34843318489` validó `KArchive -3`.

Ese PASS queda como evidencia histórica.

## Historia KHolidays

Workflow `34720201713` falló por `Qt6::LinguistTools` ausente.

Workflow `34776389758` alcanzó `8/8` tests PASS.

Ese intento reveló 36 símbolos públicos nuevos de calendario hebreo.

Mantén esos símbolos con versión mínima upstream `6.30.0`.

Workflow `34834818877` emitió un `false PASS` del pipeline.

La revisión posterior reclasificó correctamente ese intento como FAIL.

El error era `rules-require-build-prerequisite`.

`debian/rules` ejecutaba Python sin declarar `python3`.

`python3:any` está ahora declarado en `Build-Depends`.

## Gate Lintian

Rechaza cualquier `Lintian: fail` informado por `sbuild`.

Ejecuta además Lintian contra `.dsc` y `.changes`.

Preserva los `.ddeb` referenciados antes de esa validación.

Conserva sus SHA-256 como evidencia.

Elimina `dag-node.txt` cuando el gate falle.

Publica PASS sólo después del gate completo.

## Incidente de infraestructura

Workflow `34884049556` no produjo FAIL propios de paquetes.

Los tres builds completaron tests y consumer smoke.

El wrapper omitió `.ddeb` referenciados por `.changes`.

Lintian abortó por evidencia incompleta.

Commit `e0f4e7c48dcf7541538eb919374a3f4b6c293b75` corrigió esa captura.

Workflow `34884764702` validó la corrección completa.

## Política de paquetes `-doc`

Mantén los nombres `-doc` por compatibilidad Debian-family.

No declares contenido QCH inexistente.

Los tres paquetes actuales sólo contienen metadatos Debian.

Mantén QDoc fuera del build predeterminado actual.

Revisa una política QDoc común antes de añadir QCH real.

## Estado canónico

Promueve los tres nodos a `PASS`.

Marca los tres como downstream elegibles.

Actualiza `manifests/kde-frameworks-tier1.json`.

Actualiza `manifests/kde-dag.json`.

El Tier 1 queda en **7 PASS / 22 pending / 0 FAIL / 0 BLOCKED**.

Mantén el PR #1 en Draft.
