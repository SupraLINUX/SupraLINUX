# KDE Frameworks 6.30 — Tier 1 package Batch 2

Status: **remediation-pending-build**

Last reviewed: **2026-09-14**

Mantén KDE Frameworks 6.30.0 como autoridad upstream.

Mantén Ubuntu Resolute como proveedor y objetivo de compatibilidad.

Mantén ECM `6.30.0-0supralinux3` como predecesor PASS.

## Nodos

Incluye `KTextTemplate`, `KArchive` y `KHolidays`.

Trata cada nodo como independiente.

No conviertas `SKIPPED` en `PASS`.

Promueve un nodo solamente después de una compilación real.

## Intento 1

Usa workflow `34720201713` como primera campaña real.

Usa commit `5edf71b390088a551af81e7fc7e8d87a8378104f`.

Clasifica `KTextTemplate` como FAIL en `dpkg-gensymbols`.

Conserva sus `10/10` tests PASS previos al fallo.

Clasifica `KArchive` como FAIL por `Qt6::LinguistTools` ausente.

Clasifica `KHolidays` como FAIL por `Qt6::LinguistTools` ausente.

Añade `qt6-tools-dev` como proveedor de `Qt6::LinguistTools`.

No conviertas Ubuntu en autoridad sobre Qt.

## Intento 2

Usa workflow `34776389758` como segunda campaña.

Clasifica `KTextTemplate` como PASS real.

Conserva su ABI transformado desde Debian 6.28.

Conserva `KArchive` como FAIL tras `5/5` tests PASS.

Identifica `KF6Archive.pc` como archivo omitido del paquete `-dev`.

Conserva `KHolidays` como FAIL tras `8/8` tests PASS.

Registra 36 símbolos públicos nuevos de calendario hebreo.

Mantén esos símbolos con versión mínima upstream `6.30.0`.

## Revalidación KTextTemplate

Usa workflow `34776524481` como PASS revalidado.

Usa artifact `10323233062`.

Usa SHA-256 `c0825408584e8d2e37a66ba95764e3e33adeafeaa5adcb30c253fb706c6c9f27`.

Conserva `10/10` tests PASS.

Conserva SONAME `libKF6TextTemplate.so.6`.

Trata ese PASS como histórico para revisión `-0supralinux2`.

## Intento 3

Usa workflow `34834818877` como tercera campaña.

Usa commit `1634e56fcbb7dd4cc7a931f98a846b485c84077e`.

Clasifica `KArchive` como FAIL en `consumer-smoke`.

Conserva `5/5` tests PASS y Lintian sin errores.

Corrige el probe desde `<KArchive/KZip>` hacia `<KZip>`.

Reclasifica `KHolidays` como FAIL validado.

No mantengas el `false PASS` emitido por el gate anterior.

Conserva artifact `10343623713` como evidencia histórica.

Conserva SHA-256 `bb6ce23797d69f46f430fa53fef9e439b94772ce4566a3684f3a7038cada854d`.

Conserva `8/8` tests PASS y consumer smoke PASS.

Registra el error Lintian `rules-require-build-prerequisite`.

Añade `python3:any` porque `debian/rules` ejecuta Python.

Identifica la causa del `false PASS` en el gate anterior.

El gate anterior validaba sólo `.changes` después de `sbuild`.

El log `sbuild` ya contenía `Lintian: fail`.

## KArchive PASS histórico

Usa workflow `34843318489` como PASS real de `KArchive -3`.

Usa artifact `10346983258`.

Usa SHA-256 `2f851d5c3cf2f568e87f075483f86a8107eba635956982220c35533c9be8cf3b`.

Conserva `5/5` tests PASS.

Conserva SONAME `libKF6Archive.so.6`.

Conserva consumer smoke PASS.

Trata ese PASS como histórico tras abrir revisión `-0supralinux4`.

## Gate Lintian corregido

Ejecuta primero el runner de compilación existente.

Rechaza cualquier resumen `Lintian: fail` emitido por `sbuild`.

Ejecuta Lintian contra `.dsc` y `.changes` conjuntamente.

Corrige `result.json` a FAIL cuando falle el gate.

Elimina `dag-node.txt` cuando falle el gate.

Publica PASS sólo después del gate corregido.

## Política de paquetes `-doc`

Mantén los nombres `-doc` por compatibilidad Debian-family.

No declares contenido QCH inexistente.

Los tres paquetes actuales sólo contienen metadatos Debian.

Documenta explícitamente esa ausencia en `debian/control`.

Mantén QDoc fuera del build predeterminado actual.

Revisa una política QDoc común antes de añadir QCH real.

## Revisiones pendientes

Compila `KTextTemplate 6.30.0-0supralinux3`.

Compila `KArchive 6.30.0-0supralinux4`.

Compila `KHolidays 6.30.0-0supralinux4`.

Mantén los tres nodos como `remediation-pending-build`.

Mantén `downstream_eligible=false` para las revisiones pendientes.

Conserva todo PASS anterior como evidencia histórica.

Actualiza el DAG canónico sólo después del cierre completo.

Mantén el PR #1 en Draft.
