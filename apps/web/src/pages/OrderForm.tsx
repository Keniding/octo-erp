import { FormEvent, useState } from "react";
import { Product, ProductVariant } from "@octo-erp/shared";
import { useErp } from "../api/ErpApiProvider";
import { Button, Callout, Input, Select } from "../design-system";

interface ItemDraft {
  variantId: string;
  quantity: string;
}

interface OrderFormProps {
  variants: ProductVariant[];
  products: Product[];
  onCreated?: () => void;
}

export function OrderForm({ variants, products, onCreated }: OrderFormProps) {
  const { createOrder } = useErp();
  const [customerName, setCustomerName] = useState("");
  const [items, setItems] = useState<ItemDraft[]>([
    { variantId: variants[0]?.id ?? "", quantity: "1" },
  ]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function productName(productId: string) {
    return products.find((p) => p.id === productId)?.name ?? "—";
  }

  function updateItem(index: number, patch: Partial<ItemDraft>) {
    setItems((prev) => prev.map((it, i) => (i === index ? { ...it, ...patch } : it)));
  }

  function addItemRow() {
    setItems((prev) => [...prev, { variantId: variants[0]?.id ?? "", quantity: "1" }]);
  }

  function removeItemRow(index: number) {
    setItems((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    setSuccess(null);
    if (!customerName.trim()) {
      setError("El nombre del cliente es obligatorio.");
      return;
    }
    if (items.length === 0) {
      setError("Agregá al menos un artículo al pedido.");
      return;
    }
    try {
      const order = await createOrder({
        customerName: customerName.trim(),
        items: items.map((it) => ({
          variantId: it.variantId,
          quantity: Number(it.quantity || 0),
        })),
      });
      setSuccess(`Pedido ${order.code} creado.`);
      setCustomerName("");
      setItems([{ variantId: variants[0]?.id ?? "", quantity: "1" }]);
      onCreated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el pedido.");
    }
  }

  return (
    <form className="stack-form" onSubmit={handleSubmit} data-testid="order-form">
      {error && (
        <Callout tone="critical" data-testid="order-form-error">
          {error}
        </Callout>
      )}
      {success && (
        <Callout tone="valid" data-testid="order-form-success">
          {success}
        </Callout>
      )}
      <Input
        label="Cliente"
        value={customerName}
        onChange={(e) => setCustomerName(e.target.value)}
        data-testid="order-customer-input"
        required
      />

      <fieldset className="variant-fieldset">
        <legend className="text-label">Artículos</legend>
        {items.map((item, index) => {
          const variant = variants.find((v) => v.id === item.variantId);
          return (
            <div className="variant-row" key={index} data-testid={`order-item-row-${index}`}>
              <Select
                label="Variante"
                value={item.variantId}
                onChange={(e) => updateItem(index, { variantId: e.target.value })}
                data-testid={`order-item-variant-${index}`}
              >
                {variants.map((v) => (
                  <option key={v.id} value={v.id}>
                    {productName(v.productId)} — {v.name} ({v.stockUnits} disp.)
                  </option>
                ))}
              </Select>
              <Input
                label="Cantidad"
                type="number"
                min="1"
                value={item.quantity}
                onChange={(e) => updateItem(index, { quantity: e.target.value })}
                data-testid={`order-item-quantity-${index}`}
              />
              <span className="text-body-sm" data-testid={`order-item-available-${index}`}>
                Disponible: {variant?.stockUnits ?? 0}
              </span>
              {items.length > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => removeItemRow(index)}
                >
                  Quitar
                </Button>
              )}
            </div>
          );
        })}
        <Button type="button" variant="secondary" size="sm" onClick={addItemRow}>
          + Agregar artículo
        </Button>
      </fieldset>

      <div>
        <Button type="submit" variant="primary" data-testid="order-submit">
          Confirmar pedido
        </Button>
      </div>
    </form>
  );
}
