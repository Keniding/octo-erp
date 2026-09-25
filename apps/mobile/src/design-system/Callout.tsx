import { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useTheme } from "../theme/ThemeContext";

type Tone = "note" | "valid" | "warning" | "critical";

const defaultWord: Record<Tone, string> = {
  note: "Nota",
  valid: "Validación",
  warning: "Advertencia",
  critical: "Crítico",
};

interface CalloutProps {
  tone: Tone;
  title?: string;
  children: ReactNode;
  word?: string;
  testID?: string;
}

export function Callout({ tone, title, children, word, testID }: CalloutProps) {
  const { colors, spacing } = useTheme();
  const backgroundMap: Record<Tone, string> = {
    note: colors.statusNote,
    valid: colors.statusValid,
    warning: colors.statusWarning,
    critical: colors.statusCritical,
  };
  const textColor = tone === "critical" ? colors.onAccent : colors.onStatus;

  return (
    <View
      testID={testID}
      style={[styles.callout, { backgroundColor: backgroundMap[tone], padding: spacing.space4, gap: spacing.space1 }]}
    >
      <Text style={[styles.word, { color: textColor }]}>{word ?? defaultWord[tone]}</Text>
      {title && <Text style={[styles.title, { color: textColor }]}>{title}</Text>}
      <Text style={{ color: textColor, fontSize: 16, lineHeight: 22 }}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  callout: {
    borderRadius: 0,
  },
  word: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1,
  },
  title: {
    fontSize: 18,
    fontWeight: "600",
  },
});
