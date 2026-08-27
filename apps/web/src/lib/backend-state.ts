/**
 * Backend state — fetched from production health endpoint to determine
 * whether to display demo mode or production mode UI.
 *
 * This ensures the frontend accurately reflects the backend's actual state,
 * not just a hardcoded or guessed value.
 */

export interface BackendState {
  status: "healthy" | "unhealthy";
  service: string;
  version: string;
  demo_mode: boolean;
}

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function fetchBackendState(): Promise<BackendState | null> {
  try {
    const res = await fetch(`${API_URL}/api/v1/health`, {
      cache: "no-store",
    });
    if (!res.ok) {
      return null;
    }
    return (await res.json()) as BackendState;
  } catch (error) {
    console.error("[backend-state] Failed to fetch health endpoint:", error);
    return null;
  }
}
