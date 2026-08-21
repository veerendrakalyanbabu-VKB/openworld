import { api } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDate } from "@/lib/utils";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { notFound } from "next/navigation";

export const dynamic = "force-dynamic";

const PIPELINE = [
  { id: "requested", label: "Requested" },
  { id: "identity", label: "Identified" },
  { id: "capability", label: "Authorized" },
  { id: "policy", label: "Policy" },
  { id: "risk", label: "Risk evaluated" },
  { id: "decision", label: "Decision" },
  { id: "approval", label: "Approval" },
  { id: "execution", label: "Execution" },
  { id: "verification", label: "Verification" },
] as const;

export default async function ActionDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  let data: Awaited<ReturnType<typeof api.action>> | null = null;
  try {
    data = await api.action(id);
  } catch {
    notFound();
  }

  const action = data.action;
  const byStage = Object.fromEntries(action.stages.map((s) => [s.stage, s]));
  const executed = Boolean(byStage.execution && ["completed", "verified"].includes(byStage.execution.status));
  const verified = action.status === "verified";

  return (
    <div className="space-y-6">
      <Link href="/actions" className="inline-flex items-center gap-2 text-sm text-ow-text-muted hover:text-ow-accent">
        <ArrowLeft className="h-4 w-4" /> Back to Actions
      </Link>

      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold font-mono">{action.action}</h1>
          <p className="text-sm text-ow-text-muted mt-1">
            Agent {action.agent_name} · {action.id}
          </p>
        </div>
        <div className="flex items-center gap-2">
          {action.risk_level && <StatusBadge status={action.risk_level} />}
          <StatusBadge status={action.status} />
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="glass p-4">
          <p className="text-[10px] uppercase tracking-wider text-ow-text-dim">Executed</p>
          <p className="text-lg font-medium mt-1">{executed ? "Yes" : "No"}</p>
        </div>
        <div className="glass p-4">
          <p className="text-[10px] uppercase tracking-wider text-ow-text-dim">Verified</p>
          <p className="text-lg font-medium mt-1">{verified ? "Yes" : "No"}</p>
        </div>
        <div className="glass p-4">
          <p className="text-[10px] uppercase tracking-wider text-ow-text-dim">Decision</p>
          <p className="text-lg font-medium mt-1">{action.policy_decision?.decision ?? "—"}</p>
        </div>
      </div>

      <div className="glass p-5 space-y-3">
        <h2 className="text-sm font-medium">Trust pipeline</h2>
        <ol className="space-y-2">
          {PIPELINE.map((step) => {
            const record = byStage[step.id];
            return (
              <li key={step.id} className="flex items-start gap-3 rounded-lg bg-ow-bg/40 px-3 py-2">
                <span className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-ow-accent" />
                <div className="min-w-0 flex-1">
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm">{step.label}</span>
                    {record ? <StatusBadge status={record.status} /> : <span className="text-xs text-ow-text-dim">not reached</span>}
                  </div>
                  {record?.details && Object.keys(record.details).length > 0 && (
                    <p className="text-xs text-ow-text-muted mt-1 truncate">
                      {JSON.stringify(record.details)}
                    </p>
                  )}
                </div>
              </li>
            );
          })}
        </ol>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="glass p-5 space-y-2 text-sm">
          <h2 className="text-sm font-medium mb-3">Request</h2>
          <p><span className="text-ow-text-muted">Target: </span>{action.target || "—"}</p>
          <p><span className="text-ow-text-muted">Risk score: </span>{action.risk_score ?? "—"}</p>
          <p><span className="text-ow-text-muted">Created: </span>{formatDate(action.created_at)}</p>
          <pre className="mt-3 text-xs bg-ow-bg/50 p-3 rounded-lg overflow-x-auto">{JSON.stringify(action.parameters, null, 2)}</pre>
        </div>
        <div className="glass p-5 space-y-2 text-sm">
          <h2 className="text-sm font-medium mb-3">Policy</h2>
          {action.policy_decision ? (
            <>
              <p><span className="text-ow-text-muted">Name: </span>{action.policy_decision.policy_name || "—"}</p>
              <p><span className="text-ow-text-muted">Decision: </span>{action.policy_decision.decision}</p>
              <ul className="list-disc pl-5 text-ow-text-muted">
                {action.policy_decision.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            </>
          ) : (
            <p className="text-ow-text-dim">Policy was not evaluated (blocked earlier).</p>
          )}
        </div>
      </div>
    </div>
  );
}
