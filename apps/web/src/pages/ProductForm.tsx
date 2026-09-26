import { FormEvent, useState } from "react";
import { Material, ProductCategory } from "@octo-erp/shared";
import { useErp } from "../api/ErpApiProvider";
import { Button, Input, Select, Callout } from "../design-system";

const CATEGORIES: ProductCategory[] = [
  "Anime",
  "Videojuegos",
  "Fantasia",
  "Miniaturas TTRPG",
  "Personalizado",
];

interface VariantDraft {
  name: string;
  sku: string;
  price: string;
  materialId: string;
  weight: string;
  stock: string;
  threshold: string;
}

function emptyVariant(materialId: string): VariantDraft {
  return { name: "", sku: "", price: "", materialId, weight: "", stock: "0", threshold: "3" };
}

interface ProductFormProps {
  materials: Material[];
  onCreated?: () => void;
}

export function ProductForm({ materials, onCreated }: ProductFormProps) {
  const { addProduct } = useErp();
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<ProductCategory>(CATEGORIES[0]);
  const [variants, setVariants] = useState<VariantDraft[]>([
    emptyVariant(materials[0]?.id ?? ""),
  ]);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  function updateVariant(index: number, patch: Partial<VariantDraft>) {
    setVariants((prev) => prev.map((v, i) => (i === index ? { ...v, ...patch } : v)));
  }

  function addVariantRow() {
    setVariants((prev) => [...prev, emptyVariant(materials[0]?.id ?? "")]);
  }

  function removeVariantRow(index: number) {
    setVariants((prev) => prev.filter((_, i) => i !== index));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    setError(null);
    if (!name.trim()) {
      setError("El nombre de la figura es obligatorio.");
      return;
    }
    if (variants.length === 0) {
      setError("Agregá al menos una variante.");
      return;
    }
    for (const v of variants) {
      if (!v.name.trim() || !v.sku.trim() || !v.materialId) {
        setError("Completá nombre, SKU y material en cada variante.");
        return;
      }
    }
    try {
      await addProduct({
        name: name.trim(),
        description: description.trim(),
        category,
        variants: variants.map((v) => ({
          name: v.name.trim(),
          sku: v.sku.trim(),
          priceCents: Math.round(Number(v.price || 0) * 100),
          materialId: v.materialId,
          weightGrams: Number(v.weight || 0),
          stockUnits: Number(v.stock || 0),
          reorderThreshold: Number(v.threshold || 0),
        })),
      });
      setSuccess(true);
      setName("");
      setDescription("");
      setVariants([emptyVariant(materials[0]?.id ?? "")]);
      onCreated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la figura.");
    }
  }

  return (
    <form className="stack-form" onSubmit={handleSubmit} data-testid="product-form">
      {error && (
        <Callout tone="critical" data-testid="product-form-error">
          {error}
        </Callout>
      )}
      {success && (
        <Callout tone="valid" data-testid="product-form-success">
          Figura creada correctamente.
        </Callout>
      )}
      <div className="form-row">
        <Input
          label="Nombre de la figura"
          value={name}
          onChange={(e) => setName(e.target.value)}
          data-testid="product-name-input"
          required
        />
        <Select
          label="Categoría"
          value={category}
          onChange={(e) => setCategory(e.target.value as ProductCategory)}
          data-testid="product-category-select"
        >
          {CATEGORIES.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </Select>
      </div>
      <Input
        label="Descripción"
        value={description}
        onChange={(e) => setDescription(e.target.value)}
        data-testid="product-description-input"
      />

      <fieldset className="variant-fieldset">
        <legend className="text-label">Variantes</legend>
        {variants.map((variant, index) => (
          <div className="variant-row" key={index} data-testid={`variant-form-row-${index}`}>
            <Input
              label="Nombre"
              value={variant.name}
              onChange={(e) => updateVariant(index, { name: e.target.value })}
              data-testid={`variant-name-${index}`}
            />
            <Input
              label="SKU"
              value={variant.sku}
              onChange={(e) => updateVariant(index, { sku: e.target.value })}
              data-testid={`variant-sku-${index}`}
            />
            <Input
              label="Precio (USD)"
              type="number"
              min="0"
              step="0.01"
              value={variant.price}
              onChange={(e) => updateVariant(index, { price: e.target.value })}
              data-testid={`variant-price-${index}`}
            />
            <Select
              label="Material"
              value={variant.materialId}
              onChange={(e) => updateVariant(index, { materialId: e.target.value })}
              data-testid={`variant-material-${index}`}
            >
              {materials.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </Select>
            <Input
              label="Peso (g)"
              type="number"
              min="0"
              value={variant.weight}
              onChange={(e) => updateVariant(index, { weight: e.target.value })}
              data-testid={`variant-weight-${index}`}
            />
            <Input
              label="Stock inicial"
              type="number"
              min="0"
              value={variant.stock}
              onChange={(e) => updateVariant(index, { stock: e.target.value })}
              data-testid={`variant-stock-${index}`}
            />
            {variants.length > 1 && (
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={() => removeVariantRow(index)}
              >
                Quitar variante
              </Button>
            )}
          </div>
        ))}
        <Button type="button" variant="secondary" size="sm" onClick={addVariantRow}>
          + Agregar variante
        </Button>
      </fieldset>

      <div>
        <Button type="submit" variant="primary" data-testid="product-submit">
          Guardar figura
        </Button>
      </div>
    </form>
  );
}
