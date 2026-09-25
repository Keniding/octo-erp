import { StyleSheet, Text } from "react-native";
import { useTheme } from "../theme/ThemeContext";

type Tone = "muted" | "ink" | "accent";

interface LabelProps {
  parts?: string[];
  children?: string;
  tone?: Tone;
}

export function Label({ parts, children, tone = "muted" }: LabelProps) {
  const { colors } = useTheme();
  const segments = parts ?? (children ? [children] : []);
  const color = tone === "ink" ? colors.ink : tone === "accent" ? colors.accent : colors.inkMuted;
  return (
    <Text style={[styles.label, { color }]}>
      {segments.map((s) => s.toUpperCase()).join(" // ")}
    </Text>
  );
}

const styles = StyleSheet.create({
  label: {
    fontSize: 12,
    lineHeight: 16,
    fontWeight: "600",
    letterSpacing: 1,
    fontFamily: undefined,
  },
});
