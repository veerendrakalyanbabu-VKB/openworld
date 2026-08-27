const ACTIVE_AGENT_KEY = "openworld.activeAgentId";

export const DEFAULT_AGENT_ID = "agent-ops-bot";

export function getActiveAgentId(): string {
  if (typeof window === "undefined") return DEFAULT_AGENT_ID;
  return sessionStorage.getItem(ACTIVE_AGENT_KEY) || DEFAULT_AGENT_ID;
}

export function setActiveAgentId(agentId: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(ACTIVE_AGENT_KEY, agentId);
}

export function hasRole(roles: string[] | undefined, role: string): boolean {
  if (!roles) return false;
  if (roles.includes("system_admin")) return true;
  return roles.includes(role);
}
