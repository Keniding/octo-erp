import { StyleSheet, Text, TextInput, TextInputProps, View } from "react-native";
import { useTheme } from "../theme/ThemeContext";

interface InputProps extends TextInputProps {
  label: string;
  hint?: string;
}

export function Input({ label, hint, style, testID, ...rest }: InputProps) {
  const { colors, spacing, radius } = useTheme();
  return (
    <View style={{ gap: spacing.space1 }}>
      <Text style={[styles.label, { color: colors.inkMuted }]}>{label.toUpperCase()}</Text>
      <TextInput
        testID={testID}
        placeholderTextColor={colors.inkMuted}
        style={[
          styles.control,
          {
            borderColor: colors.rule,
            borderRadius: radius.sm,
            backgroundColor: colors.surface,
            color: colors.ink,
            padding: spacing.space2,
          },
          style,
        ]}
        {...rest}
      />
      {hint && <Text style={{ color: colors.inkMuted, fontSize: 14 }}>{hint}</Text>}
    </View>
  );
}

const styles = StyleSheet.create({
  label: {
    fontSize: 12,
    fontWeight: "600",
    letterSpacing: 1,
  },
  control: {
    borderWidth: 1,
    fontSize: 16,
  },
});
