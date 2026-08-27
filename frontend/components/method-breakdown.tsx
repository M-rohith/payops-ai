import type { PaymentMethodMetric } from "@/lib/api";

const colors: Record<string, string> = { upi: "#2f5bea", card: "#7c3aed", netbanking: "#06b6d4", wallet: "#f59e0b" };
export function MethodBreakdown({ methods }: { methods: PaymentMethodMetric[] }) {
  const total = methods.reduce((sum, item) => sum + item.payment_count, 0);
  const gradient = methods.map((item, index) => {
    const preceding = methods.slice(0, index).reduce((sum, entry) => sum + entry.payment_count, 0);
    const start = total ? preceding / total * 100 : 0;
    const end = total ? (preceding + item.payment_count) / total * 100 : 0;
    return `${colors[item.method]} ${start}% ${end}%`;
  }).join(", ");
  return <section className="rounded-xl border border-slate-200 bg-white p-5 shadow-card"><h2 className="font-semibold">Payment Method Breakdown</h2><p className="mt-1 text-sm text-slate-500">All attempts in the last 30 days</p>{total ? <div className="mt-6 flex items-center gap-8"><div className="grid h-36 w-36 shrink-0 place-items-center rounded-full" style={{ background: `conic-gradient(${gradient})` }}><div className="grid h-20 w-20 place-items-center rounded-full bg-white text-center"><div><p className="text-xl font-semibold">{total}</p><p className="text-[10px] text-slate-400">PAYMENTS</p></div></div></div><div className="flex-1 space-y-3">{methods.map(item => <div className="flex items-center justify-between text-sm" key={item.method}><span className="flex items-center gap-2 capitalize"><i className="h-2.5 w-2.5 rounded-full" style={{ background: colors[item.method] }}/>{item.method}</span><span className="font-semibold">{Math.round(item.payment_count / total * 100)}%</span></div>)}</div></div> : <div className="grid h-44 place-items-center text-sm text-slate-500">No payment-method data for this source.</div>}</section>;
}
