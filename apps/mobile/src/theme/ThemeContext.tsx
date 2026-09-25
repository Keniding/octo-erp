import { createContext, ReactNode, useContext, useMemo } from "react";
import { useColorScheme } from "react-native";
import { fonts, getTheme, radius, spacing, ThemeMode, type as typeStyles } from "@octo-erp/design-tokens/src/theme";

interface ThemeContextValue {
  mode: ThemeMode;
  colors: ReturnType<typeof getTheme>;
  spacing: typeof spacing;
  radius: typeof radius;
  fonts: typeof fonts;
  type: typeof typeStyles;
}

const ThemeContext = createContext<ThemeContextValue | null>(null);

export function ThemeProvider({ children }: { children: ReactNode }) {
  const scheme = useColorScheme();
  const mode: ThemeMode = scheme === "dark" ? "dark" : "light";
  const value = useMemo<ThemeContextValue>(
    () => ({
      mode,
      colors: getTheme(mode),
      spacing,
      radius,
      fonts,
      type: typeStyles,
    }),
    [mode],
  );
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export function useTheme() {
  const ctx = useContext(ThemeContext);
  if (!ctx) throw new Error("useTheme debe usarse dentro de ThemeProvider");
  return ctx;
}
