# Puertas de distribución (D00–D12)
Estado de todas: NOT_RUN. No distro ni release existente.
| ID | Evidencia exigida |
|---|---|
| D00 | Comparativa Arkdep/RAUC/sysupdate, licencia, mantenimiento, modelo de datos y coste |
| D01 | Snapshot Arch coherente, PKGBUILD, locks, firmas y SBOM |
| D02 | Imagen de prueba arranca en KVM/UEFI y sesión mínima |
| D03 | Actualización interrumpida en descarga, stage y boot; anterior sigue arrancable |
| D04 | Boot assessment/rollback, datos y migraciones compatibles, espacio insuficiente |
| D05 | Flatpak, AppImage/AppDir, Applications, sin autoejecución, sin .deb |
| D06 | instalación bajo demanda de módulo de prueba (v4l2loopback candidato), rebuild por kernel y rollback |
| D07 | NVIDIA/Intel/AMD, legacy, CUDA/VRAM bajo carga, multilib y juegos |
| D08 | AUR build separado, exportación, perfil restringido y host por capas |
| D09 | Verificación firmas, boot trust, módulos, recovery y permisos; pruebas negativas inocuas |
| D10 | Instalador, cifrado, dual boot, recuperación y hardware |
| D11 | CVE, canales, promoción, revocación y disponibilidad de artefactos |
| D12 | Auditoría, documentación, soporte y aprobación explícita antes de publicación |
No declarar PASS sin evidencia; no confundir checks Markdown con pruebas. Mantener track distro separado de desarrollo de compositor; no bloquear M01/M02. D00 requiere decisión de nombre/repositorio/alcance y recursos de mantenimiento; no migrar SupraLINUX existente.

[Matriz D ampliada](DEEP_VALIDATION.md) descompone las 18 áreas y sus casos de prueba. Todos NOT_RUN. Prioridad: D00 backend y layering; D01 reproducibilidad; D03/D04 fallos; D06 módulos; D09 confianza; UX transversal.
