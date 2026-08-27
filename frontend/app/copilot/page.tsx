import { CopilotChat } from "@/components/copilot-chat";
import { PageHeader } from "@/components/page-header";
import type { DataSource } from "@/lib/api";

export default async function CopilotPage({ searchParams }: { searchParams: Promise<{ source?: string }> }) {
  const requested = (await searchParams).source; const source: DataSource = requested === "all" || requested === "razorpay" ? requested : "demo";
  return <><PageHeader eyebrow="CONTROLLED AI TOOLS" title="PayOps AI" description="Investigate payment operations using evidence from approved, read-only backend tools."/><div className="mt-6"><CopilotChat initialSource={source}/></div></>;
}
