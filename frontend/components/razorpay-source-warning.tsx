"use client";

import { useEffect, useState } from "react";

export function RazorpaySourceWarning() {
  const [disconnected, setDisconnected] = useState(false);
  useEffect(() => { fetch("/api/integrations/razorpay/status").then(response => response.json()).then(status => setDisconnected(!(status.reachable && status.mode === "test"))).catch(() => setDisconnected(true)); }, []);
  if (!disconnected) return null;
  return <div className="mt-5 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-800">Razorpay Test Mode is currently disconnected. The dashboard is showing previously normalized local PostgreSQL data.</div>;
}
