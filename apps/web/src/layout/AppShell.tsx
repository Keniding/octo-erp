import { NavLink, Outlet } from "react-router-dom";
import { Label } from "../design-system";
import "./app-shell.css";

const NAV_ITEMS = [
  { to: "/", label: "Catálogo", testId: "nav-catalogo" },
  { to: "/inventario", label: "Inventario", testId: "nav-inventario" },
  { to: "/pedidos", label: "Pedidos", testId: "nav-pedidos" },
  { to: "/agente", label: "Agente", testId: "nav-agente" },
];

export function AppShell() {
  return (
    <div className="app-shell">
      <header className="app-shell__header">
        <div className="app-shell__brand-panel">
          <Label parts={["Octo ERP"]} tone="ink" />
          <h1 className="text-display-lg app-shell__brand-title">
            Figuras <em>impresas en 3D</em>
          </h1>
        </div>
        <nav className="app-shell__nav-panel" aria-label="Navegación principal">
          <Label parts={["Módulos"]} tone="muted" />
          <ul className="app-shell__nav-list">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.to === "/"}
                  data-testid={item.testId}
                  className={({ isActive }) =>
                    "app-shell__nav-link" + (isActive ? " app-shell__nav-link--active" : "")
                  }
                >
                  {item.label}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>
      <main className="app-shell__main">
        <Outlet />
      </main>
    </div>
  );
}
