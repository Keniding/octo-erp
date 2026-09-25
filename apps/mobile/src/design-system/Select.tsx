import { useState } from "react";
import { FlatList, Modal, Pressable, StyleSheet, Text, View } from "react-native";
import { useTheme } from "../theme/ThemeContext";

export interface SelectOption {
  value: string;
  label: string;
}

interface SelectProps {
  label: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  testID?: string;
}

export function Select({ label, value, options, onChange, testID }: SelectProps) {
  const { colors, spacing, radius } = useTheme();
  const [open, setOpen] = useState(false);
  const selected = options.find((o) => o.value === value);

  return (
    <View style={{ gap: spacing.space1 }}>
      <Text style={[styles.label, { color: colors.inkMuted }]}>{label.toUpperCase()}</Text>
      <Pressable
        testID={testID}
        onPress={() => setOpen(true)}
        style={[
          styles.control,
          {
            borderColor: colors.rule,
            borderRadius: radius.sm,
            backgroundColor: colors.surface,
            padding: spacing.space2,
          },
        ]}
      >
        <Text style={{ color: colors.ink }} numberOfLines={1}>
          {selected?.label ?? "Seleccionar…"}
        </Text>
      </Pressable>
      <Modal visible={open} transparent animationType="fade" onRequestClose={() => setOpen(false)}>
        <Pressable style={styles.backdrop} onPress={() => setOpen(false)}>
          <View style={[styles.sheet, { backgroundColor: colors.surfaceRaised, borderColor: colors.rule }]}>
            <FlatList
              data={options}
              keyExtractor={(item) => item.value}
              renderItem={({ item }) => (
                <Pressable
                  testID={testID ? `${testID}-option-${item.value}` : undefined}
                  style={[styles.option, { borderBottomColor: colors.rule }]}
                  onPress={() => {
                    onChange(item.value);
                    setOpen(false);
                  }}
                >
                  <Text style={{ color: colors.ink }}>{item.label}</Text>
                </Pressable>
              )}
            />
          </View>
        </Pressable>
      </Modal>
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
    minHeight: 44,
    justifyContent: "center",
  },
  backdrop: {
    flex: 1,
    backgroundColor: "rgba(25,25,25,0.4)",
    justifyContent: "flex-end",
  },
  sheet: {
    maxHeight: "60%",
    borderTopWidth: 1,
    padding: 8,
  },
  option: {
    paddingVertical: 12,
    paddingHorizontal: 8,
    borderBottomWidth: 1,
  },
});
