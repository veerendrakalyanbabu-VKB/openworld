const API_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const DEFAULT_OPERATOR_AGENT_ID = "agent-ops-bot";

export interface DemoAgentAuth {
  agent_id: string;
  agent_name: string;
  access_token: string;
  roles: string[];
}

/**
 * DEMO AUTHENTICATION
 * Token cache used only for local/demo development.
 * Production authentication uses a short-lived JWT stored in sessionStorage.
 */
let demoTokenCache: Record<string, string> | null = null;
let demoAgentsCache: DemoAgentAuth[] | null = null;

async function loadDemoAgents(): Promise<DemoAgentAuth[]> {
  if (demoAgentsCache) {
    return demoAgentsCache;
  }

  if (process.env.NEXT_PUBLIC_DEMO_TOKEN) {
    demoAgentsCache = [];
    demoTokenCache = {
      __default__: process.env.NEXT_PUBLIC_DEMO_TOKEN,
    };

    return demoAgentsCache;
  }

  const res = await fetch(
    `${API_URL}/api/v1/auth/demo-agents`,
    {
      cache: "no-store",
    }
  );

  if (!res.ok) {
    demoAgentsCache = [];
    demoTokenCache = {};
    return demoAgentsCache;
  }

  const data = await res.json();

  demoAgentsCache = data.agents as DemoAgentAuth[];
  demoTokenCache = {};

  for (const agent of demoAgentsCache) {
    demoTokenCache[agent.agent_id] = agent.access_token;
  }

  return demoAgentsCache;
}

/**
 * Read a production JWT for an agent.
 *
 * sessionStorage is intentionally used instead of localStorage so the
 * credential disappears when the browser session/tab is closed.
 */
function getProductionToken(
  agentId: string
): string | undefined {
  if (typeof window === "undefined") {
    return undefined;
  }

  return (
    window.sessionStorage.getItem(
      `openworld.jwt.${agentId}`
    ) ?? undefined
  );
}

function storeProductionToken(
  agentId: string,
  token: string
): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.setItem(
    `openworld.jwt.${agentId}`,
    token
  );
}

function clearProductionToken(
  agentId: string
): void {
  if (typeof window === "undefined") {
    return;
  }

  window.sessionStorage.removeItem(
    `openworld.jwt.${agentId}`
  );
}

/**
 * Exchange the operator-supplied production bootstrap credential
 * for a short-lived agent JWT.
 *
 * The bootstrap token is sent only for the authentication request and
 * is never persisted by this client.
 */
async function authenticateProduction(
  agentId: string,
  bootstrapToken: string
): Promise<void> {
  if (!agentId) {
    throw new Error("agent_id is required");
  }

  if (!bootstrapToken) {
    throw new Error("bootstrap token is required");
  }

  const res = await fetch(
    "/api/auth/token",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        agent_id: agentId,
        bootstrap_token: bootstrapToken,
      }),
      cache: "no-store",
    }
  );

  if (!res.ok) {
    throw new Error(
      `Authentication failed: ${res.status}`
    );
  }

  const data = (await res.json()) as {
    access_token?: string;
  };

  if (!data.access_token) {
  throw new Error(
    "Authentication response did not contain an access token"
  );
}

storeProductionToken(
  agentId,
  data.access_token
);
  storeProductionToken(
    agentId,
    data.access_token
  );
}

/**
 * Resolve authentication for an API request.
 *
 * Production JWTs are preferred.
 * Demo authentication is retained only as a local/demo fallback.
 */
async function getAgentToken(
  agentId: string
): Promise<string | undefined> {
  const productionToken =
    getProductionToken(agentId);

  if (productionToken) {
    return productionToken;
  }

  await loadDemoAgents();

  if (!demoTokenCache) {
    return undefined;
  }

  return (
    demoTokenCache[agentId] ??
    demoTokenCache.__default__
  );
}

