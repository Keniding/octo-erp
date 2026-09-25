import { ReactNode } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { useTheme } from "../theme/ThemeContext";
import { Label } from "../design-system";

export type Screen = "catalogo" | "inventario" | "pedidos";

const TABS: { key: Screen; title: string }[] = [
  { key: "catalogo", title: "Catálogo" },
  { key: "inventario", title: "Inventario" },
  { key: "pedidos", title: "Pedidos" },
];

interface AppShellProps {
  active: Screen;
  onChange: (screen: Screen) => void;
  children: ReactNode;
}

export function AppShell({ active, onChange, children }: AppShellProps) {
  const { colors, spacing } = useTheme();

  return (
    <SafeAreaView style={{ flex: 1, backgroundColor: colors.surface }} edges={["top", "left", "right"]}>
      <View style={[styles.header, { backgroundColor: colors.accentField, padding: spacing.space4 }]}>
        <Label parts={["Octo ERP"]} tone="ink" />
        <Text style={[styles.brandTitle, { color: colors.onAccentField }]}>Figuras 3D</Text>
      </View>
      <View style={{ flex: 1 }}>{children}</View>
      <View style={[styles.tabBar, { borderTopColor: colors.rule, backgroundColor: colors.surfaceRaised }]}>
        {TABS.map((tab) => {
          const isActive = tab.key === active;
          return (
            <Pressable
              key={tab.key}
              testID={`tab-${tab.key}`}
              style={styles.tabItem}
              onPress={() => onChange(tab.key)}
            >
              <Text
                style={{
                  color: isActive ? colors.accent : colors.inkMuted,
                  fontWeight: isActive ? "700" : "500",
                  fontSize: 14,
                }}
              >
                {tab.title}
              </Text>
            </Pressable>
          );
        })}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  header: {
    gap: 4,
  },
  brandTitle: {
    fontSize: 24,
    fontWeight: "500",
  },
  tabBar: {
    flexDirection: "row",
    borderTopWidth: 1,
  },
  tabItem: {
    flex: 1,
    alignItems: "center",
    paddingVertical: 12,
  },
});
