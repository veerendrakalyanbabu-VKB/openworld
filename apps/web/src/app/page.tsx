import { StatCard } from "@/components/ui/StatCard";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { TrustCore } from "@/components/trust-core/TrustCore";
import { api, DEFAULT_OPERATOR_AGENT_ID } from "@/lib/api";
import { formatDate } from "@/lib/utils";
import Link from "next/link";
import { ArrowRight, Shield } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function OverviewPage() {
  let stats: Record<string, number | boolean> = {};
  let actions: Awaited<ReturnType<typeof api.actions>>["actions"] = [];
  let approvals: Awaited<ReturnType<typeof api.approvals>>["approvals"] = [];

  try {
    [stats, { actions }, { approvals }] = await Promise.all([
      api.stats(),
      api.actions({ limit: "8" }),
      api.approvals(DEFAULT_OPERATOR_AGENT_ID),
    ]);
  } catch {
    // API may not be running during build
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-ow-text">Command Center</h1>
        <p className="text-sm text-ow-text-muted mt-1">Your AI workforce is under control.</p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard label="Trust Score" value={`${stats.avg_trust_score ?? "—"}`} variant="accent" />
        <StatCard label="Active Agents" value={Number(stats.active_agents) || 0} variant="trusted" />
        <StatCard label="Verified" value={Number(stats.verified_actions) || 0} variant="trusted" />
        <StatCard label="Blocked" value={Number(stats.blocked_actions) || 0} variant="blocked" />
        <StatCard label="Pending" value={Number(stats.pending_approvals) || 0} variant="approval" />
        <StatCard label="Audit Events" value={Number(stats.audit_events) || 0} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2">
          <TrustCore
            activeAgents={Number(stats.active_agents) || 0}
            pendingApprovals={Number(stats.pending_approvals) || 0}
            blockedActions={Number(stats.blocked_actions) || 0}
          />
        </div>

        <div className="glass p-5 space-y-4">
          <div className="flex items-center justify-between">
            <h2 className="text-sm font-medium text-ow-text">Pending Approvals</h2>
            <Link href="/approvals" className="text-xs text-ow-accent hover:underline flex items-center gap-1">
              View all <ArrowRight className="h-3 w-3" />
            </Link>
          </div>
          {approvals.length === 0 ? (
            <p className="text-sm text-ow-text-dim py-4 text-center">No pending approvals</p>
          ) : (
            <div className="space-y-3">
              {approvals.slice(0, 3).map((a) => (
                <Link key={a.id} href={`/approvals`} className="block p-3 rounded-lg bg-ow-bg/50 hover:bg-ow-surface-elevated/50 transition-colors">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium text-ow-text">{a.agent_name}</span>
                    <StatusBadge status={a.risk_level || "medium"} />
                  </div>
                  <p className="text-xs text-ow-text-muted">{a.action}</p>
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="glass p-5">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-ow-text">Recent Activity</h2>
          <Link href="/actions" className="text-xs text-ow-accent hover:underline flex items-center gap-1">
            View timeline <ArrowRight className="h-3 w-3" />
          </Link>
        </div>
        <div className="space-y-2">
          {actions.length === 0 ? (
            <p className="text-sm text-ow-text-dim py-4 text-center">No recent actions</p>
          ) : (
            actions.map((action) => (
              <div key={action.id} className="flex items-center justify-between py-2.5 px-3 rounded-lg hover:bg-ow-surface-elevated/30 transition-colors">
                <div className="flex items-center gap-3">
                  <Shield className="h-4 w-4 text-ow-text-dim" strokeWidth={1.5} />
                  <div>
                    <span className="text-sm text-ow-text">{action.agent_name}</span>
                    <span className="text-sm text-ow-text-muted"> — {action.action}</span>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={action.status} />
                  <time className="text-xs text-ow-text-dim font-mono">{formatDate(action.created_at)}</time>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
