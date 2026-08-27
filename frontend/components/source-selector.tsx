import Link from "next/link";
import type { DataSource } from "@/lib/api";

const choices: Array<[DataSource, string]> = [["all", "All Data"], ["demo", "Demo Data"], ["razorpay", "Razorpay Test"]];

export function SourceSelector({ selected }: { selected: DataSource }) {
  return <div><p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-400">Data source</p><div className="inline-flex rounded-lg border border-slate-200 bg-white p-1 shadow-sm">{choices.map(([value, label]) => <Link className={`rounded-md px-3 py-1.5 text-xs font-semibold ${selected === value ? "bg-brand text-white" : "text-slate-500 hover:text-ink"}`} href={`/?source=${value}`} key={value}>{label}</Link>)}</div></div>;
}
