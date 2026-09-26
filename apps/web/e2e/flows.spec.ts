import { expect, test } from "@playwright/test";

test.describe("Alta de producto", () => {
  test("crea una figura nueva con una variante desde el catálogo", async ({ page }) => {
    await page.goto("/");
    await page.getByTestId("toggle-new-product").click();
    await expect(page.getByTestId("product-form")).toBeVisible();

    const productName = "Golem de raíz";
    await page.getByTestId("product-name-input").fill(productName);
    await page.getByTestId("product-description-input").fill(
      "Golem tallado con motivos botánicos, edición limitada.",
    );
    await page.getByTestId("variant-name-0").fill("15cm — sin pintar");
    await page.getByTestId("variant-sku-0").fill("GOL-15-RAW");
    await page.getByTestId("variant-price-0").fill("32.50");
    await page.getByTestId("variant-weight-0").fill("140");
    await page.getByTestId("variant-stock-0").fill("6");

    await page.getByTestId("product-submit").click();

    await expect(page.getByTestId("product-form-success")).toBeVisible();
    await expect(page.getByTestId("product-list")).toContainText(productName);
    await expect(page.getByTestId("product-list")).toContainText("15cm — sin pintar");
  });
});

test.describe("Ajuste de inventario", () => {
  test("aumenta el stock de una variante existente", async ({ page }) => {
    await page.goto("/inventario");

    const variantId = "var-samurai-10-sin-pintar";
    const stockCell = page.getByTestId(`variant-stock-value-${variantId}`);
    const before = Number(await stockCell.innerText());

    await page.getByTestId("variant-stock-select").selectOption(variantId);
    await page.getByTestId("variant-stock-delta").fill("5");
    await page.getByTestId("variant-stock-note").fill("Reposición de taller");
    await page.getByTestId("variant-stock-submit").click();

    await expect(page.getByTestId("inventory-success")).toBeVisible();
    await expect(stockCell).toHaveText(String(before + 5));
  });

  test("rechaza un ajuste que dejaría stock negativo", async ({ page }) => {
    await page.goto("/inventario");
    const variantId = "var-dragon-resina"; // seed stock: 2

    await page.getByTestId("variant-stock-select").selectOption(variantId);
    await page.getByTestId("variant-stock-delta").fill("-10");
    await page.getByTestId("variant-stock-submit").click();

    await expect(page.getByTestId("inventory-error")).toBeVisible();
    await expect(page.getByTestId(`variant-stock-value-${variantId}`)).toHaveText("2");
  });
});

test.describe("Creación de pedido", () => {
  test("crea un pedido y descuenta stock de la variante vendida", async ({ page }) => {
    const variantId = "var-samurai-10-sin-pintar"; // primera opción del selector

    // El backend ahora tiene estado real de servidor (no un store por-pestaña que se
    // resetea): se lee el stock actual en vez de asumir el valor semilla, porque otro test
    // de este mismo archivo (ajuste de inventario) puede haber corrido antes y mutado esta
    // misma variante contra el mismo proceso.
    await page.goto("/inventario");
    const stockCell = page.getByTestId(`variant-stock-value-${variantId}`);
    const before = Number(await stockCell.innerText());

    await page.goto("/pedidos");
    await page.getByTestId("toggle-new-order").click();
    await expect(page.getByTestId("order-form")).toBeVisible();

    await page.getByTestId("order-customer-input").fill("Taller Origami");
    await page.getByTestId("order-item-variant-0").selectOption(variantId);
    await page.getByTestId("order-item-quantity-0").fill("2");

    await page.getByTestId("order-submit").click();

    await expect(page.getByTestId("order-form-success")).toBeVisible();
    await expect(page.getByTestId("order-list")).toContainText("Taller Origami");

    await page.getByTestId("nav-inventario").click();
    await expect(page.getByTestId(`variant-stock-value-${variantId}`)).toHaveText(String(before - 2));
  });

  test("no permite pedir más unidades que el stock disponible", async ({ page }) => {
    await page.goto("/pedidos");
    const variantId = "var-dragon-resina"; // seed stock: 2

    await page.getByTestId("toggle-new-order").click();
    await page.getByTestId("order-customer-input").fill("Cliente sin stock");
    await page.getByTestId("order-item-variant-0").selectOption(variantId);
    await page.getByTestId("order-item-quantity-0").fill("99");
    await page.getByTestId("order-submit").click();

    await expect(page.getByTestId("order-form-error")).toBeVisible();
  });
});
