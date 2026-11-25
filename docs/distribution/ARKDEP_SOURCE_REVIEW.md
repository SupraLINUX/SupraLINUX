# Revisión estática de Arkdep y alternativas — 2026-11-24

Estado PROPOSED / NOT_RUN. No auditoría exhaustiva de seguridad, no ejecución, no fork. Revisión exacta de [arkdep d7aa2f7](https://github.com/arkanelinux/arkdep/blob/d7aa2f7de742a97eaa39b6dd57710222c26a633c/arkdep), script principal de 1580 líneas, repositorio GPL-3.0 según metadata GitHub. Verificar texto de licencia y avisos por archivo antes de incorporar.

| Referencia de código | Hallazgo | Requisito para nuestro producto |
|---|---|---|
| L21, L1035–1072 | Modos de firma; descarga de firma puede omitirse en modo 1 | Firma requerida y keyring válido, error explícito ante ausencia de confianza |
| L31–32, L1453–1475 | Layer cambia root RO a RW si procede, instala en activo y añade al tracker | No exponer layer/unlayer in-place; resolver y componer siguiente despliegue |
| L1183–1198 | Instala lista global en root destino, fallo de pacman produce advertencia | Fallo de capa bloquea activación; manifiesto de paquetes reales por despliegue |
| L1200–1205 | Migración de rutas locales | Inventario de datos y reglas por dominio, pruebas de reversibilidad |
| L1295–1309, L1330–1359 | Tracker actualizado antes de entrada boot; extensiones y script de migración forman parte del flujo | Orden recuperable de commit, validación de hooks, reconciliación de root/boot/manifest; no asumir atomicidad entre Btrfs y ESP |
| L1343–1347 | Entrada systemd-boot con +3 intentos | Reutilizar boot counting; validar selección fallback y health gate, no considerar ya resuelto |

El default package-layer-command usa pacman -Syy --needed --noconfirm; no es la política de snapshot coherente requerida. No utilizar operaciones in-place del upstream en interfaz oficial. La longitud del script solo orienta coste, no demuestra facilidad de mantenimiento. [Documentación de uso](https://docs.arkanelinux.org/arkdep/usage/) confirma desalineación del tracker tras rollback y omisión de capas fallidas.

## Estrategia
SupraDeploy es interfaz versionada de transacciones de la distribución, no un segundo gestor de paquetes ni dependencia obligatoria de SupraDesktop. Separar cliente GUI/CLI/MCP, servicio privilegiado con acciones tipadas y consentimiento humano, planificador de paquetes, estado efectivo por despliegue, adaptador backend. Prototipo con Arkdep fijado y parches mínimos; conservar build, transferencia, creación Btrfs y boot integration donde cumplen. No mantener dos registros autoritativos; backend expone hechos, registro reconcilia. Evitar analizar texto de progreso Bash como contrato estable: eventos estructurados, errores y estado consultable. No exponer comando shell arbitrario. Código GPL adaptado con licencia, avisos, fuente y revisión upstream; Rust para componentes nuevos si conveniente, no reescritura total por lenguaje. Separación por proceso no decide por sí sola obligaciones de licencia.

## Comparativa revisada
- [Solera 0b405285](https://github.com/calambrenet/solera/tree/0b4052851d831820345203fc54c4ea0aef8059f4) utiliza Arkdep, snapshots fechados y paquetes propios. Su [CLI](https://github.com/calambrenet/solera/blob/0b4052851d831820345203fc54c4ea0aef8059f4/packages/solera-config/src/solera-cli/solera) delega layer/unlayer/layer-ls (L61–73). No resuelve por sí mismo deficiencias de layering; referencia de pipeline. README dice alpha, sitio dice beta; no inferir madurez de producción ni reproducibilidad bit a bit sin test.
- [Shanios filesystem](https://docs.shani.dev/doc/arch/filesystem/) describe blue/green y subvolúmenes persistentes por dominio. Referencia de estado y recuperación, no evidencia de capas host equivalentes.
- [blendOS](https://blendos.co/install/post-install/intro/) referencia declaración de paquetes/kernel; no adoptar distro completa.
- [bootc e074dc8](https://github.com/bootc-dev/bootc/tree/e074dc8e5f0711844620491c1084517abf804c33/docs/src) documenta local builds y switch de imagen, integración de gestores y detección de fallos distinta en OSTree/composefs. [Local builds](https://github.com/bootc-dev/bootc/blob/e074dc8e5f0711844620491c1084517abf804c33/docs/src/bootc-local-builds.7.md). OCI atractivo para distribución, pero Arch, pacman DB, módulos y local layers requieren prueba. No declarar que soporte Fedora equivale a soporte Arch. 
- [sysupdate.d](https://man.archlinux.org/man/core/systemd/sysupdate.d.5.en) admite targets Btrfs subvolume y recursos versionados; composición de paquetes y recovery propios. [RAUC](https://rauc.readthedocs.io/en/stable/) alternativa slots fijos, no resolver AUR por sí.
- [Automatic Boot Assessment](https://systemd.io/AUTOMATIC_BOOT_ASSESSMENT/): boot counting y bless-boot son piezas reutilizables, hay que definir boot-complete gate y estrategia de reinicio tras fallo; no confundir contador con watchdog.

Decisión profesional provisional: Arkdep primero. Si parches afectan arquitectura central de despliegue, comparar sysupdate con composición local acotada, luego RAUC según diseño de almacenamiento. No mantener todas las opciones en producción. Gates en PROTOTYPE_GATES.md.