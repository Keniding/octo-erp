import type { Material, Order, Product, ProductVariant } from "./types";

export const seedMaterials: Material[] = [
  {
    id: "mat-pla-negro",
    name: "PLA Negro",
    type: "PLA",
    colorHex: "#191919",
    costPerGramCents: 4,
    stockGrams: 4200,
    reorderThresholdGrams: 500,
  },
  {
    id: "mat-pla-terracota",
    name: "PLA Terracota",
    type: "PLA",
    colorHex: "#cc5a3f",
    costPerGramCents: 5,
    stockGrams: 1800,
    reorderThresholdGrams: 500,
  },
  {
    id: "mat-petg-transparente",
    name: "PETG Transparente",
    type: "PETG",
    colorHex: "#bdd2cb",
    costPerGramCents: 6,
    stockGrams: 900,
    reorderThresholdGrams: 400,
  },
  {
    id: "mat-resina-gris",
    name: "Resina Gris Detalle",
    type: "Resina",
    colorHex: "#7d8d78",
    costPerGramCents: 12,
    stockGrams: 350,
    reorderThresholdGrams: 300,
  },
];

export const seedProducts: Product[] = [
  {
    id: "prod-samurai",
    name: "Samurai errante",
    description:
      "Figura de samurái en pose de combate, esculpida a partir de grabados clásicos y reinterpretada en poliedros bajos.",
    category: "Fantasia",
    createdAt: "2026-01-12T10:00:00.000Z",
  },
  {
    id: "prod-mecha",
    name: "Centinela Mecha MK-II",
    description: "Mecha articulado de línea limpia, impreso por piezas y ensamblado sin pegamento.",
    category: "Videojuegos",
    createdAt: "2026-02-03T10:00:00.000Z",
  },
  {
    id: "prod-dragon-whelp",
    name: "Dragoncillo de cuarzo",
    description: "Miniatura de dragón joven para mesa de rol, base hexagonal de 25mm.",
    category: "Miniaturas TTRPG",
    createdAt: "2026-02-20T10:00:00.000Z",
  },
];

export const seedVariants: ProductVariant[] = [
  {
    id: "var-samurai-10-sin-pintar",
    productId: "prod-samurai",
    name: "10cm — sin pintar",
    sku: "SAM-10-RAW",
    priceCents: 1800,
    materialId: "mat-pla-negro",
    weightGrams: 85,
    stockUnits: 14,
    reorderThreshold: 5,
  },
  {
    id: "var-samurai-18-pintada",
    productId: "prod-samurai",
    name: "18cm — pintada",
    sku: "SAM-18-PAINT",
    priceCents: 5200,
    materialId: "mat-pla-terracota",
    weightGrams: 210,
    stockUnits: 4,
    reorderThreshold: 3,
  },
  {
    id: "var-mecha-standard",
    productId: "prod-mecha",
    name: "Estándar — articulado",
    sku: "MEC-STD",
    priceCents: 4600,
    materialId: "mat-petg-transparente",
    weightGrams: 260,
    stockUnits: 7,
    reorderThreshold: 4,
  },
  {
    id: "var-dragon-resina",
    productId: "prod-dragon-whelp",
    name: "Base 25mm — resina",
    sku: "DRG-25-RES",
    priceCents: 2400,
    materialId: "mat-resina-gris",
    weightGrams: 22,
    stockUnits: 2,
    reorderThreshold: 6,
  },
];

export const seedOrders: Order[] = [
  {
    id: "ord-1001",
    code: "ORD-1001",
    customerName: "Estudio Katana",
    items: [
      { variantId: "var-samurai-10-sin-pintar", quantity: 2, unitPriceCents: 1800 },
    ],
    status: "confirmado",
    createdAt: "2026-03-01T15:30:00.000Z",
    totalCents: 3600,
  },
];
