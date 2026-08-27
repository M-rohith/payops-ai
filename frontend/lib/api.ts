export type DashboardSummary = {
  payment_volume: number;
  success_rate: number;
  failed_payments: number;
  refund_amount: number;
  settlement_amount: number;
  open_alerts: number;
};

export type VolumePoint = { timestamp: string; amount: number; payment_count: number };
export type PaymentMethodMetric = { method: string; payment_count: number; amount: number };
export type Alert = { id: number; type: string; severity: string; title: string; description: string; metric_value: number | null; baseline_value: number | null; status: string; created_at: string };
export type Payment = { id: number; external_payment_id: string; external_order_id: string; customer_name: string; source: "demo" | "razorpay"; amount: number; currency: string; method: string; status: string; error_code: string | null; error_description: string | null; captured: boolean; created_at: string };
export type PaymentList = { items: Payment[]; total: number; limit: number; offset: number };
export type Settlement = { id: number; external_settlement_id: string; expected_amount: number; actual_amount: number; difference: number; fees: number; adjustments: number; status: string; settled_at: string | null; created_at: string };
export type ReconciliationIssue = { id: number; issue_type: string; description: string; status: string; order_id: number | null; external_order_id: string | null; payment_id: number | null; external_payment_id: string | null; amount: number | null; created_at: string };

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export type DataSource = "all" | "demo" | "razorpay";

export async function getDashboardSummary(source: DataSource = "all"): Promise<DashboardSummary> {
  const response = await fetch(`${backendUrl}/api/dashboard/summary?source=${source}`, {
    cache: "no-store",
  });

  if (!response.ok) {
    throw new Error(`Dashboard API returned ${response.status}`);
  }

  return response.json() as Promise<DashboardSummary>;
}

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${backendUrl}${path}`, { cache: "no-store" });
  if (!response.ok) throw new Error(`PayOps API returned ${response.status} for ${path}`);
  return response.json() as Promise<T>;
}

export const getVolume = (range: string, source: DataSource = "all") => apiGet<VolumePoint[]>(`/api/dashboard/volume?time_range=${range}&source=${source}`);
export const getPaymentMethods = (range = "30D", source: DataSource = "all") => apiGet<PaymentMethodMetric[]>(`/api/dashboard/payment-methods?time_range=${range}&source=${source}`);
export const getIssues = (source: DataSource = "all") => apiGet<Alert[]>(`/api/dashboard/issues?source=${source}`);
export const getAlerts = () => apiGet<Alert[]>("/api/alerts");
export const getSettlements = () => apiGet<Settlement[]>("/api/settlements");
export const getReconciliationIssues = () => apiGet<ReconciliationIssue[]>("/api/reconciliation/issues");
export const getPayments = (query = "") => apiGet<PaymentList>(`/api/payments${query ? `?${query}` : ""}`);
