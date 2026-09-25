import { ReactNode } from "react";
import { GestureResponderEvent, Pressable, StyleSheet, Text } from "react-native";
import { useTheme } from "../theme/ThemeContext";

type Variant = "primary" | "secondary" | "ghost";
type Size = "md" | "sm";

interface ButtonProps {
  children: ReactNode;
  onPress?: (event: GestureResponderEvent) => void;
  variant?: Variant;
  size?: Size;
  disabled?: boolean;
  testID?: string;
}

export function Button({
  children,
  onPress,
  variant = "secondary",
  size = "md",
  disabled,
  testID,
}: ButtonProps) {
  const { colors, radius, spacing } = useTheme();

  const background =
    variant === "primary" ? colors.accent : variant === "ghost" ? "transparent" : "transparent";
  const borderColor = variant === "ghost" ? "transparent" : variant === "primary" ? colors.accent : colors.ink;
  const textColor = variant === "primary" ? colors.onAccent : variant === "ghost" ? colors.accent : colors.ink;

  return (
    <Pressable
      testID={testID}
      onPress={onPress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.base,
        {
          backgroundColor: pressed && variant !== "ghost" ? colors.ink : background,
          borderColor,
          borderWidth: variant === "ghost" ? 0 : 1,
          borderRadius: radius.sm,
          paddingVertical: size === "sm" ? spacing.space1 : spacing.space2,
          paddingHorizontal: size === "sm" ? spacing.space2 : spacing.space4,
          opacity: disabled ? 0.5 : 1,
        },
      ]}
    >
      {({ pressed }) => (
        <Text
          style={[
            styles.text,
            {
              color: pressed && variant !== "ghost" ? colors.surface : textColor,
              fontSize: size === "sm" ? 14 : 16,
              textDecorationLine: variant === "ghost" ? "underline" : "none",
            },
          ]}
        >
          {children}
        </Text>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    alignItems: "center",
    justifyContent: "center",
    alignSelf: "flex-start",
  },
  text: {
    fontWeight: "600",
  },
});
