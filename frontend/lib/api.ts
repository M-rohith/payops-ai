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
export type InvestigationMetric = { label: string; value: number; format: "count" | "money" | "percent" | "percentage_points" };
export type Investigation = { id: string; type: "payment_failure_spike" | "settlement_variance" | "reconciliation_issue" | "alert"; title: string; severity: "high" | "medium" | "low"; source: "demo" | "razorpay"; summary: string; metrics: InvestigationMetric[]; evidence: string[]; financial_impact: number; suggested_question: string };
export type Payment = { id: number; external_payment_id: string; external_order_id: string; customer_name: string; source: "demo" | "razorpay"; amount: number; currency: string; method: string; status: string; error_code: string | null; error_description: string | null; captured: boolean; created_at: string };
export type PaymentList = { items: Payment[]; total: number; limit: number; offset: number };
export type Settlement = { id: number; external_settlement_id: string; expected_amount: number; actual_amount: number; difference: number; fees: number; adjustments: number; status: string; settled_at: string | null; created_at: string };
export type ReconciliationIssue = { id: number; issue_type: string; description: string; status: string; order_id: number | null; external_order_id: string | null; payment_id: number | null; external_payment_id: string | null; amount: number | null; created_at: string };
export type EvaluationCase = { case_id: string; benchmark: "specification" | "robustness"; benchmark_name: string; scenario: string; expected: string; predicted: string; correct: boolean; display_status: "correct" | "safe_unresolved" | "incorrect_unresolved" | "mismatch"; ground_truth_reason: string; engine_reason: string; evidence_summary: string[] };
export type EvaluationMetrics = { cases_processed: number; total_correct: number; total_incorrect: number; clean_match_recall: number; exception_precision: number; exception_recall: number; exception_f1: number; exception_classification_accuracy: number; unresolved_count: number; unresolved_rate: number; correctly_unresolved: number; incorrectly_unresolved: number; false_positive_exceptions: number; missed_exceptions: number; misclassified_exception_types: number };
export type EvaluationBenchmark = { key: "specification" | "robustness"; name: string; seed: number; dataset_version: string; dataset_sha256: string; synthetic: boolean; metrics: EvaluationMetrics; runtime_seconds: number; throughput_cases_per_second: number; scenario_distribution: Record<string, number>; cases: EvaluationCase[]; known_mismatches: EvaluationCase[] };
export type EvaluationPayload = { generated_from: string; disclaimer: string; benchmarks: EvaluationBenchmark[]; known_limitation: { title: string; summary: string; detail: string } };

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
export const getInvestigations = (source: DataSource = "all") => apiGet<Investigation[]>(`/api/investigations?source=${source}`);
export const getAlerts = () => apiGet<Alert[]>("/api/alerts");
export const getSettlements = () => apiGet<Settlement[]>("/api/settlements");
export const getReconciliationIssues = () => apiGet<ReconciliationIssue[]>("/api/reconciliation/issues");
export const getPayments = (query = "") => apiGet<PaymentList>(`/api/payments${query ? `?${query}` : ""}`);
export const getEvaluation = () => apiGet<EvaluationPayload>("/api/evaluation");
