"use client";

import { useEffect, useMemo, useState } from "react";
import type { DataSource, VolumePoint } from "@/lib/api";
import { formatMoney } from "@/lib/format";

export function VolumeChart({ initial, source }: { initial: VolumePoint[]; source: DataSource }) {
  const [range, setRange] = useState("7D"); const [points, setPoints] = useState(initial); const [loading, setLoading] = useState(false);
  useEffect(() => { fetch(`/api/dashboard/volume?time_range=${range}&source=${source}`).then(r => r.json()).then(setPoints).finally(() => setLoading(false)); }, [range, source]);
  const path = useMemo(() => { const max = Math.max(...points.map(p => p.amount), 1); return points.map((p, i) => `${(i / Math.max(points.length - 1, 1)) * 700},${190 - (p.amount / max) * 150}`).join(" "); }, [points]);
  const total = points.reduce((sum, point) => sum + point.amount, 0);
  return <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-card"><div className="flex items-start justify-between gap-4"><div><h2 className="font-semibold">Payment Volume Over Time</h2><p className="mt-1 text-sm text-slate-500">{formatMoney(total, true)} captured in this period</p></div><div className="flex rounded-lg bg-slate-100 p-1">{["1D", "7D", "30D"].map(value => <button className={`rounded-md px-3 py-1.5 text-xs font-semibold ${range === value ? "bg-white text-brand shadow-sm" : "text-slate-500"}`} key={value} onClick={() => { setLoading(true); setRange(value); }}>{value}</button>)}</div></div><div className={`mt-6 h-52 transition-opacity ${loading ? "opacity-40" : "opacity-100"}`}><svg aria-label="Payment volume line chart" className="h-full w-full" preserveAspectRatio="none" viewBox="0 0 700 210"><defs><linearGradient id="area" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor="#2f5bea" stopOpacity=".25"/><stop offset="1" stopColor="#2f5bea" stopOpacity="0"/></linearGradient></defs><line stroke="#e2e8f0" x1="0" x2="700" y1="190" y2="190"/><polygon fill="url(#area)" points={`0,190 ${path} 700,190`}/><polyline fill="none" points={path} stroke="#2f5bea" strokeLinecap="round" strokeLinejoin="round" strokeWidth="3"/></svg></div></section>;
}
