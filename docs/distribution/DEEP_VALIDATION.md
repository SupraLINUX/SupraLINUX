# Matriz ampliada de investigación D
Consulta documental 2026-11-24. Todos NOT_RUN, no imagen ni benchmark. Cada prueba registra commit, base snapshot, VM/hardware, entradas, logs, métricas, estado efectivo y limitaciones. No sustituye D00–D12.
| Área | Documento | Prueba concreta |
|---|---|---|
| Arkdep/RAUC/sysupdate | BACKEND_EVALUATION | mismo workload, comparar coste, corte en cada fase, no mutar activo |
| Congelación Arch | DELIVERY_SECURITY | reconstruir closure desde lock, mirror rolling no permitido |
| Atomicidad/rollback | DEPLOYMENT | fallo antes/después de boot commit, boot counting, known-good |
| DKMS | KERNEL_EXTENSIONS | módulo bajo demanda, rebuild exacto, fallo kernel y rollback |
| Firma | TRUST_BOOT | paquete/manifest inválido, rotación, origen local vs oficial |
| Secure Boot/UKI | TRUST_BOOT | OVMF y hardware, boot signed y fallback, módulos policy |
| Configuración | STATE_RECOVERY | merge /etc, conflicto, account IDs, DB schema y rollback |
| AUR | PACKAGE_LAYERING | tres destinos, paquete normal/local, dependencias, rollback tracker |
| CUDA/NVIDIA/gaming | GPU_COMPATIBILITY | GPU real, CDI, GL32, pressure, suspend, juego |
| Archiso/Calamares | INSTALLER_HARDWARE | instalación offline y dual boot en disco fixture, cifrado y recovery |
| LUKS2 | TRUST_BOOT | passphrase/recovery, TPM opcional, rollback y pérdida de TPM |
| Recovery offline | STATE_RECOVERY | red ausente, modo seguro y medio externo, datos protegidos |
| Deltas | DELIVERY_SECURITY | full vs delta bytes, parent mismatch, reanudar y full fallback |
| Repos/entrega | DELIVERY_SECURITY | mirror corrupto/no disponible, resume, retention/restore |
| CVE | DELIVERY_SECURITY | inventario, advisory sintético, emergency release y capa bloqueante |
| Canales | DELIVERY_SECURITY | mismo digest promoción, pausa, cambio de canal/rollback informado |
| Datos | STATE_RECOVERY | home/app/var preservados, migration reversible y cuotas |
| Backups | STATE_RECOVERY | destino independiente, restauración de muestra y pérdida disco fixture |
UX transversal: USER_EXPERIENCE, tareas sin terminal, accesibilidad, progreso real, origen y riesgos comprendidos. D00/D01/D03/D04/D06/D09 críticos y no compensables; no publicar hasta gates, licencia, recursos de mantenimiento y aprobación. No se fijó nombre ni repositorio de distro.
## Gate de elección del backend y frontend
[PROTOTYPE_GATES.md](PROTOTYPE_GATES.md). Verificar que el contador de arranque existente de Arkdep se combina con health gate real; no confundir tres intentos con recuperación demostrada. Auditar transacción multi-recurso, AUR y persistencia. Probar presentación Calamares con datos sintéticos y disco descartable antes de adaptar particionador.
