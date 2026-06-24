# Prompt para Claude (modo diseño / artifact) — Rediseño UI/UX "Síntesis de Briefings CIITEC"

> Pega todo el bloque siguiente en una conversación nueva de Claude (con artifacts/diseño activado).
> El objetivo es obtener un **mockup interactivo de alta fidelidad** que sirva de base para reimplementar el frontend real (React + TS + Vite, PWA).

---

## ROL Y OBJETIVO

Actúa como **diseñador de producto senior + diseñador de sistemas de diseño** especializado en
**aplicaciones de software para gobierno, defensa y seguridad** (herramientas densas en datos, de misión crítica,
para operadores profesionales — no productos de consumo).

Tu tarea: rediseñar por completo la estética y la UX/UI de una aplicación web interna y producir
**un único artifact interactivo de alta fidelidad** (React + Tailwind, autocontenido, sin backend)
que muestre **todas las pantallas** con datos ficticios realistas en español. Ese mockup será la
**fuente de verdad visual** para reimplementar el frontend de producción.

Antes de diseñar, define un **sistema de diseño** (tokens, tipografía, color, espaciado, componentes) y
aplícalo de forma consistente en todas las pantallas. Prioriza: **gravedad institucional + claridad
operacional + densidad de datos legible**. Moderno y pulcro, NO infantil, NO "startup colorida".

---

## CONTEXTO DEL PRODUCTO (léelo entero antes de diseñar)

**Producto:** "Sistema de Síntesis Automática de Briefings Operacionales".
**Cliente:** CIITEC / Ejército de Chile. Aplicación **web interna on-premise**, en **español de Chile**,
usada en intranet por personal militar y analistas.

**Qué hace:** Lee documentos heterogéneos (PDF, Word, Excel, correos, bitácoras), extrae "hechos" con un
LLM, genera un **briefing institucional** (estructura de 6 páginas: Portada, Personal, Inteligencia,
Operaciones ×2, Logística), detecta inconsistencias, mantiene versiones trazables y exporta a PDF/Word/Texto.

**Flujo central que el usuario debe sentir:** **Cargar → Generar → Revisar → Exportar.**

**Usuarios / roles (con nivel de habilitación):**
- Oficial de Operaciones (RESERVADO)
- Analista de Operaciones (RESERVADO)
- Comandante (SECRETO) — aprueba versiones
- Auditor (SECRETO) — solo lectura + auditoría
- Administrador del Sistema (SECRETO)

**Concepto crítico — Clasificación de seguridad (3 niveles).** Es el rasgo visual más importante. Cada
documento, briefing y versión tiene un nivel, con código de color **semántico y consistente** en toda la app:
- `PÚBLICO` → verde
- `RESERVADO` → ámbar/naranja
- `SECRETO` → rojo

Debe haber una **banda/cinta de clasificación** visible (estilo marcado institucional) y badges en cada
entidad. El nivel de habilitación del usuario (en la barra superior) condiciona qué puede ver.

**Restricciones reales que el diseño debe reflejar:**
- Conectividad degradada: **modo offline (PWA)**. Indicador claro de OFFLINE + cola de cargas pendientes de sincronizar.
- Procesamiento asíncrono: la generación corre en un pipeline de 5 etapas
  (**Ingestar → Normalizar → Extraer → Detectar → Sintetizar**) y reporta progreso **en vivo por WebSocket**.
  Necesito una experiencia de progreso excelente (stepper + consola de log en vivo), no un spinner.
- Sesión que expira por inactividad (15 min) → patrón de aviso de sesión.
- Auditoría inmutable con **cadena de hash** (cada evento encadena un hash con el anterior); hay que poder
  **verificar la integridad** de la cadena visualmente.
- Trazabilidad: cada bullet del briefing enlaza a un "hecho" y éste a su "fuente" (documento original).
  El diseño debe hacer evidente y navegable esa cadena **bullet → hecho → fuente**.
- Casillas numéricas faltantes se muestran como `-.-` (no inventar datos).

---

## PANTALLAS A DISEÑAR (todas, navegables dentro del mockup)

1. **Login — "Acceso institucional".** Sobrio, con escudo/marca institucional (usa un placeholder de escudo),
   campo usuario/contraseña, aviso de sistema clasificado (banner legal), estado de conexión. Transmite confianza y autoridad.

2. **Cargar + Generar.** El corazón operativo. Incluye:
   - Zona de carga (drag & drop) multi-archivo con lista de archivos, tamaños e iconos por tipo (PDF/Word/Excel/correo/bitácora).
   - Selector de **nivel de clasificación** de la carga.
   - Estado **OFFLINE** + botón "Sincronizar cola (N)" cuando hay cargas pendientes.
   - Campo de **título** del briefing.
   - Botón "Cargar → Generar → Exportar".
   - **Experiencia de progreso en vivo:** stepper de las 5 etapas del pipeline + **consola de log**
     (estilo terminal, monoespaciada) que va imprimiendo `· etapa — documento` y termina en "✅ Briefing listo".
     Diseña también los estados de error de etapa.

3. **Briefings (listado).** Tabla/tarjetas densas: título, badge de clasificación, estado
   (BORRADOR / GENERANDO / LISTO / APROBADO), versión activa, fecha, nº de fuentes. Filtros por estado y
   clasificación, búsqueda, orden. Estado vacío bien diseñado.

