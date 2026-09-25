import { useState } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { formatCurrency, useErpStore } from "@octo-erp/shared";
import { Button, Card, Label } from "../design-system";
import { useTheme } from "../theme/ThemeContext";
import { ProductForm } from "./ProductForm";

export function CatalogScreen() {
  const products = useErpStore((s) => s.products);
  const variants = useErpStore((s) => s.variants);
  const materials = useErpStore((s) => s.materials);
  const { spacing, colors } = useTheme();
  const [showForm, setShowForm] = useState(false);

  if (showForm) {
    return (
      <View style={{ flex: 1 }} testID="product-form-panel">
        <View style={{ padding: spacing.space4 }}>
          <Button variant="ghost" onPress={() => setShowForm(false)} testID="toggle-new-product">
            Cerrar
          </Button>
        </View>
        <ProductForm materials={materials} />
      </View>
    );
  }

  return (
    <FlatList
      testID="catalog-page"
      data={products}
      keyExtractor={(item) => item.id}
      contentContainerStyle={{ padding: spacing.space4, gap: spacing.space4 }}
      ListHeaderComponent={
        <View style={[styles.headerRow, { marginBottom: spacing.space4 }]}>
          <View>
            <Label parts={["Catálogo", "Figuras 3D"]} />
            <Text style={[styles.heading, { color: colors.ink }]}>Catálogo</Text>
          </View>
          <Button variant="primary" onPress={() => setShowForm(true)} testID="toggle-new-product">
            Nueva figura
          </Button>
        </View>
      }
      renderItem={({ item: product }) => {
        const productVariants = variants.filter((v) => v.productId === product.id);
        return (
          <Card
            testID={`product-card-${product.id}`}
            label={[product.category]}
            title={product.name}
            footer={`${productVariants.length} variante(s)`}
          >
            <Text style={{ color: colors.ink, fontSize: 14 }}>{product.description}</Text>
            {productVariants.map((variant) => {
              const material = materials.find((m) => m.id === variant.materialId);
              return (
                <View key={variant.id} style={[styles.variantRow, { borderTopColor: colors.rule }]}>
                  <Text style={{ color: colors.ink, fontSize: 14 }}>{variant.name}</Text>
                  <Text style={{ color: colors.inkMuted, fontSize: 14 }}>
                    {formatCurrency(variant.priceCents)} · {variant.stockUnits} u. · {material?.name}
                  </Text>
                </View>
              );
            })}
          </Card>
        );
      }}
    />
  );
}

const styles = StyleSheet.create({
  headerRow: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "flex-end",
    gap: 12,
  },
  heading: {
    fontSize: 30,
    fontWeight: "500",
  },
  variantRow: {
    borderTopWidth: 1,
    paddingTop: 6,
    marginTop: 6,
    gap: 2,
  },
});
