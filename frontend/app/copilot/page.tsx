import { CopilotChat } from "@/components/copilot-chat";
import { PageHeader } from "@/components/page-header";
import type { DataSource } from "@/lib/api";

export default async function CopilotPage({ searchParams }: { searchParams: Promise<{ source?: string; question?: string }> }) {
  const params = await searchParams;
  const source: DataSource = params.source === "all" || params.source === "razorpay" ? params.source : "demo";
  const question = (params.question ?? "").slice(0, 2000);
  return <><PageHeader eyebrow="CONTROLLED AI TOOLS" title="PayOps AI" description="Investigate payment operations using evidence from approved, read-only backend tools."/><div className="mt-6"><CopilotChat initialQuestion={question} initialSource={source}/></div></>;
}
