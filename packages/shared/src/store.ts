import { create } from "zustand";
import { makeId } from "./id";
import { seedMaterials, seedOrders, seedProducts, seedVariants } from "./seed";
import {
  InsufficientStockError,
  Material,
  NewOrderInput,
  NewProductInput,
  Order,
  Product,
  ProductVariant,
  StockMovement,
} from "./types";

export interface ErpState {
  products: Product[];
  variants: ProductVariant[];
  materials: Material[];
  orders: Order[];
  movements: StockMovement[];

  addProduct: (input: NewProductInput) => Product;
  adjustVariantStock: (
    variantId: string,
    delta: number,
    reason: StockMovement["reason"],
    note?: string,
  ) => void;
  adjustMaterialStock: (
    materialId: string,
    delta: number,
    reason: StockMovement["reason"],
    note?: string,
  ) => void;
  createOrder: (input: NewOrderInput) => Order;
  updateOrderStatus: (orderId: string, status: Order["status"]) => void;

  variantsForProduct: (productId: string) => ProductVariant[];
  lowStockVariants: () => ProductVariant[];
  lowStockMaterials: () => Material[];
}

export const useErpStore = create<ErpState>((set, get) => ({
  products: [...seedProducts],
  variants: [...seedVariants],
  materials: [...seedMaterials],
  orders: [...seedOrders],
  movements: [],

  addProduct: (input) => {
    const product: Product = {
      id: makeId("prod"),
      name: input.name,
      description: input.description,
      category: input.category,
      imageUrl: input.imageUrl,
      createdAt: new Date().toISOString(),
    };
    const variants: ProductVariant[] = input.variants.map((v) => ({
      id: makeId("var"),
      productId: product.id,
      ...v,
    }));
    set((state) => ({
      products: [...state.products, product],
      variants: [...state.variants, ...variants],
    }));
    return product;
  },

  adjustVariantStock: (variantId, delta, reason, note) => {
    const { variants } = get();
    const variant = variants.find((v) => v.id === variantId);
    if (!variant) throw new Error(`Variante no encontrada: ${variantId}`);
    const nextStock = variant.stockUnits + delta;
    if (nextStock < 0) {
      throw new InsufficientStockError(variantId, variant.stockUnits, -delta);
    }
    const movement: StockMovement = {
      id: makeId("mov"),
      targetType: "variant",
      targetId: variantId,
      delta,
      reason,
      note,
      createdAt: new Date().toISOString(),
    };
    set((state) => ({
      variants: state.variants.map((v) =>
        v.id === variantId ? { ...v, stockUnits: nextStock } : v,
      ),
      movements: [movement, ...state.movements],
    }));
  },

  adjustMaterialStock: (materialId, delta, reason, note) => {
    const { materials } = get();
    const material = materials.find((m) => m.id === materialId);
    if (!material) throw new Error(`Material no encontrado: ${materialId}`);
    const nextStock = material.stockGrams + delta;
    if (nextStock < 0) {
      throw new InsufficientStockError(materialId, material.stockGrams, -delta);
    }
    const movement: StockMovement = {
      id: makeId("mov"),
      targetType: "material",
      targetId: materialId,
      delta,
      reason,
      note,
      createdAt: new Date().toISOString(),
    };
    set((state) => ({
      materials: state.materials.map((m) =>
        m.id === materialId ? { ...m, stockGrams: nextStock } : m,
      ),
      movements: [movement, ...state.movements],
    }));
  },

  createOrder: (input) => {
    const { variants } = get();
    if (input.items.length === 0) {
      throw new Error("El pedido necesita al menos un artículo.");
    }
    for (const item of input.items) {
      const variant = variants.find((v) => v.id === item.variantId);
      if (!variant) throw new Error(`Variante no encontrada: ${item.variantId}`);
      if (variant.stockUnits < item.quantity) {
        throw new InsufficientStockError(item.variantId, variant.stockUnits, item.quantity);
      }
    }

    const orderItems = input.items.map((item) => {
      const variant = variants.find((v) => v.id === item.variantId)!;
      return {
        variantId: item.variantId,
        quantity: item.quantity,
        unitPriceCents: variant.priceCents,
      };
    });
    const totalCents = orderItems.reduce(
      (sum, item) => sum + item.unitPriceCents * item.quantity,
      0,
    );
    const order: Order = {
      id: makeId("ord"),
      code: `ORD-${1000 + get().orders.length + 1}`,
      customerName: input.customerName,
      items: orderItems,
      status: "confirmado",
      createdAt: new Date().toISOString(),
      totalCents,
    };

    const movements: StockMovement[] = orderItems.map((item) => ({
      id: makeId("mov"),
      targetType: "variant",
      targetId: item.variantId,
      delta: -item.quantity,
      reason: "venta",
      note: order.code,
      createdAt: new Date().toISOString(),
    }));

    set((state) => ({
      orders: [order, ...state.orders],
      variants: state.variants.map((v) => {
        const item = orderItems.find((i) => i.variantId === v.id);
        return item ? { ...v, stockUnits: v.stockUnits - item.quantity } : v;
      }),
      movements: [...movements, ...state.movements],
    }));

    return order;
  },

  updateOrderStatus: (orderId, status) => {
    set((state) => ({
      orders: state.orders.map((o) => (o.id === orderId ? { ...o, status } : o)),
    }));
  },

  variantsForProduct: (productId) => get().variants.filter((v) => v.productId === productId),
  lowStockVariants: () => get().variants.filter((v) => v.stockUnits <= v.reorderThreshold),
  lowStockMaterials: () =>
    get().materials.filter((m) => m.stockGrams <= m.reorderThresholdGrams),
}));
