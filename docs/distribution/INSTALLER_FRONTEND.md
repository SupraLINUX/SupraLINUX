# Instalador visual 1:1 y recuperación
Dirección ACCEPTED por mantenedor: adaptar frontends a experiencia visual macOS, mantener lógica fiable; no recursos Apple; seguridad, accesibilidad y Beginner First. Implementación PROPOSED, NOT_RUN.

## Fuente activa
[Calamares oficial](https://calamares.codeberg.page/) anuncia serie 3.4 y release 3.4.2; migración a [Codeberg](https://codeberg.org/Calamares/calamares). GitHub histórico archivado. Se inspeccionó revisión histórica [95aa33f branding.desc](https://github.com/calamares/calamares/blob/95aa33fd2f0ea6f081fe604fb84eb829fc806d86/src/branding/default/branding.desc), L32–90, L173–195, y [módulos](https://github.com/calamares/calamares/blob/95aa33fd2f0ea6f081fe604fb84eb829fc806d86/src/modules/README.md). Documentan QSS, QML sidebar/navigation, ventana, slideshow, módulos view y job. Revalidar APIs en versión activa: acceso directo a repositorio Codeberg no disponible en esta revisión. No fijar versión histórica por comodidad.

## Capas
1. Branding propio, QML sidebar/navigation, paleta, tipografía libre, iconos y tokens generados. Usar QSS donde widgets lo permiten. 
2. Adaptar viewmodules C++/QML cuando branding no cubra geometría o interacción. No alterar cálculos de partición ni validar menos por estética; si se requiere nuevo view, conservar modelo/validación.
3. Job atómico específico de distribución: plan de instalación validado, disco seleccionado, cifrado, layout, imagen firmada, despliegue, boot assets, prueba final. Backend separado de presentación. No reutilizar un job de instalación convencional si contradice layout.
4. SupraSetup tras primer arranque: idioma, región, accesibilidad, apariencia y privacidad, cuenta local sin red ni IA obligatoria. No repetir configuración.
5. SupraRecovery con entorno independiente del compositor principal, herramientas verificadas y opciones de rollback, modo seguro, reinstalación, backup y diagnóstico. Medio externo offline. No prometer reparar todo automáticamente.

Preferir C++/QML existente para adaptar Calamares a Rust First razonado, no reimplementar particionador. Una UI SupraUI propia posterior solo si justificada por fidelidad y APIs. Consumo de tokens común sin depender de SupraDesktop en recovery. Separar privilegios y operaciones destructivas de presentación donde arquitectura lo permita; consentimiento de disco/cambios y progreso real. No copiar arte, fuentes o branding Apple.

## Pruebas
I01 branding/UI sintética clara/oscura, teclado/lector, es-AR/RTL, escala y ROI; I02 geometría de páginas, progreso indeterminado/determinado y errores sin falsear; I03 equivalencia de plan de disco entre frontend modificado y referencia en VM; I04 disco descartable, UEFI, LUKS2, instalación offline, reboot; I05 cancelación antes de commit y fallos durante jobs, explicar consecuencias; I06 recovery con compositor ausente, red ausente, versión anterior y medio externo; I07 dual boot fixture y preservación de datos únicamente si plan lo garantiza. Todos NOT_RUN.
Documentación activa [configuración](https://calamares.codeberg.page/docs/deploy-configuration/) y [tester guide](https://calamares.codeberg.page/docs/test-guide/) confirma configuración modular. [Laboratorio](RELEASE_LAB.md). No inspección de código actual Codeberg ni prueba visual todavía.
