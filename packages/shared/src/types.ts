export type MaterialType = "PLA" | "PETG" | "ABS" | "Resina" | "TPU";

export interface Material {
  id: string;
  name: string;
  type: MaterialType;
  colorHex: string;
  costPerGramCents: number;
  stockGrams: number;
  reorderThresholdGrams: number;
}

export type ProductCategory =
  | "Anime"
  | "Videojuegos"
  | "Fantasia"
  | "Miniaturas TTRPG"
  | "Personalizado";

export interface ProductVariant {
  id: string;
  productId: string;
  name: string;
  sku: string;
  priceCents: number;
  materialId: string;
  weightGrams: number;
  stockUnits: number;
  reorderThreshold: number;
}

export interface Product {
  id: string;
  name: string;
  description: string;
  category: ProductCategory;
  imageUrl?: string;
  createdAt: string;
}

export type StockMovementReason =
  | "recepcion"
  | "ajuste-manual"
  | "venta"
  | "merma"
  | "produccion";

export interface StockMovement {
  id: string;
  targetType: "variant" | "material";
  targetId: string;
  delta: number;
  reason: StockMovementReason;
  note?: string;
  createdAt: string;
}

export type OrderStatus =
  | "borrador"
  | "confirmado"
  | "en_produccion"
  | "enviado"
  | "cancelado";

export interface OrderItem {
  variantId: string;
  quantity: number;
  unitPriceCents: number;
}

export interface Order {
  id: string;
  code: string;
  customerName: string;
  items: OrderItem[];
  status: OrderStatus;
  createdAt: string;
  totalCents: number;
}

export interface NewProductInput {
  name: string;
  description: string;
  category: ProductCategory;
  imageUrl?: string;
  variants: Array<{
    name: string;
    sku: string;
    priceCents: number;
    materialId: string;
    weightGrams: number;
    stockUnits: number;
    reorderThreshold: number;
  }>;
}

export interface NewOrderInput {
  customerName: string;
  items: Array<{ variantId: string; quantity: number }>;
}

export class InsufficientStockError extends Error {
  constructor(public variantId: string, public available: number, public requested: number) {
    super(
      `Stock insuficiente para la variante ${variantId}: disponible ${available}, solicitado ${requested}`,
    );
    this.name = "InsufficientStockError";
  }
}
