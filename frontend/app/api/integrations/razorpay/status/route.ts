import { NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET() {
  const response = await fetch(`${backendUrl}/api/integrations/razorpay/status`, { cache: "no-store" });
  return NextResponse.json(await response.json(), { status: response.status });
}
