import { useState } from "react";
import { formatCurrency } from "@octo-erp/shared";
import { useErp } from "../api/ErpApiProvider";
import { Button, Card, GridPaper, Label } from "../design-system";
import { ProductForm } from "./ProductForm";

export function CatalogPage() {
  const { products, variants, materials } = useErp();
  const [showForm, setShowForm] = useState(false);

  return (
    <section data-testid="catalog-page">
      <div className="page-header">
        <div>
          <Label parts={["Catálogo", "Figuras 3D"]} />
          <h2 className="text-display-lg">Catálogo de productos</h2>
        </div>
        <Button
          variant="primary"
          data-testid="toggle-new-product"
          onClick={() => setShowForm((v) => !v)}
        >
          {showForm ? "Cerrar" : "Nueva figura"}
        </Button>
      </div>

      {showForm && (
        <GridPaper className="section-block" data-testid="product-form-panel">
          <ProductForm materials={materials} />
        </GridPaper>
      )}

      <div className="card-grid" data-testid="product-list">
        {products.map((product) => {
          const productVariants = variants.filter((v) => v.productId === product.id);
          return (
            <Card
              key={product.id}
              label={[product.category]}
              title={product.name}
              data-testid={`product-card-${product.id}`}
              footer={`${productVariants.length} variante(s)`}
            >
              <p className="text-body-sm">{product.description}</p>
              <ul className="variant-list">
                {productVariants.map((variant) => {
                  const material = materials.find((m) => m.id === variant.materialId);
                  return (
                    <li key={variant.id} data-testid={`variant-row-${variant.id}`}>
                      <span>{variant.name}</span>
                      <span>{formatCurrency(variant.priceCents)}</span>
                      <span className="text-body-sm">
                        {variant.stockUnits} u. · {material?.name ?? "—"}
                      </span>
                    </li>
                  );
                })}
              </ul>
            </Card>
          );
        })}
      </div>
    </section>
  );
}
