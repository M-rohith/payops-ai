"use client";

import { FormEvent, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkBreaks from "remark-breaks";
import type { DataSource } from "@/lib/api";

type AssistantResult = {
  answer: string;
  source: DataSource;
  tools_used: string[];
  citations: Array<{ label: string }>;
  advisory: boolean;
};

type Message = { role: "user"; text: string } | { role: "assistant"; result: AssistantResult };

const sourceLabels: Record<DataSource, string> = { all: "All Data", demo: "Demo Data", razorpay: "Razorpay Test" };
const starters: Record<DataSource, string[]> = {
  demo: ["Why are UPI payments failing today?", "Why is my settlement lower than expected?", "What needs my attention right now?"],
  razorpay: ["What happened with my recent payments?", "Show my recent failed payments.", "Do I have any settlement data?"],
  all: ["What needs my attention right now?", "Why are payments failing?", "Summarize payment operations."],
};
const toolLabels: Record<string, string> = {
  get_dashboard_summary: "Dashboard summary",
  get_payment_failure_stats: "Payment failure stats",
  get_failure_reason_breakdown: "Failure reason breakdown",
  compare_failure_rates: "Failure-rate comparison",
  get_failed_payments: "Failed payments",
  get_settlement_variance: "Settlement variance",
  get_reconciliation_issues: "Reconciliation issues",
  get_alerts: "Operational alerts",
  get_payment_details: "Payment details",
};

function AssistantMarkdown({ children }: { children: string }) {
  return (
    <div className="text-sm leading-7 text-slate-700 [&_a]:font-medium [&_a]:text-brand [&_a]:underline [&_a]:underline-offset-2 [&_code]:rounded [&_code]:bg-slate-200/70 [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:font-mono [&_code]:text-[0.85em] [&_code]:text-slate-800 [&_li]:my-1 [&_ol]:my-3 [&_ol]:list-decimal [&_ol]:space-y-1 [&_ol]:pl-6 [&_p]:my-3 [&_p:first-child]:mt-0 [&_p:last-child]:mb-0 [&_strong]:font-semibold [&_strong]:text-slate-900 [&_ul]:my-3 [&_ul]:list-disc [&_ul]:space-y-1 [&_ul]:pl-6">
      <ReactMarkdown remarkPlugins={[remarkBreaks]} skipHtml>{children}</ReactMarkdown>
    </div>
  );
}

export function CopilotChat({ initialSource = "demo" }: { initialSource?: DataSource }) {
  const [source, setSource] = useState<DataSource>(initialSource);
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function ask(text: string) {
    const message = text.trim();
    if (!message || loading) return;
    setMessages((current) => [...current, { role: "user", text: message }]);
    setInput("");
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/copilot/query", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ message, source }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(body.detail ?? "PayOps AI could not answer right now.");
      setMessages((current) => [...current, { role: "assistant", result: body }]);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "PayOps AI could not answer right now.");
    } finally {
      setLoading(false);
    }
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    void ask(input);
  }

  return (
    <div className="grid gap-5 xl:grid-cols-[1fr_280px]">
      <section className="flex min-h-[620px] flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-card">
        <div className="border-b border-slate-100 bg-gradient-to-r from-indigo-50 to-white px-5 py-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <h2 className="font-semibold">Operations conversation</h2>
              <p className="mt-1 text-xs text-slate-500">Evidence from {sourceLabels[source]} · read-only</p>
            </div>
            <div aria-label="Data source for future questions" className="flex rounded-lg bg-white p-1 shadow-sm" role="group">
              {(["all", "demo", "razorpay"] as DataSource[]).map((value) => (
                <button aria-pressed={source === value} className={`rounded-md px-3 py-1.5 text-xs font-semibold transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand ${source === value ? "bg-brand text-white" : "text-slate-600 hover:bg-slate-50"}`} key={value} onClick={() => setSource(value)} type="button">
                  {sourceLabels[value]}
                </button>
              ))}
            </div>
          </div>
        </div>

        <div aria-live="polite" className="flex-1 space-y-5 overflow-y-auto p-5">
          {messages.length === 0 && (
            <div className="grid h-full place-items-center text-center">
              <div>
                <div className="mx-auto grid h-12 w-12 place-items-center rounded-xl bg-indigo-100 font-bold text-brand">AI</div>
                <h3 className="mt-4 font-semibold">Ask about payment operations</h3>
                <p className="mt-2 max-w-md text-sm leading-6 text-slate-500">PayOps AI can investigate local payment, failure, settlement, alert, and reconciliation facts through controlled tools.</p>
              </div>
            </div>
          )}
          {messages.map((message, index) => message.role === "user" ? (
            <div className="ml-auto max-w-[80%] rounded-2xl rounded-br-md bg-brand px-4 py-3 text-sm leading-6 text-white" key={index}>{message.text}</div>
          ) : (
            <article className="max-w-[90%] rounded-2xl rounded-bl-md border border-slate-200 bg-slate-50 px-4 py-4" key={index}>
              <div className="mb-3 flex items-center gap-2">
                <span className="rounded-full border border-indigo-100 bg-indigo-50 px-2.5 py-1 text-[11px] font-semibold text-indigo-700">{sourceLabels[message.result.source]}</span>
              </div>
              <AssistantMarkdown>{message.result.answer}</AssistantMarkdown>
              <div className="mt-5 border-t border-slate-200 pt-3">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Evidence used</p>
                <div className="mt-2 flex flex-wrap gap-2">
                  {message.result.tools_used.map((tool) => <span className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs text-slate-600" key={tool}>{toolLabels[tool] ?? tool.replaceAll("_", " ")}</span>)}
                </div>
              </div>
            </article>
          ))}
          {loading && <div className="w-fit rounded-2xl rounded-bl-md bg-slate-100 px-4 py-3 text-sm text-slate-500">Reviewing PayOps evidence…</div>}
        </div>

        {error && <div className="mx-5 mb-3 rounded-lg border border-rose-200 bg-rose-50 px-3 py-2 text-sm text-rose-700">{error}</div>}
        <form className="flex gap-3 border-t border-slate-100 p-4" onSubmit={submit}>
          <label className="sr-only" htmlFor="copilot-question">Ask PayOps AI a question</label>
          <input className="min-w-0 flex-1 rounded-lg border border-slate-200 px-4 py-3 text-sm outline-none focus:border-brand focus:ring-2 focus:ring-indigo-100" id="copilot-question" maxLength={2000} onChange={(event) => setInput(event.target.value)} placeholder="Ask a payment-operations question…" value={input} />
          <button aria-label="Send question to PayOps AI" className="rounded-lg bg-brand px-5 py-3 text-sm font-semibold text-white disabled:opacity-50" disabled={loading || input.trim().length < 2}>Send</button>
        </form>
      </section>

      <aside className="space-y-4">
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-card">
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Suggested questions</p>
          <div className="mt-3 space-y-2">
            {starters[source].map((prompt) => <button aria-label={`Ask: ${prompt}`} className="w-full rounded-lg border border-slate-200 px-3 py-2.5 text-left text-sm leading-5 text-slate-600 transition-colors hover:border-brand hover:text-brand focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-brand" key={prompt} onClick={() => void ask(prompt)} type="button">{prompt}</button>)}
          </div>
        </div>
        <div className="rounded-xl border border-blue-100 bg-blue-50 p-4 text-xs leading-5 text-blue-800">
          <strong>Read-only advisory mode</strong>
          <p className="mt-1">PayOps AI cannot capture payments, issue refunds, or modify financial records.</p>
        </div>
      </aside>
    </div>
  );
}
