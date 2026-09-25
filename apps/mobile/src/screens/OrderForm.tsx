import { useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { Product, ProductVariant, useErpStore } from "@octo-erp/shared";
import { Button, Callout, Input, Select } from "../design-system";
import { useTheme } from "../theme/ThemeContext";

interface OrderFormProps {
  variants: ProductVariant[];
  products: Product[];
  onCreated?: () => void;
}

export function OrderForm({ variants, products, onCreated }: OrderFormProps) {
  const { spacing, colors } = useTheme();
  const createOrder = useErpStore((s) => s.createOrder);
  const [customerName, setCustomerName] = useState("");
  const [variantId, setVariantId] = useState(variants[0]?.id ?? "");
  const [quantity, setQuantity] = useState("1");
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  function productName(productId: string) {
    return products.find((p) => p.id === productId)?.name ?? "—";
  }

  const selectedVariant = variants.find((v) => v.id === variantId);

  function handleSubmit() {
    setError(null);
    setSuccess(null);
    if (!customerName.trim()) {
      setError("El nombre del cliente es obligatorio.");
      return;
    }
    try {
      const order = createOrder({
        customerName: customerName.trim(),
        items: [{ variantId, quantity: Number(quantity || 0) }],
      });
      setSuccess(`Pedido ${order.code} creado.`);
      setCustomerName("");
      setQuantity("1");
      onCreated?.();
    } catch (err) {
      setError(err instanceof Error ? err.message : "No se pudo crear el pedido.");
    }
  }

  return (
    <ScrollView contentContainerStyle={{ gap: spacing.space4, padding: spacing.space4 }} testID="order-form">
      {error && <Callout tone="critical" testID="order-form-error">{error}</Callout>}
      {success && <Callout tone="valid" testID="order-form-success">{success}</Callout>}
      <Input label="Cliente" value={customerName} onChangeText={setCustomerName} testID="order-customer-input" />
      <Select
        label="Variante"
        value={variantId}
        onChange={setVariantId}
        options={variants.map((v) => ({
          value: v.id,
          label: `${productName(v.productId)} — ${v.name} (${v.stockUnits} disp.)`,
        }))}
        testID="order-item-variant-0"
      />
      <Input
        label="Cantidad"
        value={quantity}
        onChangeText={setQuantity}
        keyboardType="numeric"
        testID="order-item-quantity-0"
      />
      <Text style={{ color: colors.inkMuted, fontSize: 14 }} testID="order-item-available-0">
        Disponible: {selectedVariant?.stockUnits ?? 0}
      </Text>
      <Button variant="primary" onPress={handleSubmit} testID="order-submit">
        Confirmar pedido
      </Button>
    </ScrollView>
  );
}
