# Design system — cómo se usó

Fuente: design system del workspace *"Humanismo Editorial"*
(artifact `9c5d30b9-c801-460f-b187-5117b6a00f8f`, leído antes de escribir
cualquier código de UI). Es un sistema editorial impreso — papel sin
blanquear, tinta, semitonos, sin sombras ni esquinas redondeadas — pensado
originalmente para artifacts/documentos. Este proyecto lo traduce a una
interfaz de aplicación (ERP) real, con las adaptaciones que eso exige, pero
**sin introducir ningún valor de color, tipografía o espaciado que no
estuviera ya en `tokens.json`**.

## Dónde vive

`packages/design-tokens/src/tokens.json` es la copia de trabajo de los
tokens (colores semánticos de los temas Papel/Tinta, familias tipográficas,
espaciado, radios, bordes). De ahí se derivan:

- `tokens.css` — variables CSS (`--surface`, `--ink`, `--accent`, etc.) que
  consume `apps/web` directamente.
- `theme.ts` — el mismo contenido como objeto TypeScript, consumido por
  `apps/mobile` a través de `ThemeContext` (React Native no tiene variables
  CSS).

Si el design system cambia, **el único lugar que se edita es
`packages/design-tokens/src/tokens.json`** (y su reflejo en `tokens.css` /
`theme.ts`); ninguna app debe tener colores o tamaños hardcodeados.

## Qué se implementó de los 9 componentes del design system

| Componente  | Web (`apps/web/src/design-system`) | Mobile (`apps/mobile/src/design-system`) |
|---|---|---|
| `Button`    | ✅ `Button.tsx` — variantes `primary`/`secondary`/`ghost`, `radius-sm`, sin sombra | ✅ `Button.tsx` — mismo comportamiento con `Pressable` |
| `Card`      | ✅ | ✅ |
| `Label`     | ✅ — mayúsculas + separador `//` | ✅ |
| `Callout`   | ✅ — 4 tonos (`note`/`valid`/`warning`/`critical`), siempre con palabra de estado | ✅ |
| `GridPaper` | ✅ — fondo de papel milimetrado + cruces de registro, usado como contenedor de los formularios "nuevo" | ⚠️ simplificado (ver más abajo) |
| `Lamina`    | ✅ — reinterpretado como cabecera de la app (panel terracota + panel verde agua) | ✅ — mismo motivo en el header |
| `NodeGraph` | ❌ no aplica: es un motivo ilustrativo de portada, no hay superficie de "portada" en un ERP operativo | ❌ |
| `CodeBlock` | ❌ no aplica: no hay bloques de código en la interfaz de un ERP | ❌ |
| `ContextMeter` | ❌ es específico de medir ventana de contexto de un LLM, no tiene equivalente de negocio aquí | ❌ |

`Input` y `Select` **no** están en el design system original (que no define
formularios), pero se construyeron siguiendo su misma gramática visual:
`label` en mayúsculas tipo etiqueta, borde `border-hairline` en `rule`,
esquinas `radius-sm`, foco con anillo sólido de `focus` — nunca un estilo
nuevo por fuera de los tokens existentes.

### GridPaper en mobile

En React Native no hay `background-image` con gradientes lineales para
dibujar la cuadrícula de 19px, así que la versión móvil no reproduce el
patrón de rejilla (requeriría SVG o Canvas). Se mantiene el resto de la
especificación (superficie `surfaceRaised`, sin sombra, esquinas rectas).
Es la única omisión visual entre ambas plataformas; está documentada aquí
para no perderla de vista si se decide invertir en una versión con
`react-native-svg`.

## Tipografía

Se cargan las tres familias reales del sistema vía Google Fonts en
`apps/web/index.html` (EB Garamond para display/headings, Hanken Grotesk
para interfaz/cuerpo, JetBrains Mono para código/diagramas — aunque esta
última no se usa activamente en el ERP). En mobile se referencian los
mismos nombres de familia en `theme.ts`; si se agregan como fuentes nativas
con `expo-font`, no hace falta tocar el resto del código porque los
componentes ya leen `fonts.display` / `fonts.sans` desde el tema.

## Regla operativa

Ver `CLAUDE.md` en la raíz del repo: **toda nueva interfaz reutiliza los
tokens y componentes existentes**; no se agregan colores, tamaños de fuente
o espaciados "a mano". Si un caso de uso necesita algo que el design system
no cubre, se extiende `tokens.json` explícitamente (como se hizo con
`Input`/`Select`, siempre componiendo con tokens ya existentes) en vez de
escribir un valor suelto en un componente.
