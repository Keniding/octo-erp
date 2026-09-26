import { FormEvent, useState } from "react";
import { useErp } from "../api/ErpApiProvider";
import { Button, Callout, Card, Input, Label, Select } from "../design-system";

export function InventoryPage() {
  const { variants, materials, products, adjustVariantStock, adjustMaterialStock } = useErp();

  const [variantId, setVariantId] = useState(variants[0]?.id ?? "");
  const [delta, setDelta] = useState("1");
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [materialId, setMaterialId] = useState(materials[0]?.id ?? "");
  const [materialDelta, setMaterialDelta] = useState("100");

  function productName(productId: string) {
    return products.find((p) => p.id === productId)?.name ?? "—";
  }

  async function handleAdjustVariant(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    const amount = Number(delta);
    if (!variantId || !amount) {
      setError("Elegí una variante y una cantidad distinta de cero.");
      return;
    }
    try {
      await adjustVariantStock(variantId, amount, "ajuste-manual", note || undefined);
      setSuccess("Stock actualizado.");
      setNote("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo ajustar el stock.");
    }
  }

  async function handleAdjustMaterial(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    const amount = Number(materialDelta);
    if (!materialId || !amount) {
      setError("Elegí un material y una cantidad distinta de cero.");
      return;
    }
    try {
      await adjustMaterialStock(materialId, amount, "recepcion");
      setSuccess("Filamento actualizado.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo ajustar el material.");
    }
  }

  const lowStockVariants = variants.filter((v) => v.stockUnits <= v.reorderThreshold);

  return (
    <section data-testid="inventory-page">
      <div className="page-header">
        <div>
          <Label parts={["Inventario", "Stock y filamento"]} />
          <h2 className="text-display-lg">Inventario</h2>
        </div>
      </div>

      {error && (
        <Callout tone="critical" data-testid="inventory-error">
          {error}
        </Callout>
      )}
      {success && (
        <Callout tone="valid" data-testid="inventory-success">
          {success}
        </Callout>
      )}
      {lowStockVariants.length > 0 && (
        <Callout tone="warning" data-testid="inventory-low-stock">
          {lowStockVariants.length} variante(s) por debajo del umbral de reposición.
        </Callout>
      )}

      <div className="two-col">
        <Card label={["Variantes", "Ajuste de stock"]} title="Ajustar stock de variante">
          <form className="stack-form" onSubmit={handleAdjustVariant} data-testid="variant-stock-form">
            <Select
              label="Variante"
              value={variantId}
              onChange={(e) => setVariantId(e.target.value)}
              data-testid="variant-stock-select"
            >
              {variants.map((v) => (
                <option key={v.id} value={v.id}>
                  {productName(v.productId)} — {v.name} ({v.stockUnits} u.)
                </option>
              ))}
            </Select>
            <Input
              label="Cantidad (+ ingreso / - salida)"
              type="number"
              value={delta}
              onChange={(e) => setDelta(e.target.value)}
              data-testid="variant-stock-delta"
            />
            <Input
              label="Nota"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              data-testid="variant-stock-note"
            />
            <div>
              <Button type="submit" variant="primary" data-testid="variant-stock-submit">
                Aplicar ajuste
              </Button>
            </div>
          </form>
        </Card>

        <Card label={["Materiales", "Filamento"]} title="Reponer filamento">
          <form className="stack-form" onSubmit={handleAdjustMaterial} data-testid="material-stock-form">
            <Select
              label="Material"
              value={materialId}
              onChange={(e) => setMaterialId(e.target.value)}
              data-testid="material-stock-select"
            >
              {materials.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name} ({m.stockGrams} g)
                </option>
              ))}
            </Select>
            <Input
              label="Gramos (+ ingreso / - consumo)"
              type="number"
              value={materialDelta}
              onChange={(e) => setMaterialDelta(e.target.value)}
              data-testid="material-stock-delta"
            />
            <div>
              <Button type="submit" variant="secondary" data-testid="material-stock-submit">
                Aplicar ajuste
              </Button>
            </div>
          </form>
        </Card>
      </div>

      <Card label={["Detalle"]} title="Stock por variante" className="section-block">
        <table className="ds-table" data-testid="variant-stock-table">
          <thead>
            <tr>
              <th>Figura</th>
              <th>Variante</th>
              <th>SKU</th>
              <th>Stock</th>
              <th>Umbral</th>
            </tr>
          </thead>
          <tbody>
            {variants.map((v) => (
              <tr key={v.id} data-testid={`variant-stock-row-${v.id}`}>
                <td>{productName(v.productId)}</td>
                <td>{v.name}</td>
                <td>{v.sku}</td>
                <td data-testid={`variant-stock-value-${v.id}`}>{v.stockUnits}</td>
                <td>{v.reorderThreshold}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>

      <Card label={["Detalle"]} title="Stock de materiales" className="section-block">
        <table className="ds-table" data-testid="material-stock-table">
          <thead>
            <tr>
              <th>Material</th>
              <th>Tipo</th>
              <th>Stock (g)</th>
              <th>Umbral (g)</th>
            </tr>
          </thead>
          <tbody>
            {materials.map((m) => (
              <tr key={m.id}>
                <td>{m.name}</td>
                <td>{m.type}</td>
                <td>{m.stockGrams}</td>
                <td>{m.reorderThresholdGrams}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </section>
  );
}
