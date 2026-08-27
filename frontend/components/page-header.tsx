export function PageHeader({ eyebrow, title, description }: { eyebrow: string; title: string; description: string }) {
  return <header className="border-b border-slate-200 pb-7"><p className="text-xs font-semibold tracking-[0.16em] text-brand">{eyebrow}</p><h1 className="mt-2 text-3xl font-semibold tracking-tight">{title}</h1><p className="mt-2 text-sm text-slate-500">{description}</p></header>;
}
