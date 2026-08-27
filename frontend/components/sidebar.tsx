const navigation = [
  ["Overview", "/"],
  ["Payments", "/payments"],
  ["Settlements", "/settlements"],
  ["Reconciliation", "/reconciliation"],
  ["Alerts", "/alerts"],
  ["PayOps AI", "/copilot"],
];

export function Sidebar() {
  return (
    <aside className="flex w-full flex-col bg-ink px-5 py-6 text-white md:min-h-screen md:w-64">
      <div className="mb-8 flex items-center gap-3 px-2">
        <div className="grid h-9 w-9 place-items-center rounded-lg bg-brand font-bold">P</div>
        <div>
          <div className="font-semibold tracking-tight">PayOps AI</div>
          <div className="text-xs text-slate-400">Operations copilot</div>
        </div>
      </div>
      <nav className="grid grid-cols-2 gap-1 md:grid-cols-1" aria-label="Primary navigation">
        {navigation.map(([item, href], index) => (
          <a
            className={`rounded-lg px-3 py-2.5 text-sm transition-colors ${
              index === 0 ? "bg-white/10 font-medium text-white" : "text-slate-400 hover:bg-white/5 hover:text-white"
            }`}
            href={href}
            key={item}
          >
            {item}
          </a>
        ))}
      </nav>
      <div className="mt-auto hidden rounded-lg border border-white/10 p-3 text-xs leading-5 text-slate-400 md:block">
        Phase 2 · Demo operations data
      </div>
    </aside>
  );
}
