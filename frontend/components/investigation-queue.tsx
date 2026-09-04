import Link from "next/link";

import { StatusBadge } from "@/components/status-badge";
import type { DataSource, Investigation, InvestigationMetric } from "@/lib/api";
import { formatMoney } from "@/lib/format";

const sourceLabels: Record<Exclude<DataSource, "all">, string> = {
  demo: "Demo Data",
  razorpay: "Razorpay Test",
};

function formatMetric(metric: InvestigationMetric): string {
  if (metric.format === "money") return formatMoney(metric.value);
  if (metric.format === "percent") return `${metric.value}%`;
  if (metric.format === "percentage_points") return `${metric.value > 0 ? "+" : ""}${metric.value}pp`;
  return new Intl.NumberFormat("en-IN").format(metric.value);
}

function investigateHref(item: Investigation): string {
  const params = new URLSearchParams({ source: item.source, question: item.suggested_question });
  return `/copilot?${params.toString()}`;
}

export function InvestigationQueue({ items, selectedSource }: { items: Investigation[]; selectedSource: DataSource }) {
  const selectedLabel = selectedSource === "all" ? "All Data" : sourceLabels[selectedSource];
  return (
    <section aria-labelledby="needs-attention-heading" className="mt-6 rounded-xl border border-slate-200 bg-white shadow-card">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-100 px-5 py-4">
        <div>
          <h2 className="font-semibold" id="needs-attention-heading">Needs Attention</h2>
          <p className="mt-1 text-sm text-slate-500">Prioritized payment-operations issues ready for investigation.</p>
        </div>
        <span className="text-sm font-semibold text-brand">{items.length} for {selectedLabel}</span>
      </div>
      {items.length ? (
        <div className="divide-y divide-slate-100">
          {items.map((item) => (
            <article className="grid gap-4 px-5 py-5 2xl:grid-cols-[minmax(0,1.25fr)_minmax(280px,1fr)_auto] 2xl:items-center" key={item.id}>
              <div className="min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <StatusBadge value={item.severity} />
                  <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-semibold text-slate-600">{sourceLabels[item.source]}</span>
                </div>
                <h3 className="mt-3 font-semibold text-ink">{item.title}</h3>
                <p className="mt-1 text-sm leading-6 text-slate-500">{item.summary}</p>
              </div>
              <div>
                <dl className="grid grid-cols-2 gap-2 sm:grid-cols-3">
                  {item.metrics.slice(0, 3).map((metric) => (
                    <div className="rounded-lg bg-slate-50 px-3 py-2" key={metric.label}>
                      <dt className="text-[10px] font-semibold uppercase tracking-wide text-slate-400">{metric.label}</dt>
                      <dd className="mt-1 text-sm font-semibold text-slate-700">{formatMetric(metric)}</dd>
                    </div>
                  ))}
                </dl>
                <ul className="mt-2 space-y-1 text-xs leading-5 text-slate-500">
                  {item.evidence.slice(0, 2).map((line) => <li key={line}>{line}</li>)}
                </ul>
              </div>
              <Link aria-label={`Investigate ${item.title} with PayOps AI using ${sourceLabels[item.source]}`} className="w-fit shrink-0 rounded-lg border border-brand px-3.5 py-2 text-sm font-semibold text-brand transition-colors hover:bg-indigo-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand" href={investigateHref(item)}>
                Investigate with PayOps AI
              </Link>
            </article>
          ))}
        </div>
      ) : (
        <div className="px-5 py-10 text-center text-sm text-slate-500">No high-priority operational issues for this source.</div>
      )}
    </section>
  );
}
