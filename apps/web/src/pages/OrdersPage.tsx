import { useState } from "react";
import { formatCurrency, formatDate } from "@octo-erp/shared";
import { useErp } from "../api/ErpApiProvider";
import { Button, Card, GridPaper, Label } from "../design-system";
import { OrderForm } from "./OrderForm";

const STATUS_TONE: Record<string, "note" | "valid" | "warning" | "critical"> = {
  borrador: "note",
  confirmado: "valid",
  en_produccion: "warning",
  enviado: "valid",
  cancelado: "critical",
};

export function OrdersPage() {
  const { orders, variants, products } = useErp();
  const [showForm, setShowForm] = useState(false);

  function variantLabel(variantId: string) {
    const variant = variants.find((v) => v.id === variantId);
    const product = products.find((p) => p.id === variant?.productId);
    return `${product?.name ?? "—"} — ${variant?.name ?? "—"}`;
  }

  return (
    <section data-testid="orders-page">
      <div className="page-header">
        <div>
          <Label parts={["Ventas", "Pedidos"]} />
          <h2 className="text-display-lg">Pedidos</h2>
        </div>
        <Button variant="primary" data-testid="toggle-new-order" onClick={() => setShowForm((v) => !v)}>
          {showForm ? "Cerrar" : "Nuevo pedido"}
        </Button>
      </div>

      {showForm && (
        <GridPaper className="section-block" data-testid="order-form-panel">
          <OrderForm variants={variants} products={products} />
        </GridPaper>
      )}

      <div className="card-grid" data-testid="order-list">
        {orders.map((order) => (
          <Card
            key={order.id}
            label={[order.status.replace("_", " ")]}
            title={order.code}
            data-testid={`order-card-${order.id}`}
            footer={formatDate(order.createdAt)}
          >
            <p className="text-body-sm">Cliente: {order.customerName}</p>
            <ul className="variant-list">
              {order.items.map((item, i) => (
                <li key={i}>
                  <span>{variantLabel(item.variantId)}</span>
                  <span>
                    {item.quantity} × {formatCurrency(item.unitPriceCents)}
                  </span>
                </li>
              ))}
            </ul>
            <p className="text-body" data-testid={`order-total-${order.id}`}>
              Total: {formatCurrency(order.totalCents)}
            </p>
          </Card>
        ))}
      </div>
    </section>
  );
}
