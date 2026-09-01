"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import type { EvaluationBenchmark, EvaluationCase } from "@/lib/api";

type ResultFilter = "all" | "correct" | "unresolved" | "mismatches";
type BenchmarkFilter = "all" | "specification" | "robustness";

const statusStyle: Record<EvaluationCase["display_status"], string> = {
  correct: "border-emerald-200 bg-emerald-50 text-emerald-800",
  safe_unresolved: "border-blue-200 bg-blue-50 text-blue-800",
  incorrect_unresolved: "border-amber-300 bg-amber-50 text-amber-900",
  mismatch: "border-rose-200 bg-rose-50 text-rose-800",
};
const statusLabel: Record<EvaluationCase["display_status"], string> = {
  correct: "Correct",
  safe_unresolved: "Safe unresolved",
  incorrect_unresolved: "Incorrect unresolved",
  mismatch: "Mismatch",
};
const label = (value: string) => value.toLowerCase().replaceAll("_", " ").replace(/^./, (first) => first.toUpperCase());
const percent = (value: number) => `${(value * 100).toFixed(value === 1 ? 0 : 2)}%`;

function Metric({ name, value, note }: { name: string; value: string; note?: string }) {
  return <div className="rounded-lg border border-slate-200 bg-white p-3"><p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{name}</p><p className="mt-1 text-xl font-semibold text-ink">{value}</p>{note && <p className="mt-1 text-xs text-slate-500">{note}</p>}</div>;
}

function BenchmarkCard({ benchmark }: { benchmark: EvaluationBenchmark }) {
  const m = benchmark.metrics;
  const purpose = benchmark.key === "specification" ? "Validates deterministic reconciliation against known specification cases." : "Challenges the reconciliation engine with adversarial and edge-case variations.";
  return <section aria-labelledby={`${benchmark.key}-title`} className="rounded-xl border border-slate-200 bg-slate-50/60 p-5">
    <div className="flex flex-wrap items-start justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wide text-brand">Benchmark {benchmark.key === "specification" ? "A" : "B"}</p><h2 className="mt-1 text-xl font-semibold" id={`${benchmark.key}-title`}>{benchmark.name}</h2><p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{purpose}</p></div><div className="rounded-lg border border-slate-200 bg-white px-3 py-2 text-right text-xs text-slate-500"><strong className="block text-sm text-ink">{m.cases_processed} cases</strong>Fixed seed {benchmark.seed}</div></div>
    <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
      <Metric name={benchmark.key === "specification" ? "Specification correctness" : "Robustness correctness"} value={`${m.total_correct}/${m.cases_processed}`} note={percent(m.total_correct / m.cases_processed)} />
      <Metric name="Clean-match recall" value={percent(m.clean_match_recall)} />
      <Metric name="Exception precision / recall" value={`${percent(m.exception_precision)} / ${percent(m.exception_recall)}`} />
      <Metric name="Exception F1 / classification" value={`${percent(m.exception_f1)} / ${percent(m.exception_classification_accuracy)}`} />
      <Metric name="Unresolved" value={`${m.unresolved_count}`} note={`${m.correctly_unresolved} correct · ${m.incorrectly_unresolved} incorrect`} />
      <Metric name="False positives / missed" value={`${m.false_positive_exceptions} / ${m.missed_exceptions}`} />
      <Metric name="Local deterministic runtime" value={`${(benchmark.runtime_seconds * 1000).toFixed(2)} ms`} note="Cached result measured on this backend process" />
      <Metric name="Local in-memory throughput" value={`${Math.round(benchmark.throughput_cases_per_second).toLocaleString()}/s`} note="Not production payment capacity" />
    </div>
    <div className="mt-5 border-t border-slate-200 pt-4"><p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Dataset composition</p><div className="mt-3 flex flex-wrap gap-2">{Object.entries(benchmark.scenario_distribution).sort().map(([scenario, count]) => <span className="rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-700" key={scenario}><span className="font-medium">{label(scenario)}</span> · {count}</span>)}</div></div>
  </section>;
}

