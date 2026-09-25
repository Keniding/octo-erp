export function formatCurrency(cents: number): string {
  return (cents / 100).toLocaleString("es-AR", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
  });
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("es-AR", {
    year: "numeric",
    month: "short",
    day: "2-digit",
  });
}
