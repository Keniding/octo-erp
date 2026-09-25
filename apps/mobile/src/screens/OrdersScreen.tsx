import { useState } from "react";
import { FlatList, StyleSheet, Text, View } from "react-native";
import { formatCurrency, formatDate, useErpStore } from "@octo-erp/shared";
import { Button, Card, Label } from "../design-system";
import { useTheme } from "../theme/ThemeContext";
import { OrderForm } from "./OrderForm";

export function OrdersScreen() {
  const orders = useErpStore((s) => s.orders);
  const variants = useErpStore((s) => s.variants);
  const products = useErpStore((s) => s.products);
  const { spacing, colors } = useTheme();
  const [showForm, setShowForm] = useState(false);

  function variantLabel(variantId: string) {
    const variant = variants.find((v) => v.id === variantId);
    const product = products.find((p) => p.id === variant?.productId);
    return `${product?.name ?? "—"} — ${variant?.name ?? "—"}`;
  }

  if (showForm) {
    return (
      <View style={{ flex: 1 }} testID="order-form-panel">
        <View style={{ padding: spacing.space4 }}>
          <Button variant="ghost" onPress={() => setShowForm(false)} testID="toggle-new-order">
            Cerrar
          </Button>
        </View>
        <OrderForm variants={variants} products={products} />
      </View>
    );
  }

  return (
    <FlatList
      testID="orders-page"
      data={orders}
      keyExtractor={(item) => item.id}
      contentContainerStyle={{ padding: spacing.space4, gap: spacing.space4 }}
      ListHeaderComponent={
        <View style={[styles.headerRow, { marginBottom: spacing.space4 }]}>
          <View>
            <Label parts={["Ventas", "Pedidos"]} />
            <Text style={[styles.heading, { color: colors.ink }]}>Pedidos</Text>
          </View>
          <Button variant="primary" onPress={() => setShowForm(true)} testID="toggle-new-order">
            Nuevo pedido
          </Button>
        </View>
      }
      renderItem={({ item: order }) => (
        <Card
          testID={`order-card-${order.id}`}
          label={[order.status.replace("_", " ")]}
          title={order.code}
          footer={formatDate(order.createdAt)}
        >
          <Text style={{ color: colors.ink, fontSize: 14 }}>Cliente: {order.customerName}</Text>
          {order.items.map((item, i) => (
            <Text key={i} style={{ color: colors.inkMuted, fontSize: 14 }}>
              {variantLabel(item.variantId)} — {item.quantity} × {formatCurrency(item.unitPriceCents)}
            </Text>
          ))}
          <Text style={{ color: colors.ink, fontWeight: "600" }} testID={`order-total-${order.id}`}>
            Total: {formatCurrency(order.totalCents)}
          </Text>
        </Card>
      )}
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
});
