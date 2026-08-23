import { NextRequest, NextResponse } from "next/server";

const API_URL =
  process.env.OPENWORLD_API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000";

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();

    const agentId = body?.agent_id;
    const bootstrapToken = body?.bootstrap_token;

    if (!agentId || typeof agentId !== "string") {
      return NextResponse.json(
        { detail: "agent_id is required" },
        { status: 400 }
      );
    }

    if (!bootstrapToken || typeof bootstrapToken !== "string") {
      return NextResponse.json(
        { detail: "bootstrap_token is required" },
        { status: 401 }
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
      headers: {
        "Cache-Control": "no-store",
      },
    });
  } catch {
    return NextResponse.json(
      { detail: "Authentication bridge failed" },
      { status: 500 }
    );
  }
}
