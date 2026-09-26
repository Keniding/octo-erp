import { expect, test } from "@playwright/test";

test.describe("Agente conversacional", () => {
  test("responde con ayuda ante un mensaje que no reconoce", async ({ page }) => {
    await page.goto("/agente");
    await page.getByTestId("agent-input").fill("bailame un tango");
    await page.getByTestId("agent-send").click();

    const agentMessages = page.getByTestId("agent-message-agent");
    await expect(agentMessages.last()).toContainText("No entendí ese mensaje");
    await expect(agentMessages.last()).toContainText("catálogo");
  });

  test("el comando de catálogo devuelve una respuesta real del backend", async ({ page }) => {
    await page.goto("/agente");
    await page.getByTestId("agent-example-catálogo").click();

    const agentMessages = page.getByTestId("agent-message-agent");
    await expect(agentMessages.last()).toContainText("Catálogo actual");
    await expect(agentMessages.last()).toContainText("Samurai errante");
  });

  test("crear un pedido por chat descuenta stock real y consulta el stock actualizado", async ({ page }) => {
    await page.goto("/agente");

    await page.getByTestId("agent-input").fill("stock de SAM-10-RAW");
    await page.getByTestId("agent-send").click();
    const stockBeforeText = await page.getByTestId("agent-message-agent").last().innerText();
    const stockBefore = Number(stockBeforeText.match(/(\d+) unidades/)?.[1]);
    expect(Number.isFinite(stockBefore)).toBe(true);

    await page.getByTestId("agent-input").fill("pedido SAM-10-RAW x2 para Taller Origami (agente)");
    await page.getByTestId("agent-send").click();
    await expect(page.getByTestId("agent-message-agent").last()).toContainText("Pedido ORD-");
    await expect(page.getByTestId("agent-message-agent").last()).toContainText("Taller Origami (agente)");

    await page.getByTestId("agent-input").fill("stock de SAM-10-RAW");
    await page.getByTestId("agent-send").click();
    await expect(page.getByTestId("agent-message-agent").last()).toContainText(
      `${stockBefore - 2} unidades`,
    );
  });

  test("una acción del agente se refleja en tiempo real en otra pestaña, sin recargar", async ({ context }) => {
    const inventoryPage = await context.newPage();
    await inventoryPage.goto("/inventario");
    const variantId = "var-dragon-resina";
    const stockCell = inventoryPage.getByTestId(`variant-stock-value-${variantId}`);
    const before = Number(await stockCell.innerText());

    const agentPage = await context.newPage();
    await agentPage.goto("/agente");
    await agentPage.getByTestId("agent-input").fill("ajustar DRG-25-RES +3 recepcion");
    await agentPage.getByTestId("agent-send").click();
    await expect(agentPage.getByTestId("agent-message-agent").last()).toContainText("ajustado");

    // inventoryPage NUNCA navegó ni recargó — este assert solo puede pasar si el polling en
    // segundo plano de ErpApiProvider (POLL_INTERVAL_MS) trajo el cambio hecho por otra
    // pestaña. Timeout generoso (> POLL_INTERVAL_MS) para darle margen a un ciclo de poll.
    await expect(stockCell).toHaveText(String(before + 3), { timeout: 8_000 });

    await agentPage.close();
    await inventoryPage.close();
  });

  test("un ajuste que dejaría stock negativo se rechaza sin mutar nada", async ({ page }) => {
    await page.goto("/agente");
    await page.getByTestId("agent-input").fill("ajustar DRG-25-RES -9999");
    await page.getByTestId("agent-send").click();
    await expect(page.getByTestId("agent-message-agent").last()).toContainText("No pude ajustar el stock");
  });
});
