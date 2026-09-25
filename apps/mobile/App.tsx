import { useState } from "react";
import { StatusBar } from "expo-status-bar";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { ThemeProvider } from "./src/theme/ThemeContext";
import { AppShell, Screen } from "./src/navigation/AppShell";
import { CatalogScreen } from "./src/screens/CatalogScreen";
import { InventoryScreen } from "./src/screens/InventoryScreen";
import { OrdersScreen } from "./src/screens/OrdersScreen";

export default function App() {
  const [screen, setScreen] = useState<Screen>("catalogo");

  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <AppShell active={screen} onChange={setScreen}>
          {screen === "catalogo" && <CatalogScreen />}
          {screen === "inventario" && <InventoryScreen />}
          {screen === "pedidos" && <OrdersScreen />}
        </AppShell>
        <StatusBar style="auto" />
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
