import { useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { Material, ProductCategory, useErpStore } from "@octo-erp/shared";
import { Button, Callout, Input, Select } from "../design-system";
import { useTheme } from "../theme/ThemeContext";

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
  const { spacing } = useTheme();
  const addProduct = useErpStore((s) => s.addProduct);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [category, setCategory] = useState<ProductCategory>(CATEGORIES[0]);
  const [variant, setVariant] = useState<VariantDraft>(emptyVariant(materials[0]?.id ?? ""));
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  function handleSubmit() {
    setError(null);
    if (!name.trim()) {
      setError("El nombre de la figura es obligatorio.");
      return;
    }
    if (!variant.name.trim() || !variant.sku.trim() || !variant.materialId) {
      setError("Completá nombre, SKU y material de la variante.");
      return;
    }
    try {
      addProduct({
        name: name.trim(),
        description: description.trim(),
        category,
        variants: [
          {
            name: variant.name.trim(),
            sku: variant.sku.trim(),
            priceCents: Math.round(Number(variant.price || 0) * 100),
            materialId: variant.materialId,
            weightGrams: Number(variant.weight || 0),
            stockUnits: Number(variant.stock || 0),
            reorderThreshold: Number(variant.threshold || 0),
          },
        ],
      });
      setSuccess(true);
      setName("");
      setDescription("");
      setVariant(emptyVariant(materials[0]?.id ?? ""));
      onCreated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear la figura.");
    }
  }

  return (
    <ScrollView contentContainerStyle={{ gap: spacing.space4, padding: spacing.space4 }} testID="product-form">
      {error && <Callout tone="critical" testID="product-form-error">{error}</Callout>}
      {success && <Callout tone="valid" testID="product-form-success">Figura creada correctamente.</Callout>}
      <Input label="Nombre de la figura" value={name} onChangeText={setName} testID="product-name-input" />
      <Select
        label="Categoría"
        value={category}
        onChange={(v) => setCategory(v as ProductCategory)}
        options={CATEGORIES.map((c) => ({ value: c, label: c }))}
        testID="product-category-select"
      />
      <Input label="Descripción" value={description} onChangeText={setDescription} testID="product-description-input" />

      <View style={styles.variantBlock}>
        <Text style={styles.variantTitle}>Variante</Text>
        <Input label="Nombre" value={variant.name} onChangeText={(v) => setVariant((s) => ({ ...s, name: v }))} testID="variant-name-0" />
        <Input label="SKU" value={variant.sku} onChangeText={(v) => setVariant((s) => ({ ...s, sku: v }))} testID="variant-sku-0" />
        <Input
          label="Precio (USD)"
          value={variant.price}
          onChangeText={(v) => setVariant((s) => ({ ...s, price: v }))}
          keyboardType="numeric"
          testID="variant-price-0"
        />
        <Select
          label="Material"
          value={variant.materialId}
          onChange={(v) => setVariant((s) => ({ ...s, materialId: v }))}
          options={materials.map((m) => ({ value: m.id, label: m.name }))}
          testID="variant-material-0"
        />
        <Input
          label="Peso (g)"
          value={variant.weight}
          onChangeText={(v) => setVariant((s) => ({ ...s, weight: v }))}
          keyboardType="numeric"
          testID="variant-weight-0"
        />
        <Input
          label="Stock inicial"
          value={variant.stock}
          onChangeText={(v) => setVariant((s) => ({ ...s, stock: v }))}
          keyboardType="numeric"
          testID="variant-stock-0"
        />
      </View>

      <Button variant="primary" onPress={handleSubmit} testID="product-submit">
        Guardar figura
      </Button>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  variantBlock: {
    gap: 16,
  },
  variantTitle: {
    fontSize: 12,
    fontWeight: "700",
    letterSpacing: 1,
  },
});
