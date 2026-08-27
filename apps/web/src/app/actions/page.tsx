import Link from "next/link";
import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

const stageIcons: Record<string, string> = {
  requested: "○",
  identity: "◉",
  policy: "◈",
  risk: "△",
  approval: "◎",
  execution: "▶",
  verification: "✓",
  complete: "●",
};

export default async function ActionsPage() {
  let actions: Awaited<ReturnType<typeof api.actions>>["actions"] = [];
  try {
    ({ actions } = await api.actions({ limit: "50" }));
  } catch { /* API offline */ }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Action Center</h1>
        <p className="text-sm text-ow-text-muted mt-1">Full lifecycle timeline for every agent action</p>
      </div>

      <div className="space-y-4">
        {actions.length === 0 ? (
          <div className="glass p-8 text-center text-ow-text-dim">No actions recorded</div>
        ) : (
          actions.map((action) => (
            <Link key={action.id} href={`/actions/${action.id}`} className="glass p-5 block hover:bg-ow-surface-elevated/20">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-semibold text-ow-text">{action.agent_name}</span>
                    <span className="text-ow-text-dim">→</span>
                    <span className="text-sm text-ow-accent font-mono">{action.action}</span>
                  </div>
                  {action.target && <p className="text-xs text-ow-text-muted mt-0.5">Target: {action.target}</p>}
                </div>
                <div className="flex items-center gap-3">
                  {action.risk_level && <StatusBadge status={action.risk_level} />}
                  <StatusBadge status={action.status} />
                </div>
              </div>

              <div className="flex items-center gap-1 overflow-x-auto py-2">
                {action.stages.map((stage, i) => (
                  <div key={i} className="flex items-center gap-1 shrink-0">
                    <div className={`flex flex-col items-center px-3 py-2 rounded-lg text-center min-w-[80px] ${
                      stage.status === "completed" || stage.status === "verified" || stage.status === "approved"
                        ? "bg-ow-trusted/10"
                        : stage.status === "blocked" || stage.status === "denied" || stage.status === "failed"
                        ? "bg-ow-blocked/10"
                        : stage.status === "pending"
                        ? "bg-ow-approval/10"
                        : "bg-ow-surface-elevated/50"
                    }`}>
                      <span className="text-xs text-ow-text-dim">{stageIcons[stage.stage] || "·"}</span>
                      <span className="text-[10px] text-ow-text-muted uppercase mt-1">{stage.stage}</span>
                      <span className="text-[10px] text-ow-text-dim">{stage.status}</span>
                    </div>
                    {i < action.stages.length - 1 && (
                      <div className="w-4 h-px bg-ow-border" />
                    )}
                  </div>
                ))}
              </div>

              {action.policy_decision && (
                <div className="mt-3 p-3 rounded-lg bg-ow-bg/50 text-xs">
                  <span className="text-ow-text-muted">Policy: </span>
                  <span className="text-ow-text">{action.policy_decision.policy_name}</span>
                  <span className="text-ow-text-dim"> — </span>
                  <span className="text-ow-accent">{action.policy_decision.decision}</span>
                  {action.policy_decision.reasons.length > 0 && (
                    <p className="text-ow-text-dim mt-1">{action.policy_decision.reasons.join("; ")}</p>
                  )}
                </div>
              )}

              <div className="flex items-center justify-between mt-3 text-xs text-ow-text-dim">
                <span className="font-mono">{action.id.slice(0, 8)}...</span>
                <time>{formatDate(action.created_at)}</time>
              </div>
            </Link>
          ))
        )}
      </div>
    </div>
  );
}
