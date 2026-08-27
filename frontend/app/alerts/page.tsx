import { PageHeader } from "@/components/page-header";
import { StatusBadge } from "@/components/status-badge";
import { getAlerts } from "@/lib/api";
import { formatDate } from "@/lib/format";

export default async function AlertsPage() { const alerts = await getAlerts(); return <><PageHeader eyebrow="MONITORING" title="Alerts" description="Operational signals derived from the seeded payment and settlement dataset."/><div className="mt-6 grid gap-4">{alerts.map(a=><article className="rounded-xl border border-slate-200 bg-white p-5 shadow-card" key={a.id}><div className="flex items-start justify-between gap-4"><div className="flex gap-3"><StatusBadge value={a.severity}/><div><p className="text-xs font-medium uppercase tracking-wide text-slate-400">{a.type.replaceAll("_", " ")}</p><h2 className="mt-1 font-semibold">{a.title}</h2></div></div><StatusBadge value={a.status}/></div><p className="mt-4 text-sm leading-6 text-slate-600">{a.description}</p><p className="mt-3 text-xs text-slate-400">Created {formatDate(a.created_at)}</p></article>)}</div></>; }