4. **Briefing (detalle) — la pantalla más rica.** Debe organizar mucha información sin saturar:
   - Encabezado: título, badge de clasificación, estado, versión activa, botones **Exportar PDF / Word / Texto**.
   - **Resumen ejecutivo** (bullets).
   - **Asuntos críticos** (tabla: Asunto · Impacto · Responsable).
   - **Proyección 24–72 h**.
   - **Secciones institucionales** (Personal · Inteligencia · Operaciones · Logística) — agrupadas/colapsables,
     con cifras tipo tablero (donut/contadores) y `-.-` donde falte el dato.
   - **Inconsistencias (RF-005):** lista con tipo (DUPLICADO / CONTRADICCIÓN / DESACTUALIZADO / INCOMPLETO),
     cada tipo con su color de badge, y descripción.
   - **Trazabilidad (RF-006):** vista navegable bullet → hecho → fuente (idealmente al hacer hover/click en
     un bullet se resalta su hecho y su documento origen).
   - **Versiones (RF-007):** timeline/tabla de versiones (nº, comentario, aprobada sí/no, autor, fecha),
     acción **Aprobar** (solo Comandante), y **diff** entre versiones.
   - **Reconstrucción point-in-time (RF-009):** selector de fecha/hora → "estado del briefing a esa hora".

5. **Auditoría (solo Auditor/Seguridad/Admin).** Tabla del **audit log inmutable**: timestamp, usuario, acción,
   entidad, nivel, hash (truncado). Botón **"Verificar integridad de la cadena"** con resultado visual
   (cadena íntegra ✓ / rota ✗ en evento N). Filtros por usuario/acción/fecha. Debe sentirse forense y confiable.

**Chrome común:** barra superior con marca, navegación (Cargar · Briefings · Auditoría), identidad del usuario
+ su nivel de habilitación, botón Salir, indicador online/offline, y la **cinta de clasificación** global.

---

## SISTEMA DE DISEÑO (defínelo y muéstralo)

- **Lenguaje visual:** institucional/militar moderno. Serio, sobrio, de alto contraste, "command-center".
  Inspiración: paneles de control gubernamentales y herramientas de inteligencia bien diseñadas
  (no dashboards genéricos de SaaS).
- **Paleta:** una base neutra profesional (grises/azul pizarra institucional) + el azul/verde institucional
  como acento. El color **fuerte** se reserva para la **semántica de clasificación y estado** (verde/ámbar/rojo),
  para que el color comunique riesgo, no decoración.
- **Modo claro y modo oscuro** (el oscuro pensado para sala de operaciones). Ambos accesibles.
- **Tipografía:** una sans legible y de aire técnico/institucional; números tabulares para tablas y cifras;
  monoespaciada para la consola de log y hashes.
- **Densidad:** alta pero respirable. Tablas compactas, jerarquía clara, mucho dato sin ruido.
- **Componentes a especificar** (con sus estados): botones (primario/secundario/peligro/disabled),
  inputs/select, badges de clasificación, pills de estado, tablas densas, tarjetas, stepper de pipeline,
  consola de log, banner/cinta de clasificación, indicador offline, toasts, modal de confirmación,
  aviso de expiración de sesión, estados vacíos, estados de carga (skeletons) y de error.
- **Accesibilidad:** contraste AA mínimo, foco visible, no depender solo del color (íconos/etiquetas
  junto al color de clasificación), tamaños táctiles, navegación por teclado.
- **Microinteracciones** sobrias: transiciones discretas, feedback inmediato. Nada llamativo ni lúdico.

---

## ENTREGABLES (en el artifact)

1. Una **página "Design System"** al inicio del mockup: paleta (con los 3 colores de clasificación y
   los de estado), escala tipográfica, y galería de componentes con sus estados.
2. **Las 5 pantallas** completas, **navegables** dentro del propio artifact (un nav o tabs internos),
   con **datos ficticios realistas en español de Chile** (nombres de unidades, documentos, fechas, etc.).
3. Demostración del **flujo de progreso** (animación o simulación del stepper + consola avanzando por las 5 etapas).
4. Un **toggle modo claro/oscuro** funcional.
5. Estados representativos: lista con datos y lista vacía; briefing con inconsistencias; cola offline pendiente;
   verificación de auditoría OK y rota.

---

## RESTRICCIONES TÉCNICAS DEL ARTIFACT

- **Un solo artifact React** autocontenido, sin llamadas de red ni dependencias externas no disponibles.
  Usa Tailwind para estilos y `lucide-react` para íconos. Datos mockeados en el propio archivo.
- Todo el texto de interfaz **en español**.
- Pensado para **escritorio** primero (es una herramienta de intranet), pero que no se rompa en pantallas chicas.
- Que el código sea **limpio y componentizado** (componentes reutilizables: `<Badge>`, `<StatusPill>`,
  `<DataTable>`, `<PipelineStepper>`, `<LogConsole>`, `<ClassificationBar>`, etc.), porque lo voy a portar a
  un proyecto React + TS + Vite real. Usa **design tokens** (variables CSS / constantes) en vez de valores mágicos repetidos.

---

## PROCESO QUE QUIERO QUE SIGAS

1. Primero, en texto, propón **2 direcciones visuales** distintas (mood + paleta + tipografía + principio rector),
   y **recomienda una** con una frase de por qué.
2. Luego define los **design tokens** y los **componentes base**.
3. Luego construye el **artifact** completo con todas las pantallas y la página de Design System.
4. Cierra con notas de **handoff para implementación** (mapa de componentes → dónde van, tokens, y decisiones
   de UX clave) para que yo lo reimplemente en el frontend real.

Hazlo lo mejor posible: pulcro, coherente, creíble para una demo ante una revisión técnica exigente del Ejército.
