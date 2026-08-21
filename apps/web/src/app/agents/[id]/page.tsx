import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDate } from "@/lib/utils";
import { Bot, ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

export default async function AgentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let data: Awaited<ReturnType<typeof api.agent>> | null = null;
  try {
    data = await api.agent(id);
  } catch {
    notFound();
  }

  const { agent, recent_actions } = data;
  const trust = agent.trust_dimensions;

  return (
    <div className="space-y-6">
      <Link href="/agents" className="inline-flex items-center gap-2 text-sm text-ow-text-muted hover:text-ow-accent transition-colors">
        <ArrowLeft className="h-4 w-4" /> Back to Agents
      </Link>

      <div className="flex items-start gap-4">
        <div className="p-3 rounded-xl bg-ow-accent/10">
          <Bot className="h-8 w-8 text-ow-accent" strokeWidth={1.5} />
        </div>
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-semibold">{agent.name}</h1>
            <StatusBadge status={agent.status} />
          </div>
          <p className="text-sm text-ow-text-muted mt-1">{agent.description}</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="glass p-5 space-y-4">
          <h2 className="text-sm font-medium">Trust Dimensions</h2>
          {Object.entries(trust).map(([key, value]) => (
            <div key={key} className="space-y-1">
              <div className="flex justify-between text-xs">
                <span className="text-ow-text-muted capitalize">{key}</span>
                <span className="text-ow-text font-mono">{value}</span>
              </div>
              <div className="h-1.5 rounded-full bg-ow-bg overflow-hidden">
                <div className="h-full rounded-full bg-ow-accent transition-all" style={{ width: `${value}%` }} />
              </div>
            </div>
          ))}
        </div>

        <div className="glass p-5 space-y-3">
          <h2 className="text-sm font-medium">Capabilities</h2>
          <div className="flex flex-wrap gap-2">
            {agent.capabilities.map((cap) => (
              <span key={cap} className="text-xs px-2 py-1 rounded-lg bg-ow-bg font-mono text-ow-text-muted">{cap}</span>
            ))}
          </div>
        </div>

        <div className="glass p-5 space-y-3">
          <h2 className="text-sm font-medium">Identity</h2>
          <dl className="space-y-2 text-sm">
            <div className="flex justify-between"><dt className="text-ow-text-muted">ID</dt><dd className="font-mono text-xs">{agent.id}</dd></div>
            <div className="flex justify-between"><dt className="text-ow-text-muted">Owner</dt><dd>{agent.owner}</dd></div>
            <div className="flex justify-between"><dt className="text-ow-text-muted">Created</dt><dd>{formatDate(agent.created_at)}</dd></div>
          </dl>
        </div>
      </div>

      <div className="glass p-5">
        <h2 className="text-sm font-medium mb-4">Recent Actions</h2>
        {recent_actions.length === 0 ? (
          <p className="text-sm text-ow-text-dim text-center py-4">No actions yet</p>
        ) : (
          <div className="space-y-2">
            {recent_actions.map((action) => (
              <div key={action.id} className="flex items-center justify-between py-2 px-3 rounded-lg hover:bg-ow-surface-elevated/30">
                <span className="text-sm">{action.action}</span>
                <div className="flex items-center gap-3">
                  <StatusBadge status={action.status} />
                  <time className="text-xs text-ow-text-dim font-mono">{formatDate(action.created_at)}</time>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
