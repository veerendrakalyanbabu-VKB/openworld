import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Shield } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function PoliciesPage() {
  let policies: Awaited<ReturnType<typeof api.policies>>["policies"] = [];
  try {
    ({ policies } = await api.policies());
  } catch { /* API offline */ }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Policy Studio</h1>
        <p className="text-sm text-ow-text-muted mt-1">Deterministic rules governing agent actions</p>
      </div>

      <div className="space-y-4">
        {policies.map((policy) => (
          <div key={policy.id} className="glass p-5">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <Shield className="h-5 w-5 text-ow-accent" strokeWidth={1.5} />
                <div>
                  <h3 className="text-sm font-semibold">{policy.name}</h3>
                  <p className="text-xs text-ow-text-muted">{policy.description}</p>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-xs text-ow-text-dim font-mono">v{policy.version}</span>
                <StatusBadge status={policy.enabled ? "active" : "inactive"} />
              </div>
            </div>

            <div className="space-y-3">
              {policy.rules.map((rule) => (
                <div key={rule.id} className="p-4 rounded-lg bg-ow-bg/50 border border-ow-border-subtle">
                  <div className="text-[10px] font-medium text-ow-text-dim uppercase tracking-wider mb-2">When</div>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-2 text-sm mb-3">
                    {rule.agent_match && (
                      <div><span className="text-ow-text-muted">Agent: </span><span className="font-mono text-ow-accent">{rule.agent_match}</span></div>
                    )}
                    {rule.action_match && (
                      <div><span className="text-ow-text-muted">Action: </span><span className="font-mono text-ow-accent">{rule.action_match}</span></div>
                    )}
                    {rule.conditions.map((c, i) => (
                      <div key={i}><span className="text-ow-text-muted">Condition: </span><span className="font-mono">{c.field} {c.operator} {String(c.value)}</span></div>
                    ))}
                  </div>
                  <div className="text-[10px] font-medium text-ow-text-dim uppercase tracking-wider mb-1">Then</div>
                  <StatusBadge status={rule.effect === "require_approval" ? "pending_approval" : rule.effect === "deny" ? "blocked" : "active"} />
                  {rule.description && <p className="text-xs text-ow-text-dim mt-2">{rule.description}</p>}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
