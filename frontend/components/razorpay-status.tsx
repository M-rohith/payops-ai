"use client";

import { useEffect, useState } from "react";

type Status = { configured: boolean; reachable: boolean; mode: string };

export function RazorpayStatus() {
  const [status, setStatus] = useState<Status | null>(null);
  useEffect(() => { fetch("/api/integrations/razorpay/status").then(response => response.json()).then(setStatus).catch(() => setStatus({ configured: false, reachable: false, mode: "unknown" })); }, []);
  return <div className="mb-4 flex justify-end"><div className="flex items-center gap-2 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs text-slate-600 shadow-sm"><span className={`h-2 w-2 rounded-full ${status?.reachable && status.mode === "test" ? "bg-emerald-500" : "bg-slate-300"}`}/><span>Razorpay Test Mode</span><strong className={status?.reachable ? "text-emerald-700" : "text-slate-500"}>{status === null ? "Checking" : status.reachable && status.mode === "test" ? "Connected" : "Not connected"}</strong></div></div>;
}
