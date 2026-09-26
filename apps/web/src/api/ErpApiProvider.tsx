import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useState,
} from "react";
import {
  Material,
  NewOrderInput,
  NewProductInput,
  Order,
  Product,
  ProductVariant,
  StockMovement,
  StockMovementReason,
} from "@octo-erp/shared";

/** services/octo-erp-agent (http_app.py) — nunca packages/shared/src/store.ts (ver
 * docs/decisions/007-rest-api-para-apps-web.md). Default: backend local para dev/e2e; para
 * verificar contra lo desplegado en Azure se sobreescribe con VITE_API_BASE_URL al levantar
 * Vite, sin tocar este archivo. */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

interface ErpData {
  products: Product[];
  variants: ProductVariant[];
  materials: Material[];
  orders: Order[];
  movements: StockMovement[];
}

const EMPTY_STATE: ErpData = { products: [], variants: [], materials: [], orders: [], movements: [] };

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({ error: response.statusText }));
    throw new Error(body.error ?? `Error ${response.status} llamando a ${path}`);
  }
  return (await response.json()) as T;
}

interface ErpApiState extends ErpData {
  loading: boolean;
  loadError: string | null;
  addProduct: (input: NewProductInput) => Promise<Product>;
  adjustVariantStock: (
    variantId: string,
    delta: number,
    reason: StockMovementReason,
    note?: string,
  ) => Promise<ProductVariant>;
  adjustMaterialStock: (
    materialId: string,
    delta: number,
    reason: StockMovementReason,
    note?: string,
  ) => Promise<Material>;
  createOrder: (input: NewOrderInput) => Promise<Order>;
}

const ErpApiContext = createContext<ErpApiState | null>(null);

export function ErpApiProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<ErpData>(EMPTY_STATE);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    const state = await apiFetch<ErpData>("/api/state");
    // list_orders() del backend devuelve orden de inserción (más viejo primero); la UI
    // esperaba más reciente primero, como hacía el store en memoria al hacer unshift.
    setData({ ...state, orders: [...state.orders].reverse() });
  }, []);

  useEffect(() => {
    refresh()
      .catch((err) => setLoadError(err instanceof Error ? err.message : "No se pudo cargar el estado."))
      .finally(() => setLoading(false));
  }, [refresh]);

  const addProduct = useCallback(async (input: NewProductInput) => {
    const result = await apiFetch<{ product: Product; variants: ProductVariant[] }>("/api/products", {
      method: "POST",
      body: JSON.stringify(input),
    });
    setData((prev) => ({
      ...prev,
      products: [...prev.products, result.product],
      variants: [...prev.variants, ...result.variants],
    }));
    return result.product;
  }, []);

  const adjustVariantStock = useCallback(
    async (variantId: string, delta: number, reason: StockMovementReason, note?: string) => {
      const variant = await apiFetch<ProductVariant>(`/api/variants/${variantId}/stock-adjustments`, {
        method: "POST",
        body: JSON.stringify({ delta, reason, note }),
      });
      setData((prev) => ({
        ...prev,
        variants: prev.variants.map((v) => (v.id === variant.id ? variant : v)),
      }));
      return variant;
    },
    [],
  );

  const adjustMaterialStock = useCallback(
    async (materialId: string, delta: number, reason: StockMovementReason, note?: string) => {
      const material = await apiFetch<Material>(`/api/materials/${materialId}/stock-adjustments`, {
        method: "POST",
        body: JSON.stringify({ delta, reason, note }),
      });
      setData((prev) => ({
        ...prev,
        materials: prev.materials.map((m) => (m.id === material.id ? material : m)),
      }));
      return material;
    },
    [],
  );

  const createOrder = useCallback(
    async (input: NewOrderInput) => {
      const order = await apiFetch<Order>("/api/orders", {
        method: "POST",
        body: JSON.stringify(input),
      });
      // El pedido ya quedó guardado (con el stock descontado) del lado del servidor antes
      // de que esta respuesta vuelva — refrescar alcanza para reflejar ambas cosas, no hay
      // que recalcular el descuento de stock en el cliente.
      await refresh();
      return order;
    },
    [refresh],
  );

  return (
    <ErpApiContext.Provider
      value={{ ...data, loading, loadError, addProduct, adjustVariantStock, adjustMaterialStock, createOrder }}
    >
      {children}
    </ErpApiContext.Provider>
  );
}

export function useErp(): ErpApiState {
  const ctx = useContext(ErpApiContext);
  if (!ctx) throw new Error("useErp debe usarse dentro de <ErpApiProvider>.");
  return ctx;
}
