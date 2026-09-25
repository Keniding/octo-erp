import { Route, Routes } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { CatalogPage } from "./pages/CatalogPage";
import { InventoryPage } from "./pages/InventoryPage";
import { OrdersPage } from "./pages/OrdersPage";

export function App() {
  return (
    <Routes>
      <Route element={<AppShell />}>
        <Route index element={<CatalogPage />} />
        <Route path="inventario" element={<InventoryPage />} />
        <Route path="pedidos" element={<OrdersPage />} />
      </Route>
    </Routes>
  );
}
