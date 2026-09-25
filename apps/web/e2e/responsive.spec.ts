import path from "node:path";
import { fileURLToPath } from "node:url";
import { test } from "@playwright/test";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const SCREENSHOT_DIR = path.resolve(__dirname, "../../../docs/screenshots");

const BREAKPOINTS = [
  { name: "mobile", width: 390, height: 844 },
  { name: "tablet", width: 768, height: 1024 },
  { name: "desktop", width: 1440, height: 900 },
];

const PAGES = [
  { name: "catalogo", path: "/" },
  { name: "inventario", path: "/inventario" },
  { name: "pedidos", path: "/pedidos" },
];

for (const breakpoint of BREAKPOINTS) {
  for (const targetPage of PAGES) {
    test(`captura ${targetPage.name} en ${breakpoint.name} (${breakpoint.width}px)`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: breakpoint.width, height: breakpoint.height });
      await page.goto(targetPage.path);
      await page.waitForLoadState("networkidle");
      const fileName = `${targetPage.name}-${breakpoint.name}-${breakpoint.width}px.png`;
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, fileName),
        fullPage: true,
      });
    });
  }
}

// Los formularios "nuevo" (multi-variante / multi-artículo) son el layout
// más denso de la app: se capturan por separado con el panel abierto para
// vigilar que la grilla de campos y los botones no se rompan en ningún
// breakpoint (ver docs/decisions/003-formularios-responsive.md).
const FORMS = [
  { name: "catalogo-formulario", path: "/", toggleTestId: "toggle-new-product" },
  { name: "pedidos-formulario", path: "/pedidos", toggleTestId: "toggle-new-order" },
];

for (const breakpoint of BREAKPOINTS) {
  for (const form of FORMS) {
    test(`captura ${form.name} en ${breakpoint.name} (${breakpoint.width}px)`, async ({
      page,
    }) => {
      await page.setViewportSize({ width: breakpoint.width, height: breakpoint.height });
      await page.goto(form.path);
      await page.getByTestId(form.toggleTestId).click();
      await page.waitForLoadState("networkidle");
      const fileName = `${form.name}-${breakpoint.name}-${breakpoint.width}px.png`;
      await page.screenshot({
        path: path.join(SCREENSHOT_DIR, fileName),
        fullPage: true,
      });
    });
  }
}
