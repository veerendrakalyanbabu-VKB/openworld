"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  api,
  DEFAULT_OPERATOR_AGENT_ID,
  type Agent,
  type Action,
  type AuditEvent,
  type TrustScenario,
} from "@/lib/api";
import {
  FlaskConical,
  Play,
  Shield,
  ShieldAlert,
  ShieldCheck,
} from "lucide-react";
import { StatusBadge } from "@/components/ui/StatusBadge";

interface SimulationResult {
  simulation?: boolean;
  label?: string;
  identity?: {
    valid: boolean;
    reasons: string[];
  };
  capability?: {
    permitted: boolean;
    reasons: string[];
    missing_capabilities?: string[];
  };
  policy?: {
    decision: string;
    policy_name?: string;
    reasons: string[];
  };
  risk?: {
    risk_level: string;
    risk_score: number;
    reasons: string[];
  };
  predicted_outcome?: string;
  agent?: string;
  action?: string;
  error?: string;
}

const STAGE_LABELS: Record<string, string> = {
  requested: "Request",
  identity: "Identity",
  policy: "Policy",
  risk: "Risk",
  approval: "Approval",
  execution: "Execution",
  verification: "Verification",
  complete: "Complete",
};

function TrustChainTable({
  stages,
}: {
  stages: Action["stages"];
}) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-ow-text-dim border-b border-ow-border-subtle">
            <th className="text-left py-2 pr-3">Stage</th>
            <th className="text-left py-2 pr-3">Status</th>
            <th className="text-left py-2">Evidence</th>
          </tr>
        </thead>

        <tbody>
          {stages.map((stage, index) => (
            <tr
              key={index}
              className="border-b border-ow-border-subtle/50"
            >
              <td className="py-2 pr-3 font-mono text-ow-accent">
                {STAGE_LABELS[stage.stage] ?? stage.stage}
              </td>

              <td className="py-2 pr-3">
                <StatusBadge status={stage.status} />
              </td>

              <td className="py-2 text-ow-text-muted">
                {stage.evidence?.length > 0
                  ? stage.evidence.join("; ")
                  : "—"}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function AuditEvidenceTable({
  events,
}: {
  events: AuditEvent[];
}) {
  if (events.length === 0) {
    return (
      <p className="text-xs text-ow-text-dim">
        No audit events found for this action.
      </p>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-xs">
        <thead>
          <tr className="text-ow-text-dim border-b border-ow-border-subtle">
            <th className="text-left py-2 pr-3">Event</th>
            <th className="text-left py-2 pr-3">Decision</th>
            <th className="text-left py-2 pr-3">Outcome</th>
            <th className="text-left py-2">Reason</th>
          </tr>
        </thead>

        <tbody>
          {events.map((event) => (
            <tr
              key={event.id}
              className="border-b border-ow-border-subtle/50"
            >
              <td className="py-2 pr-3 font-mono">
                {event.event_type.replace(/_/g, " ")}
              </td>

              <td className="py-2 pr-3">
                {event.decision ? (
                  <StatusBadge status={event.decision} />
                ) : (
                  "—"
                )}
              </td>

              <td className="py-2 pr-3">
                {String(
                  event.details?.final_outcome ?? "—"
                )}
              </td>

              <td className="py-2 text-ow-text-muted">
                {String(event.details?.reason ?? "—")}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function SimulationPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [scenarios, setScenarios] =
    useState<TrustScenario[]>([]);

  const [selectedAgent, setSelectedAgent] =
    useState("");

  const [action, setAction] =
    useState("payment.create");

  const [amount, setAmount] =
    useState("10000");

  const [simResult, setSimResult] =
    useState<SimulationResult | null>(null);

  const [execResult, setExecResult] =
    useState<Action | null>(null);

  const [auditEvents, setAuditEvents] =
    useState<AuditEvent[]>([]);

  const [loading, setLoading] =
    useState(false);

  const [executing, setExecuting] =
    useState(false);

  const [mode, setMode] =
    useState<"simulate" | "execute">(
      "simulate"
    );

  const [error, setError] =
    useState<string | null>(null);

  /*
   * Production authentication state.
   *
   * The bootstrap credential lives only in component memory.
   * It is cleared after successful authentication.
   */
  const [bootstrapToken, setBootstrapToken] =
    useState("");

  const [authenticating, setAuthenticating] =
    useState(false);

  const [
    authenticatedAgent,
    setAuthenticatedAgent,
  ] = useState<string | null>(null);

  useEffect(() => {
    api
      .agents()
      .then((data) => {
        setAgents(data.agents);

        if (data.agents.length > 0) {
          setSelectedAgent(data.agents[0].id);
        }
      })
      .catch(() =>
        setError(
          "Cannot reach the OpenWorld API."
        )
      );

    api
      .scenarios()
      .then((data) =>
        setScenarios(data.scenarios)
      )
      .catch(() => {});
  }, []);

  /*
   * If the operator manually switches agents,
   * require authentication for that agent.
   */
  const handleAgentChange = (
    agentId: string
  ) => {
    setSelectedAgent(agentId);
    setAuthenticatedAgent(
      api.hasProductionToken(agentId)
        ? agentId
        : null
    );

    setError(null);
    setExecResult(null);
    setSimResult(null);
  };

  const scenarioParams = (
    scenario: TrustScenario
  ) =>
    scenario.action.includes("email")
      ? {
          to: "demo@example.com",
          subject: "Demo",
        }
      : scenario.parameters;

  const loadScenario = (
    scenario: TrustScenario
  ) => {
    setSelectedAgent(scenario.agent_id);
    setAction(scenario.action);

    setAmount(
      String(
        scenario.parameters.amount ?? ""
      )
    );

    setAuthenticatedAgent(
      api.hasProductionToken(
        scenario.agent_id
      )
        ? scenario.agent_id
        : null
    );

    setSimResult(null);
    setExecResult(null);
    setAuditEvents([]);
    setError(null);
  };

  const fetchAuditForAction = async (
    correlationId: string
  ) => {
    try {
      const data = await api.audit(
        DEFAULT_OPERATOR_AGENT_ID,
        {
          correlation_id: correlationId,
        }
      );

      setAuditEvents(data.events);
    } catch {
      setAuditEvents([]);
    }
  };

  /*
   * Production operator authentication.
   *
   * Bootstrap secret:
   * browser memory
   *      ↓
   * Next.js auth proxy
   *      ↓
   * FastAPI production bootstrap validation
   *      ↓
   * short-lived agent JWT
   *      ↓
   * sessionStorage
   */
  const authenticateOperator =
    async () => {
      if (!selectedAgent) {
        setError(
          "Select an agent before authenticating."
        );
        return;
      }

      if (!bootstrapToken.trim()) {
        setError(
          "Enter the production bootstrap token."
        );
        return;
      }

      setAuthenticating(true);
      setError(null);

      try {
        await api.authenticateProduction(
          selectedAgent,
          bootstrapToken.trim()
        );

        setAuthenticatedAgent(
          selectedAgent
        );

        /*
         * Never retain the bootstrap secret
         * after the exchange succeeds.
         */
        setBootstrapToken("");
      } catch {
        setAuthenticatedAgent(null);

        setError(
          "Production authentication failed. Verify the bootstrap token and selected agent."
        );
      } finally {
        setAuthenticating(false);
      }
    };

  const runSimulation = async () => {
    if (!selectedAgent) {
      setError("Select an agent.");
      return;
    }

    setLoading(true);
    setExecResult(null);
    setAuditEvents([]);
    setMode("simulate");
    setError(null);

    try {
      const data = await api.simulate({
        agent_id: selectedAgent,
        action,
        parameters: action.includes("email")
          ? {
              to: "demo@example.com",
              subject: "Test",
            }
          : {
              amount: Number(amount),
            },
      });

      setSimResult(
        data as SimulationResult
      );
    } catch {
      setSimResult({
        error:
          "Simulation request failed.",
      });
    } finally {
      setLoading(false);
    }
  };

  const runRealAction = async (
    override?: {
      agent_id: string;
      action: string;
      parameters: Record<
        string,
        unknown
      >;
    }
  ) => {
    const payload =
      override ?? {
        agent_id: selectedAgent,
        action,
        parameters:
          action.includes("email")
            ? {
                to: "demo@example.com",
                subject: "Demo",
              }
            : {
                amount:
                  Number(amount),
              },
      };

    /*
     * Do not even attempt a protected
     * production action without an
     * authenticated session for the agent.
     */
    if (
      !api.hasProductionToken(
        payload.agent_id
      )
    ) {
      setAuthenticatedAgent(null);

      setError(
        `Authenticate ${payload.agent_id} before executing this production action.`
      );

      return;
    }

    setExecuting(true);
    setSimResult(null);
    setExecResult(null);
    setAuditEvents([]);
    setMode("execute");
    setError(null);

    try {
      const data =
        await api.createAction(payload);

      setExecResult(data.action);

      if (
        data.action.correlation_id
      ) {
        await fetchAuditForAction(
          data.action.correlation_id
        );
      }
    } catch {
      setExecResult(null);

      /*
       * api.ts clears invalid/expired JWTs
       * after a 401, so make the UI require
       * authentication again.
       */
      if (
        !api.hasProductionToken(
          payload.agent_id
        )
      ) {
        setAuthenticatedAgent(null);

        setError(
          "Production session expired or authentication was rejected. Authenticate again."
        );
      } else {
        setError(
          "Production execution failed. Check the API response and policy decision."
        );
      }
    } finally {
      setExecuting(false);
    }
  };

  const runScenarioExecute = async (
    scenario: TrustScenario
  ) => {
    loadScenario(scenario);

    if (
      !api.hasProductionToken(
        scenario.agent_id
      )
    ) {
      setError(
        `Authenticate ${scenario.agent_name} before executing this scenario.`
      );

      return;
    }

    await runRealAction({
      agent_id: scenario.agent_id,
      action: scenario.action,
      parameters:
        scenarioParams(scenario),
    });
  };

  const scenarioIcon = (
    name: string
  ) => {
    if (name === "ALLOW") {
      return (
        <ShieldCheck className="h-4 w-4 text-ow-trusted" />
      );
    }

    if (name === "DENY") {
      return (
        <ShieldAlert className="h-4 w-4 text-ow-blocked" />
      );
    }

    return (
      <Shield className="h-4 w-4 text-ow-approval" />
    );
  };

  const executionReached =
    execResult?.stages.some(
      (stage) =>
        stage.stage === "execution"
    ) ?? false;

  const selectedAgentAuthenticated =
    Boolean(selectedAgent) &&
    authenticatedAgent ===
      selectedAgent &&
    api.hasProductionToken(
      selectedAgent
    );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <FlaskConical
            className="h-6 w-6 text-ow-accent"
            strokeWidth={1.5}
          />

          Trust Flow Demo
        </h1>

        <p className="text-sm text-ow-text-muted mt-1">
          Agent → Identity → Capability →
          Policy → Risk → Decision →
          Approval → Execution →
          Verification → Audit
        </p>
      </div>

      {error && (
        <div className="px-3 py-2 rounded-lg bg-ow-blocked/10 border border-ow-blocked/20 text-sm text-ow-blocked">
          {error}
        </div>
      )}

      {scenarios.length > 0 && (
        <div className="space-y-2">
          <h2 className="text-xs text-ow-text-muted uppercase tracking-wider">
            Canonical Scenarios
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {scenarios.map(
              (scenario) => {
                const scenarioAuthenticated =
                  authenticatedAgent ===
                    scenario.agent_id &&
                  api.hasProductionToken(
                    scenario.agent_id
                  );

                return (
                  <div
                    key={scenario.name}
                    className="glass p-4 space-y-3"
                  >
                    <div className="flex items-center gap-2">
                      {scenarioIcon(
                        scenario.name
                      )}

                      <span className="text-sm font-medium">
                        {scenario.name}
                      </span>

                      <StatusBadge
                        status={
                          scenario.expected_decision
                        }
                      />
                    </div>

                    <p className="text-xs text-ow-text-muted">
                      {
                        scenario.description
                      }
                    </p>

                    <p className="text-[10px] text-ow-text-dim font-mono">
                      {scenario.agent_name} →{" "}
                      {scenario.action}
                    </p>

                    <div className="flex gap-2">
                      <button
                        onClick={() =>
                          loadScenario(
                            scenario
                          )
                        }
                        className="btn-secondary text-xs flex-1"
                      >
                        Load
                      </button>

                      <button
                        onClick={() =>
                          runScenarioExecute(
                            scenario
                          )
                        }
                        disabled={
                          executing ||
                          !scenarioAuthenticated
                        }
                        className="btn-primary text-xs flex-1 flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
                        title={
                          scenarioAuthenticated
                            ? "Execute scenario"
                            : `Authenticate ${scenario.agent_name} first`
                        }
                      >
                        <Play className="h-3 w-3" />

                        Execute
                      </button>
                    </div>
                  </div>
                );
              }
            )}
          </div>
        </div>
      )}

      <div className="px-3 py-1.5 rounded-full bg-ow-approval/10 border border-ow-approval/20 inline-flex">
        <span className="text-[11px] font-medium text-ow-approval uppercase tracking-wide">
          DEMO / SYNTHETIC — Execution uses
          mock executors
        </span>
      </div>

      <div className="glass p-5 space-y-4 max-w-lg">
        <div className="space-y-3">
          <div>
            <p className="text-xs text-ow-text-muted uppercase tracking-wider">
              Production Operator
              Authentication
            </p>

            <p className="text-[11px] text-ow-text-dim mt-1">
              Authenticate an agent before
              executing protected production
              actions. The bootstrap credential
              is not retained after successful
              exchange.
            </p>
          </div>

          <input
            type="password"
            value={bootstrapToken}
            onChange={(event) =>
              setBootstrapToken(
                event.target.value
              )
            }
            placeholder="Enter production bootstrap token"
            autoComplete="off"
            spellCheck={false}
            className="input-field"
          />

          <button
            type="button"
            onClick={
              authenticateOperator
            }
            disabled={
              authenticating ||
              !selectedAgent ||
              !bootstrapToken.trim()
            }
            className="btn-secondary w-full disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {authenticating
              ? "Authenticating..."
              : "Authenticate Operator"}
          </button>

          <div className="text-[11px]">
            {selectedAgentAuthenticated ? (
              <span className="text-ow-trusted">
                Authenticated for this
                browser session.
              </span>
            ) : (
              <span className="text-ow-text-dim">
                Authentication required
                before protected execution.
              </span>
            )}
          </div>
        </div>

        <div>
          <label className="text-xs text-ow-text-muted uppercase tracking-wider">
            Agent
          </label>

          <select
            value={selectedAgent}
            onChange={(event) =>
              handleAgentChange(
                event.target.value
              )
            }
            className="input-field mt-1"
          >
            {agents.map((agent) => (
              <option
                key={agent.id}
                value={agent.id}
              >
                {agent.name} (
                {agent.status})
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="text-xs text-ow-text-muted uppercase tracking-wider">
            Action
          </label>

          <select
            value={action}
            onChange={(event) =>
              setAction(
                event.target.value
              )
            }
            className="input-field mt-1"
          >
            <option value="email.send">
              email.send
            </option>

            <option value="payment.create">
              payment.create
            </option>

            <option value="invoice.send">
              invoice.send
            </option>

            <option value="database.write">
              database.write
            </option>
          </select>
        </div>

        {!action.includes("email") && (
          <div>
            <label className="text-xs text-ow-text-muted uppercase tracking-wider">
              Amount (₹)
            </label>

            <input
              type="number"
              value={amount}
              onChange={(event) =>
                setAmount(
                  event.target.value
                )
              }
              className="input-field mt-1"
            />
          </div>
        )}

        <div className="flex gap-2">
          <button
            onClick={runSimulation}
            disabled={loading}
            className="btn-secondary flex-1"
          >
            {loading
              ? "Simulating..."
              : "Simulate (dry-run)"}
          </button>

          <button
            onClick={() =>
              runRealAction()
            }
            disabled={
              executing ||
              !selectedAgentAuthenticated
            }
            className="btn-primary flex-1 flex items-center justify-center gap-1 disabled:opacity-50 disabled:cursor-not-allowed"
            title={
              selectedAgentAuthenticated
                ? "Execute through production trust pipeline"
                : "Authenticate the selected agent first"
            }
          >
            <Play className="h-3.5 w-3.5" />

            {executing
              ? "Executing..."
              : "Execute (real pipeline)"}
          </button>
        </div>
      </div>

      {simResult &&
        mode === "simulate" && (
          <div className="glass p-5 space-y-4 max-w-2xl">
            <h3 className="text-sm font-medium">
              Simulation Result{" "}
              <span className="text-ow-text-dim text-xs">
                (no execution)
              </span>
            </h3>

            {simResult.error ? (
              <p className="text-ow-blocked text-sm">
                {simResult.error}
              </p>
            ) : (
              <div className="grid grid-cols-2 gap-3 text-sm">
                {simResult.identity && (
                  <div>
                    <span className="text-xs text-ow-text-muted">
                      Identity:
                    </span>{" "}

                    <StatusBadge
                      status={
                        simResult.identity
                          .valid
                          ? "verified"
                          : "denied"
                      }
                    />
                  </div>
                )}

                {simResult.capability && (
                  <div>
                    <span className="text-xs text-ow-text-muted">
                      Capability:
                    </span>{" "}

                    <StatusBadge
                      status={
                        simResult
                          .capability
                          .permitted
                          ? "allow"
                          : "deny"
                      }
                    />
                  </div>
                )}

                {simResult.policy && (
                  <div>
                    <span className="text-xs text-ow-text-muted">
                      Policy:
                    </span>{" "}

                    <StatusBadge
                      status={
                        simResult.policy
                          .decision
                      }
                    />
                  </div>
                )}

                {simResult.risk && (
                  <div>
                    <span className="text-xs text-ow-text-muted">
                      Risk:
                    </span>{" "}

                    <StatusBadge
                      status={
                        simResult.risk
                          .risk_level
                      }
                    />
                  </div>
                )}

                {simResult.predicted_outcome && (
                  <div className="col-span-2">
                    <span className="text-xs text-ow-text-muted">
                      Decision:
                    </span>{" "}

                    <StatusBadge
                      status={
                        simResult.predicted_outcome
                      }
                    />
                  </div>
                )}
              </div>
            )}
          </div>
        )}

      {execResult &&
        mode === "execute" && (
          <div className="glass p-5 space-y-4 max-w-3xl">
            <h3 className="text-sm font-medium">
              Pipeline Result

              <span className="text-ow-text-dim text-xs ml-2">
                ID:{" "}
                {execResult.id.slice(
                  0,
                  8
                )}
                …
              </span>
            </h3>

            <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
              <div>
                <span className="text-xs text-ow-text-muted block">
                  Agent
                </span>

                {execResult.agent_name}
              </div>

              <div>
                <span className="text-xs text-ow-text-muted block">
                  Status
                </span>

                <StatusBadge
                  status={
                    execResult.status
                  }
                />
              </div>

              <div>
                <span className="text-xs text-ow-text-muted block">
                  Policy
                </span>

                {execResult.policy_decision ? (
                  <StatusBadge
                    status={
                      execResult
                        .policy_decision
                        .decision
                    }
                  />
                ) : (
                  "—"
                )}
              </div>

              <div>
                <span className="text-xs text-ow-text-muted block">
                  Risk
                </span>

                {execResult.risk_level ? (
                  <StatusBadge
                    status={
                      execResult.risk_level
                    }
                  />
                ) : (
                  "—"
                )}
              </div>

              <div>
                <span className="text-xs text-ow-text-muted block">
                  Execution
                </span>

                <StatusBadge
                  status={
                    executionReached
                      ? "executed"
                      : "blocked"
                  }
                />
              </div>

              <div>
                <span className="text-xs text-ow-text-muted block">
                  Verification
                </span>

                <StatusBadge
                  status={
                    execResult.stages.find(
                      (stage) =>
                        stage.stage ===
                        "verification"
                    )?.status ??
                    "pending"
                  }
                />
              </div>
            </div>

            <div>
              <h4 className="text-xs text-ow-text-muted uppercase tracking-wider mb-2">
                Trust Chain (backend
                stages)
              </h4>

              <TrustChainTable
                stages={
                  execResult.stages
                }
              />
            </div>

            {auditEvents.length > 0 && (
              <div>
                <h4 className="text-xs text-ow-text-muted uppercase tracking-wider mb-2">
                  Audit Evidence
                  (backend)
                </h4>

                <AuditEvidenceTable
                  events={auditEvents}
                />
              </div>
            )}

            {execResult.status ===
              "pending_approval" && (
              <Link
                href="/approvals"
                className="btn-approve inline-flex text-sm"
              >
                Go to Approval Queue →
              </Link>
            )}

            <Link
              href="/audit"
              className="text-xs text-ow-accent hover:underline block"
            >
              View full audit trail →
            </Link>
          </div>
        )}
    </div>
  );
}
