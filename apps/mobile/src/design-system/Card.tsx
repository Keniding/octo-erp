import { ReactNode } from "react";
import { StyleSheet, Text, View } from "react-native";
import { useTheme } from "../theme/ThemeContext";
import { Label } from "./Label";

interface CardProps {
  label?: string | string[];
  title?: string;
  children?: ReactNode;
  footer?: ReactNode;
  testID?: string;
}

export function Card({ label, title, children, footer, testID }: CardProps) {
  const { colors, spacing } = useTheme();
  const parts = Array.isArray(label) ? label : label ? [label] : undefined;
  return (
    <View
      testID={testID}
      style={[
        styles.card,
        {
          backgroundColor: colors.surfaceRaised,
          borderColor: colors.rule,
          padding: spacing.space4,
          gap: spacing.space2,
        },
      ]}
    >
      {parts && <Label parts={parts} />}
      {title && <Text style={[styles.title, { color: colors.ink }]}>{title}</Text>}
      {children}
      {footer && (
        <View style={[styles.footer, { borderTopColor: colors.rule, paddingTop: spacing.space2 }]}>
          {typeof footer === "string" ? (
            <Text style={{ color: colors.inkMuted, fontSize: 14 }}>{footer}</Text>
          ) : (
            footer
          )}
        </View>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    borderWidth: 1,
    borderRadius: 0,
  },
  title: {
    fontSize: 22,
    fontWeight: "500",
  },
  footer: {
    borderTopWidth: 1,
  },
});
