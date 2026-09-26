import { Route, Routes } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { CatalogPage } from "./pages/CatalogPage";
import { InventoryPage } from "./pages/InventoryPage";
import { OrdersPage } from "./pages/OrdersPage";
import { useErp } from "./api/ErpApiProvider";

export function App() {
  const { loading, loadError } = useErp();

  if (loading) {
    return <p data-testid="app-loading">Cargando datos del servidor…</p>;
  }
  if (loadError) {
    return <p data-testid="app-load-error">No se pudo conectar con la API: {loadError}</p>;
  }

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
