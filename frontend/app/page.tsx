import Link from "next/link";

import { InvestigationQueue } from "@/components/investigation-queue";
import { MethodBreakdown } from "@/components/method-breakdown";
import { RazorpaySourceWarning } from "@/components/razorpay-source-warning";
import { SourceSelector } from "@/components/source-selector";
import { SummaryCard } from "@/components/summary-card";
import { VolumeChart } from "@/components/volume-chart";
import { DataSource, getDashboardSummary, getInvestigations, getPaymentMethods, getVolume } from "@/lib/api";
import { formatMoney } from "@/lib/format";

export default async function OverviewPage({ searchParams }: { searchParams: Promise<{ source?: string }> }) {
  const requested = (await searchParams).source;
  const source: DataSource = requested === "demo" || requested === "razorpay" ? requested : "all";
  const sourceLabel = source === "demo" ? "Demo Data" : source === "razorpay" ? "Razorpay Test" : "All Data";
  const [summary, volume, methods, investigations] = await Promise.all([
    getDashboardSummary(source),
    getVolume("7D", source),
    getPaymentMethods("30D", source),
    getInvestigations(source),
  ]);

  return <>
    <div className="flex flex-col gap-5 border-b border-slate-200 pb-7 sm:flex-row sm:items-end sm:justify-between"><div><p className="text-xs font-semibold tracking-[0.16em] text-brand">PAYMENT OPERATIONS</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">Overview</h1><p className="mt-2 text-sm text-slate-500">Local PostgreSQL analytics · <strong className="text-ink">{sourceLabel}</strong></p></div><SourceSelector selected={source}/></div>
    {source === "razorpay" && <RazorpaySourceWarning />}
    <section className="mt-7 grid gap-4 sm:grid-cols-2 xl:grid-cols-4"><SummaryCard label="Payment Volume" value={formatMoney(summary.payment_volume, true)} detail="Gross captured volume · 30D"/><SummaryCard label="Success Rate" value={`${summary.success_rate}%`} detail={`${summary.failed_payments} failed payments`}/><SummaryCard label="Settlement Amount" value={formatMoney(summary.settlement_amount, true)} detail={source === "razorpay" && summary.settlement_amount === 0 ? "No local settlement data available" : "Processed settlements · 30D"}/><SummaryCard label="Refund Amount" value={formatMoney(summary.refund_amount, true)} detail="Processed refunds · 30D"/></section>
    <div className="mt-6 grid gap-6 xl:grid-cols-[1.65fr_1fr]"><VolumeChart initial={volume} source={source}/><MethodBreakdown methods={methods}/></div>
    <InvestigationQueue items={investigations} selectedSource={source} />
    <section className="mt-6 overflow-hidden rounded-xl border border-indigo-100 bg-white shadow-card" id="payops-ai"><div className="border-b border-indigo-100 bg-gradient-to-r from-indigo-50 to-white px-6 py-5"><p className="text-xs font-semibold tracking-wider text-brand">READ-ONLY OPERATIONS COPILOT</p><h2 className="mt-1 text-xl font-semibold">Ask PayOps AI</h2></div><div className="flex flex-col items-start justify-between gap-4 p-6 sm:flex-row sm:items-center"><p className="max-w-xl text-sm leading-6 text-slate-500">Investigate payments, failure reasons, settlements, alerts, and reconciliation issues through controlled backend tools.</p><Link className="shrink-0 rounded-lg bg-brand px-4 py-2.5 text-sm font-semibold text-white" href={`/copilot?source=${source}`}>Open PayOps AI</Link></div></section>
  </>;
}
