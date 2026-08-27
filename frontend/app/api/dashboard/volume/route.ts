import { NextRequest, NextResponse } from "next/server";

const backendUrl = process.env.BACKEND_URL ?? "http://localhost:8000";

export async function GET(request: NextRequest) {
  const range = request.nextUrl.searchParams.get("time_range") ?? "7D";
  const source = request.nextUrl.searchParams.get("source") ?? "all";
  const response = await fetch(`${backendUrl}/api/dashboard/volume?time_range=${range}&source=${source}`, { cache: "no-store" });
  return NextResponse.json(await response.json(), { status: response.status });
}
