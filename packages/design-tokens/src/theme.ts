/**
 * Octo ERP — tokens resueltos en JS/TS para React Native (Expo).
 * Espejo de tokens.css; misma fuente: tokens.json. No inventes valores nuevos aquí.
 */
import tokens from "./tokens.json";

export type ThemeMode = "light" | "dark";

export const pigments = tokens.color.pigments;

export const themes = tokens.color.themes as Record<
  ThemeMode,
  {
    surface: string;
    surfaceRaised: string;
    ink: string;
    inkMuted: string;
    rule: string;
    gridLine: string;
    accent: string;
    onAccent: string;
    accentField: string;
    onAccentField: string;
    statusNote: string;
    statusValid: string;
    statusWarning: string;
    statusCritical: string;
    onStatus: string;
    focus: string;
  }
>;

export const fonts = {
  display: "EB Garamond",
  displayFallback: "serif",
  sans: "Hanken Grotesk",
  sansFallback: "sans-serif",
  mono: "JetBrains Mono",
  monoFallback: "monospace",
};

export const type = tokens.type.styles;

export const spacing = {
  space1: tokens.spacing.space1,
  space2: tokens.spacing.space2,
  space4: tokens.spacing.space4,
  spaceGrid: tokens.spacing.spaceGrid,
  space8: tokens.spacing.space8,
  space16: tokens.spacing.space16,
};

export const radius = tokens.radius;
export const border = tokens.border;

export function getTheme(mode: ThemeMode) {
  return themes[mode];
}

export default tokens;