async function fetchAPI<T>(
  path: string,
  options?: RequestInit & {
    agentId?: string;
    idempotencyKey?: string;
  }
): Promise<T> {
  const {
    agentId,
    idempotencyKey,
    headers: optHeaders,
    ...fetchOpts
  } = options ?? {};

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(optHeaders as
      | Record<string, string>
      | undefined),
  };

  if (agentId) {
    const token =
      await getAgentToken(agentId);

    if (token) {
      headers["Authorization"] =
        `Bearer ${token}`;
    }
  }

  if (idempotencyKey) {
    headers["Idempotency-Key"] =
      idempotencyKey;
  }

  const res = await fetch(
    `${API_URL}${path}`,
    {
      ...fetchOpts,
      headers,
      cache: "no-store",
    }
  );

  if (!res.ok) {
    /*
     * If a stored production JWT has expired or become invalid,
     * remove it so the operator can authenticate again.
     */
    if (res.status === 401 && agentId) {
      clearProductionToken(agentId);
    }

    throw new Error(
      `API error: ${res.status} ${res.statusText}`
    );
  }

  return res.json();
}

function newIdempotencyKey(): string {
  if (
    typeof crypto !== "undefined" &&
    crypto.randomUUID
  ) {
    return crypto.randomUUID();
  }

  return `idem-${Date.now()}-${Math.random()
    .toString(36)
    .slice(2)}`;
}

export const api = {
  /**
   * Local/demo only.
   */
  demoAgents: () =>
    loadDemoAgents(),

  /**
   * Production operator authentication.
   */
  authenticateProduction,

  /**
   * Remove an authenticated production session.
   */
  logoutProduction: (
    agentId: string
  ) => clearProductionToken(agentId),

  /**
   * Whether this browser session already holds
   * a JWT for the supplied agent.
   */
  hasProductionToken: (
    agentId: string
  ) =>
    Boolean(
      getProductionToken(agentId)
    ),

  /**
   * Runtime backend state.
   */
  health: () =>
    fetchAPI<{
      status: string;
      service: string;
      version: string;
      demo_mode: boolean;
      is_production?: boolean;
      environment?: string;
    }>("/api/v1/health"),

  billingAccount: (
    agentId: string
  ) =>
    fetchAPI<{
      account_id: string;
      plan_id: string;
      entitlements: Record<
        string,
        number
      >;
      usage: {
        metric: string;
        period: string;
        count: number;
      };
      payments: string;
      billing_live: boolean;
    }>(
      "/api/v1/billing/account",
      { agentId }
    ),

  stats: () =>
    fetchAPI<
      Record<string, number | boolean>
    >("/api/v1/stats"),

  agents: (
    params?: Record<string, string>
  ) => {
    const qs = params
      ? "?" +
        new URLSearchParams(
          params
        ).toString()
      : "";

    return fetchAPI<{
      agents: Agent[];
      total: number;
      demo_mode: boolean;
    }>(
      `/api/v1/agents${qs}`
    );
  },

  agent: (id: string) =>
    fetchAPI<{
      agent: Agent;
      recent_actions: Action[];
    }>(
      `/api/v1/agents/${id}`
    ),

  agentRoles: (
    id: string,
    agentId: string
  ) =>
    fetchAPI<{
      agent_id: string;
      roles: string[];
    }>(
      `/api/v1/agents/${id}/roles`,
      { agentId }
    ),

  actions: (
    params?: Record<string, string>
  ) => {
    const qs = params
      ? "?" +
        new URLSearchParams(
          params
        ).toString()
      : "";

    return fetchAPI<{
      actions: Action[];
      total: number;
    }>(
      `/api/v1/actions${qs}`
    );
  },

  action: (id: string) =>
    fetchAPI<{
      action: Action;
    }>(
      `/api/v1/actions/${id}`
    ),

  policies: () =>
    fetchAPI<{
      policies: Policy[];
      total: number;
    }>(
      "/api/v1/policies"
    ),

  approvals: (
    agentId: string
  ) =>
    fetchAPI<{
      approvals: Action[];
      total: number;
    }>(
      "/api/v1/approvals",
      { agentId }
    ),

  approve: (
    id: string,
    agentId: string
  ) =>
    fetchAPI(
      `/api/v1/approvals/${id}/approve`,
      {
        method: "POST",
        body: JSON.stringify({
          reason: "",
        }),
        agentId,
      }
    ),

  deny: (
    id: string,
    agentId: string,
    reason?: string
  ) =>
    fetchAPI(
      `/api/v1/approvals/${id}/deny`,
      {
        method: "POST",
        body: JSON.stringify({
          reason: reason || "",
        }),
        agentId,
      }
    ),

  audit: (
    agentId: string,
    params?: Record<string, string>
  ) => {
    const qs = params
      ? "?" +
        new URLSearchParams(
          params
        ).toString()
      : "";

    return fetchAPI<{
      events: AuditEvent[];
      total: number;
    }>(
      `/api/v1/audit${qs}`,
      { agentId }
    );
  },

  intelligence: (
    q: string,
    agentId?: string
  ) =>
    fetchAPI<IntelligenceResponse>(
      `/api/v1/intelligence/query?q=${encodeURIComponent(
        q
      )}`,
      agentId
        ? { agentId }
        : undefined
    ),

  simulate: (data: {
    agent_id: string;
    action: string;
    parameters?: Record<
      string,
      unknown
    >;
  }) =>
    fetchAPI(
      "/api/v1/actions/simulate",
      {
        method: "POST",
        body: JSON.stringify({
          action: data.action,
          parameters:
            data.parameters,
        }),
        agentId:
          data.agent_id,
      }
    ),

  createAction: (data: {
    agent_id: string;
    action: string;
    target?: string;
    parameters?: Record<
      string,
      unknown
    >;
    auto_approve?: boolean;
  }) =>
    fetchAPI<{
      action: Action;
      demo_mode: boolean;
    }>(
      "/api/v1/actions",
      {
        method: "POST",
        body: JSON.stringify({
          action: data.action,
          target: data.target,
          parameters:
            data.parameters,
          auto_approve:
            data.auto_approve,
        }),
        agentId:
          data.agent_id,
        idempotencyKey:
          newIdempotencyKey(),
      }
    ),

  scenarios: () =>
    fetchAPI<{
      scenarios:
        TrustScenario[];
      label: string;
    }>(
      "/api/v1/scenarios"
    ),

  verifications: () =>
    fetchAPI<{
      verifications:
        Verification[];
      total: number;
    }>(
      "/api/v1/verifications"
    ),

  demoAuthLabel:
    "DEMO AUTHENTICATION — not for production",
};

