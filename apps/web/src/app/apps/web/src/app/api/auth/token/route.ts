import { NextRequest, NextResponse } from "next/server";

const API_URL =
  process.env.OPENWORLD_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const agentId = body?.agent_id;

    if (!agentId || typeof agentId !== "string") {
      return NextResponse.json(
        { detail: "agent_id is required" },
        { status: 400 }
      );
    }

    const bootstrapToken = process.env.OPENWORLD_AUTH_BOOTSTRAP_TOKEN;

    if (!bootstrapToken) {
      return NextResponse.json(
        { detail: "Production authentication bridge is not configured" },
        { status: 503 }
      );
    }

    const response = await fetch(`${API_URL}/api/v1/auth/token`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        agent_id: agentId,
        bootstrap_token: bootstrapToken,
      }),
      cache: "no-store",
    });

    const data = await response.json().catch(() => ({
      detail: "Authentication service returned an invalid response",
    }));

    return NextResponse.json(data, {
      status: response.status,
    });
  } catch {
    return NextResponse.json(
      { detail: "Authentication bridge failed" },
      { status: 500 }
    );
  }
}
