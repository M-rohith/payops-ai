import { EvaluationAudit } from "@/components/evaluation-audit";
import { PageHeader } from "@/components/page-header";
import { getEvaluation } from "@/lib/api";

export default async function EvaluationPage() {
  const payload = await getEvaluation();
  return <>
    <PageHeader eyebrow="AUDITABLE FINANCE CONTROL" title="Reconciliation Evaluation" description="Deterministic, reproducible evaluation of PayOps AI's finance-control layer." />
    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm font-semibold text-amber-900">{payload.disclaimer}</div>
    <section className="mt-6 rounded-xl border border-indigo-100 bg-indigo-50/60 p-5"><h2 className="font-semibold text-indigo-950">How the evidence flows</h2><div className="mt-3 flex flex-wrap items-center gap-2 text-xs font-semibold text-indigo-900"><span className="rounded-md bg-white px-3 py-2">Synthetic benchmark</span><span aria-hidden="true">→</span><span className="rounded-md bg-white px-3 py-2">Deterministic reconciliation</span><span aria-hidden="true">→</span><span className="rounded-md bg-white px-3 py-2">Measured results</span><span aria-hidden="true">→</span><span className="rounded-md bg-white px-3 py-2">Exceptions / unresolved</span><span aria-hidden="true">→</span><span className="rounded-md bg-white px-3 py-2">Grounded investigation</span></div><p className="mt-3 text-xs leading-5 text-indigo-900">Fixed seeds generate known ground truth. The engine receives financial evidence—not expected labels—and every unresolved result is preserved. Razorpay Test Mode provides real integration evidence; these benchmarks evaluate deterministic finance-control logic; PayOps AI explains operational data through controlled tools.</p></section>
    <section aria-labelledby="known-limitation" className="my-6 rounded-xl border-l-4 border-l-amber-500 border-y-amber-200 border-r-amber-200 bg-white p-5 shadow-card"><p className="text-xs font-semibold uppercase tracking-wide text-amber-700">Known limitation</p><h2 className="mt-1 text-lg font-semibold" id="known-limitation">{payload.known_limitation.title}</h2><p className="mt-2 font-medium text-slate-800">{payload.known_limitation.summary}</p><p className="mt-1 text-sm leading-6 text-slate-600">{payload.known_limitation.detail}</p></section>
    <EvaluationAudit benchmarks={payload.benchmarks} />
    <p className="mt-5 text-xs leading-5 text-slate-500">Results are cached from a deterministic in-memory evaluation in this backend process. Runtime varies by machine. This synthetic, developer-authored evaluation does not establish universal production accuracy.</p>
  </>;
}
