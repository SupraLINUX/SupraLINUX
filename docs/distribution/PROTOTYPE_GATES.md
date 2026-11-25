# Cierre de investigación y primeros prototipos

Estado NOT_RUN. No instalar en host ni modificar discos reales. No publicación estable. No migrar SupraLINUX; distribución en repo diferenciado cuando mantenedor lo autorice. Limitar trabajo nuevo a decisiones que reduzcan riesgo, no aumentar indefinidamente subsistemas.

| Gate | Evidencia | Criterio de rechazo |
|---|---|---|
| D-P0 | VM UEFI descartable, baseline Arkdep fijado, build de snapshot coherente | No reproducible o no se puede reconstruir entorno |
| D-P1 | Instalar paquete normal por capa en despliegue nuevo, manifest efectivo, base anterior intacta | Activo modificado, capa fallida omitida, tracker falso |
| D-P2 | Cortes en descarga, staging, commit manifest/boot, arranque y health check | Sin known-good arrancable o datos de prueba perdidos |
| D-P3 | Paquete AUR inocuo y módulo de prueba opcional contra kernel destino | Dependencia incompatible activada, versión kernel/módulo discordante |
| D-P4 | Firma obligatoria, espacio insuficiente, rollback offline, config y estado persistente | Aceptación no autorizada, pérdida de documentos, selección de despliegue incoherente |
| D-P5 | Comparar coste parches y mantenibilidad con sysupdate/RAUC solo si gates fallan | No aceptar por afinidad ni por número de líneas |
| D-P6 | Calamares activo con branding y vista sintética, plan de instalación equivalente, job atómico en disco descartable | Regresión en validación, accesibilidad o consentimiento |
| M-P1 | SupraLab fixtures originales, tokens y geometría | No reproducible, material no medible |
| M-P2 | Compositor anidado Smithay, ventana y efecto de fondo | No funciona sin tocar sesión host |
| M-P3 | Toolkit candidato, texto, a11y y acción tipada con permisos | Incapaz de satisfacer control visual y semántico |

Medir tiempo, disco, bytes, compatibilidad y esfuerzo de mantenimiento; registrar commit exacto, artefacto, entorno, comandos y resultados. Pruebas de fallo con fixtures de prueba, no sistemas reales. Elegir backend tras gates D-P0–D-P4, o comparar alternativa acotada; no construir todas. Contratos de UI/CLI/MCP no dependen de proveedor. Separar estado de arranque técnico y confirmación de experiencia; no exigir login manual para todas las actualizaciones ni marcar good antes de health check apropiado. Automatización de pruebas y resultados auditables. Antes de incorporar código resolver licencia del componente y núcleo; antes de 1:1 obtener referencia macOS nativa autorizada.
[Laboratorio de validación](../testing/VALIDATION_LAB.md) descompone las 14 incertidumbres. D-P0–D-P4 en VM descartable y M-P1–M-P3 anidado/headless. No pruebas ejecutadas.
