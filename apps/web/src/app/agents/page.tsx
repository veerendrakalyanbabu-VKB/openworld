import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import Link from "next/link";
import { Bot } from "lucide-react";

export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  let agents: Awaited<ReturnType<typeof api.agents>>["agents"] = [];
  try {
    ({ agents } = await api.agents());
  } catch { /* API offline */ }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold">Agent Universe</h1>
          <p className="text-sm text-ow-text-muted mt-1">{agents.length} agents registered</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {agents.map((agent) => {
          const trust = agent.trust_dimensions;
          const score = (
            trust.identity * 0.2 + trust.policy * 0.25 + trust.reliability * 0.2 +
            trust.verification * 0.2 + trust.violations * 0.15
          ).toFixed(1);

          return (
            <Link key={agent.id} href={`/agents/${agent.id}`} className="glass p-5 hover:border-ow-accent/30 transition-colors group">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-ow-accent/10">
                    <Bot className="h-5 w-5 text-ow-accent" strokeWidth={1.5} />
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-ow-text group-hover:text-ow-accent transition-colors">{agent.name}</h3>
                    <p className="text-xs text-ow-text-dim">{agent.owner}</p>
                  </div>
                </div>
                <StatusBadge status={agent.status} />
              </div>
              <p className="text-xs text-ow-text-muted mb-4 line-clamp-2">{agent.description}</p>
              <div className="flex items-center justify-between">
                <div className="flex flex-wrap gap-1">
                  {agent.capabilities.slice(0, 3).map((cap) => (
                    <span key={cap} className="text-[10px] px-1.5 py-0.5 rounded bg-ow-bg text-ow-text-dim font-mono">{cap}</span>
                  ))}
                  {agent.capabilities.length > 3 && (
                    <span className="text-[10px] text-ow-text-dim">+{agent.capabilities.length - 3}</span>
                  )}
                </div>
                <span className="text-lg font-semibold text-ow-accent tabular-nums">{score}</span>
              </div>
            </Link>
          );
        })}
      </div>
    </div>
  );
}