function CaseDetails({ item }: { item: EvaluationCase }) {
  return <div className="grid gap-4 bg-slate-50 px-4 py-4 text-sm md:grid-cols-2">
    <div><p className="font-semibold text-slate-500">Ground-truth reason</p><p className="mt-1 leading-6 text-slate-700">{item.ground_truth_reason}</p></div>
    <div><p className="font-semibold text-slate-500">Engine reason</p><p className="mt-1 leading-6 text-slate-700">{item.engine_reason}</p></div>
    <div className="md:col-span-2"><p className="font-semibold text-slate-500">Relevant evidence</p><ul className="mt-2 grid gap-1.5 text-slate-700 sm:grid-cols-2">{item.evidence_summary.map((fact) => <li className="rounded-md border border-slate-200 bg-white px-3 py-2" key={fact}>{fact}</li>)}</ul></div>
    {(item.predicted === "UNRESOLVED" || !item.correct) && <div className="rounded-lg border border-indigo-100 bg-indigo-50 p-3 text-xs leading-5 text-indigo-900 md:col-span-2"><strong>Operational Copilot boundary:</strong> benchmark records are isolated and are not available to PayOps AI tools. <Link className="font-semibold underline underline-offset-2" href="/copilot?source=all">Open the operational Copilot</Link> only to investigate real demo or Razorpay records.</div>}
  </div>;
}

export function EvaluationAudit({ benchmarks }: { benchmarks: EvaluationBenchmark[] }) {
  const [resultFilter, setResultFilter] = useState<ResultFilter>("all");
  const [benchmarkFilter, setBenchmarkFilter] = useState<BenchmarkFilter>("all");
  const cases = useMemo(() => benchmarks.flatMap((benchmark) => benchmark.cases).filter((item) => {
    if (benchmarkFilter !== "all" && item.benchmark !== benchmarkFilter) return false;
    if (resultFilter === "correct") return item.correct;
    if (resultFilter === "unresolved") return item.predicted === "UNRESOLVED";
    if (resultFilter === "mismatches") return !item.correct;
    return true;
  }), [benchmarks, benchmarkFilter, resultFilter]);
  return <>
    <div className="grid gap-5 xl:grid-cols-2">{benchmarks.map((benchmark) => <BenchmarkCard benchmark={benchmark} key={benchmark.key} />)}</div>
    <section aria-labelledby="audit-table-title" className="mt-7 rounded-xl border border-slate-200 bg-white shadow-card">
      <div className="border-b border-slate-100 p-5"><h2 className="text-xl font-semibold" id="audit-table-title">Case audit</h2><p className="mt-1 text-sm text-slate-500">Compare known ground truth with deterministic output. Expand any row for reasons and summarized evidence.</p>
        <div className="mt-4 flex flex-wrap gap-4"><fieldset><legend className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Result</legend><div className="flex flex-wrap gap-1" role="group">{(["all","correct","unresolved","mismatches"] as ResultFilter[]).map(value => <button aria-pressed={resultFilter === value} className={`rounded-md px-3 py-1.5 text-xs font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand ${resultFilter === value ? "bg-brand text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`} key={value} onClick={() => setResultFilter(value)} type="button">{label(value)}</button>)}</div></fieldset>
        <fieldset><legend className="mb-1.5 text-[11px] font-semibold uppercase tracking-wide text-slate-500">Benchmark</legend><div className="flex flex-wrap gap-1" role="group">{(["all","specification","robustness"] as BenchmarkFilter[]).map(value => <button aria-pressed={benchmarkFilter === value} className={`rounded-md px-3 py-1.5 text-xs font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand ${benchmarkFilter === value ? "bg-ink text-white" : "bg-slate-100 text-slate-700 hover:bg-slate-200"}`} key={value} onClick={() => setBenchmarkFilter(value)} type="button">{value === "all" ? "All" : value === "specification" ? "A · Specification" : "B · Robustness"}</button>)}</div></fieldset></div>
      </div>
      <p aria-live="polite" className="px-5 pt-4 text-xs text-slate-500">Showing {cases.length} of {benchmarks.reduce((total, benchmark) => total + benchmark.cases.length, 0)} cases</p>
      <div className="divide-y divide-slate-100 p-3 sm:p-5">{cases.map(item => <details className="group" key={`${item.benchmark}-${item.case_id}`}><summary className="grid cursor-pointer list-none gap-2 rounded-lg px-3 py-3 hover:bg-slate-50 focus-visible:outline focus-visible:outline-2 focus-visible:outline-brand md:grid-cols-[110px_100px_1fr_1fr_160px] md:items-center"><code className="text-xs font-semibold text-ink">{item.case_id}</code><span className="text-xs text-slate-500">{item.benchmark === "specification" ? "A · Spec" : "B · Robust"}</span><span className="text-xs"><span className="text-slate-400">Expected </span><strong>{label(item.expected)}</strong></span><span className="text-xs"><span className="text-slate-400">Predicted </span><strong>{label(item.predicted)}</strong></span><span className={`w-fit rounded-full border px-2.5 py-1 text-xs font-semibold ${statusStyle[item.display_status]}`}>{statusLabel[item.display_status]} <span aria-hidden="true">⌄</span></span></summary><CaseDetails item={item}/></details>)}</div>
    </section>
  </>;
}