export interface Agent {
  id: string;
  name: string;
  description: string;
  owner: string;
  organization?: string;
  status: string;
  capabilities: string[];

  trust_dimensions: {
    identity: number;
    policy: number;
    reliability: number;
    verification: number;
    violations: number;
  };

  metadata?: {
    roles?: string[];
  };

  created_at: string;
}

export interface Action {
  id: string;
  agent_id: string;
  agent_name: string;
  action: string;
  target: string;

  parameters: Record<
    string,
    unknown
  >;

  status: string;

  risk_score?: number;
  risk_level?: string;
  correlation_id?: string;

  policy_decision?: {
    decision: string;
    policy_name?: string;
    reasons: string[];
  };

  stages: Array<{
    stage: string;
    status: string;
    timestamp: string;

    details: Record<
      string,
      unknown
    >;

    evidence: string[];
  }>;

  created_at: string;
}

export interface Policy {
  id: string;
  name: string;
  description: string;
  version: string;

  rules: Array<{
    id: string;
    name: string;
    agent_match?: string;
    action_match?: string;
    effect: string;

    conditions: Array<{
      field: string;
      operator: string;
      value: unknown;
    }>;

    description: string;
  }>;

  enabled: boolean;
}

export interface AuditEvent {
  id: string;
  event_type: string;
  actor: string;
  subject: string;
  action: string;
  decision: string;

  risk_level?: string;
  correlation_id?: string;

  timestamp: string;
  evidence: string[];

  details?: Record<
    string,
    unknown
  >;
}

export interface IntelligenceResponse {
  query: string;
  answer: string;
  evidence: unknown;
  evidence_based: boolean;
  demo_mode: boolean;
  access_level?: string;
  suggestions?: string[];
}

export interface TrustScenario {
  name: string;
  description: string;

  agent_id: string;
  agent_name: string;

  action: string;

  parameters: Record<
    string,
    unknown
  >;

  target: string;

  expected_decision: string;
  expected_outcome: string;
}

export interface Verification {
  id: string;
  action_id: string;
  status: string;
  expected_result: string;
  actual_result: string;
  evidence: string[];
}
