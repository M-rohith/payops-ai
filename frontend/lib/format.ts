export function formatMoney(minorUnits: number, compact = false): string {
  const rupees = minorUnits / 100;
  if (compact && Math.abs(rupees) >= 100_000) return `₹${(rupees / 100_000).toFixed(2)}L`;
  return new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR", maximumFractionDigits: 0 }).format(rupees);
}

export function formatDate(value: string | null): string {
  if (!value) return "Pending";
  return new Intl.DateTimeFormat("en-IN", { dateStyle: "medium", timeStyle: "short" }).format(new Date(value));
}
