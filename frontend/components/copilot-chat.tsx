"use client";

import { FormEvent, useState } from "react";
import type { DataSource } from "@/lib/api";

type AssistantResult = { answer: string; source: DataSource; tools_used: string[]; citations: Array<{ label: string }>; advisory: boolean };
type Message = { role: "user"; text: string } | { role: "assistant"; result: AssistantResult };

const sourceLabels: Record<DataSource, string> = { all: "All Data", demo: "Demo Data", razorpay: "Razorpay Test" };
const starters: Record<DataSource, string[]> = {
  demo: ["Why are UPI payments failing today?", "Why is my settlement lower than expected?", "What needs my attention right now?"],
  razorpay: ["What happened with my recent payments?", "Show my recent failed payments.", "Do I have any settlement data?"],
  all: ["What needs my attention right now?", "Why are payments failing?", "Summarize payment operations."],
};

export function CopilotChat({ initialSource = "demo" }: { initialSource?: DataSource }) {
  const [source, setSource] = useState<DataSource>(initialSource); const [input, setInput] = useState(""); const [messages, setMessages] = useState<Message[]>([]); const [loading, setLoading] = useState(false); const [error, setError] = useState("");
  async function ask(text: string) {
    const message = text.trim(); if (!message || loading) return;
    setMessages(current => [...current, { role: "user", text: message }]); setInput(""); setLoading(true); setError("");
    try {
      const response = await fetch("/api/copilot/query", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ message, source }) });
      const body = await response.json(); if (!response.ok) throw new Error(body.detail ?? "PayOps AI could not answer right now.");
      setMessages(current => [...current, { role: "assistant", result: body }]);
    } catch (reason) { setError(reason instanceof Error ? reason.message : "PayOps AI could not answer right now."); } finally { setLoading(false); }
  }
  function submit(event: FormEvent) { event.preventDefault(); void ask(input); }
  return <div className="grid gap-5 xl:grid-cols-[1fr_280px]"><section className="flex min-h-[620px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card"><div className="border-b border-slate-100 bg-gradient-to-r from-indigo-50 to-white px-5 py-4"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="font-semibold">Operations conversation</h2><p className="mt-1 text-xs text-slate-500">Evidence from {sourceLabels[source]} · read-only</p></div><div className="flex rounded-lg bg-white p-1 shadow-sm">{(["all","demo","razorpay"] as DataSource[]).map(value => <button className={`rounded-md px-3 py-1.5 text-xs font-semibold ${source === value ? "bg-brand text-white" : "text-slate-500"}`} key={value} onClick={() => setSource(value)}>{sourceLabels[value]}</button>)}</div></div></div><div className="flex-1 space-y-5 overflow-y-auto p-5">{messages.length === 0 && <div className="grid h-full place-items-center text-center"><div><div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-indigo-100 font-bold text-brand">AI</div><h3 className="mt-4 font-semibold">Ask about payment operations</h3><p className="mt-2 max-w-md text-sm leading-6 text-slate-500">PayOps AI can investigate local payment, failure, settlement, alert, and reconciliation facts through controlled tools.</p></div></div>}{messages.map((message, index) => message.role === "user" ? <div className="ml-auto max-w-[80%] rounded-2xl rounded-br-md bg-brand px-4 py-3 text-sm leading-6 text-white" key={index}>{message.text}</div> : <div className="max-w-[90%] rounded-2xl rounded-bl-md border border-slate-200 bg-slate-50 px-4 py-4" key={index}><p className="whitespace-pre-wrap text-sm leading-6 text-slate-700">{message.result.answer}</p><div className="mt-4 border-t border-slate-200 pt-3"><p className="text-[10px] font-semibold uppercase tracking-wider text-slate-400">Evidence used</p><div className="mt-2 flex flex-wrap gap-2">{message.result.tools_used.map(tool => <span className="rounded-full bg-white px-2.5 py-1 text-xs text-slate-600" key={tool}>{tool.replaceAll("_", " ")}</span>)}</div></div></div>)}{loading && <div className="w-fit rounded-2xl rounded-bl-md bg-slate-100 px-4 py-3 text-sm text-slate-500">Reviewing PayOps evidence…</div>}</div>{error && <div className="mx-5 mb-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}<form className="flex gap-3 border-t border-slate-100 p-4" onSubmit={submit}><input className="min-w-0 flex-1 rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-brand" maxLength={2000} onChange={event => setInput(event.target.value)} placeholder="Ask a payment-operations question…" value={input}/><button className="rounded-lg bg-brand px-5 py-3 text-sm font-semibold text-white disabled:opacity-50" disabled={loading || input.trim().length < 2}>Send</button></form></section><aside className="space-y-4"><div className="rounded-xl border border-slate-200 bg-white p-4 shadow-card"><p className="text-xs font-semibold uppercase tracking-wide text-slate-400">Suggested questions</p><div className="mt-3 space-y-2">{starters[source].map(prompt => <button className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-left text-sm leading-5 text-slate-600 hover:border-brand hover:text-brand" key={prompt} onClick={() => void ask(prompt)}>{prompt}</button>)}</div></div><div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-xs leading-5 text-blue-800"><strong>Read-only advisory mode</strong><p className="mt-1">PayOps AI cannot capture payments, issue refunds, or modify financial records.</p></div></aside></div>;
}
