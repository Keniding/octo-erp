import { useState } from "react";
import { ScrollView, StyleSheet, Text, View } from "react-native";
import { useErpStore } from "@octo-erp/shared";
import { Button, Callout, Card, Input, Label, Select } from "../design-system";
import { useTheme } from "../theme/ThemeContext";

export function InventoryScreen() {
  const variants = useErpStore((s) => s.variants);
  const materials = useErpStore((s) => s.materials);
  const products = useErpStore((s) => s.products);
  const adjustVariantStock = useErpStore((s) => s.adjustVariantStock);
  const { spacing, colors } = useTheme();

  const [variantId, setVariantId] = useState(variants[0]?.id ?? "");
  const [delta, setDelta] = useState("1");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function productName(productId: string) {
    return products.find((p) => p.id === productId)?.name ?? "—";
  }

  function handleAdjust() {
    setError(null);
    setSuccess(null);
    const amount = Number(delta);
    if (!variantId || !amount) {
      setError("Elegí una variante y una cantidad distinta de cero.");
      return;
    }
    try {
      adjustVariantStock(variantId, amount, "ajuste-manual");
      setSuccess("Stock actualizado.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo ajustar el stock.");
    }
  }

  const lowStock = variants.filter((v) => v.stockUnits <= v.reorderThreshold);

  return (
    <ScrollView testID="inventory-page" contentContainerStyle={{ padding: spacing.space4, gap: spacing.space4 }}>
      <View>
        <Label parts={["Inventario", "Stock y filamento"]} />
        <Text style={[styles.heading, { color: colors.ink }]}>Inventario</Text>
      </View>

      {error && <Callout tone="critical" testID="inventory-error">{error}</Callout>}
      {success && <Callout tone="valid" testID="inventory-success">{success}</Callout>}
      {lowStock.length > 0 && (
        <Callout tone="warning" testID="inventory-low-stock">
          {lowStock.length} variante(s) por debajo del umbral de reposición.
        </Callout>
      )}

      <Card label={["Variantes", "Ajuste"]} title="Ajustar stock">
        <View style={{ gap: spacing.space4 }} testID="variant-stock-form">
          <Select
            label="Variante"
            value={variantId}
            onChange={setVariantId}
            options={variants.map((v) => ({
              value: v.id,
              label: `${productName(v.productId)} — ${v.name} (${v.stockUnits} u.)`,
            }))}
            testID="variant-stock-select"
          />
          <Input
            label="Cantidad (+ ingreso / - salida)"
            value={delta}
            onChangeText={setDelta}
            keyboardType="numeric"
            testID="variant-stock-delta"
          />
          <Button variant="primary" onPress={handleAdjust} testID="variant-stock-submit">
            Aplicar ajuste
          </Button>
        </View>
      </Card>

      <Card label={["Detalle"]} title="Stock por variante">
        <View style={{ gap: spacing.space2 }} testID="variant-stock-table">
          {variants.map((v) => (
            <View key={v.id} style={[styles.row, { borderBottomColor: colors.rule }]} testID={`variant-stock-row-${v.id}`}>
              <Text style={{ color: colors.ink, flex: 1 }}>
                {productName(v.productId)} — {v.name}
              </Text>
              <Text style={{ color: colors.ink }} testID={`variant-stock-value-${v.id}`}>
                {v.stockUnits} u.
              </Text>
            </View>
          ))}
        </View>
      </Card>

      <Card label={["Detalle"]} title="Stock de materiales">
        <View style={{ gap: spacing.space2 }} testID="material-stock-table">
          {materials.map((m) => (
            <View key={m.id} style={[styles.row, { borderBottomColor: colors.rule }]}>
              <Text style={{ color: colors.ink, flex: 1 }}>{m.name}</Text>
              <Text style={{ color: colors.ink }}>{m.stockGrams} g</Text>
            </View>
          ))}
        </View>
      </Card>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  heading: {
    fontSize: 30,
    fontWeight: "500",
  },
  row: {
    flexDirection: "row",
    justifyContent: "space-between",
    borderBottomWidth: 1,
    paddingBottom: 6,
  },
});
