"use client";

import { useEffect, useState } from "react";
import { api, type Action } from "@/lib/api";
import { getActiveAgentId, hasRole } from "@/lib/session";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { CheckCircle, XCircle } from "lucide-react";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<Action[]>([]);
  const [loading, setLoading] = useState(true);
  const [processing, setProcessing] = useState<string | null>(null);
  const [canOperate, setCanOperate] = useState(false);
  const [activeAgentId, setActiveAgentId] = useState(getActiveAgentId());
  const [authError, setAuthError] = useState<string | null>(null);

  const load = async () => {
    const agentId = getActiveAgentId();
    setActiveAgentId(agentId);
    const agents = await api.demoAgents();
    const active = agents.find((a) => a.agent_id === agentId);
    const allowed = hasRole(active?.roles, "operator");
    setCanOperate(allowed);
    if (!allowed) {
      setAuthError("Active identity lacks operator role. Change identity in Settings.");
      setApprovals([]);
      setLoading(false);
      return;
    }
    setAuthError(null);
    try {
      const data = await api.approvals(agentId);
      setApprovals(data.approvals);
    } catch {
      setAuthError("Unable to load approvals (401/403). Check active identity in Settings.");
    }
    setLoading(false);
  };

  useEffect(() => {
    load();
  }, []);

  const handleApprove = async (id: string) => {
    if (!canOperate) return;
    setProcessing(id);
    try {
      await api.approve(id, activeAgentId);
      await load();
    } catch {
      setAuthError("Approval failed — insufficient authorization.");
    }
    setProcessing(null);
  };

  const handleDeny = async (id: string) => {
    if (!canOperate) return;
    setProcessing(id);
    try {
      await api.deny(id, activeAgentId, "Denied by operator");
      await load();
    } catch {
      setAuthError("Deny failed — insufficient authorization.");
    }
    setProcessing(null);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Approval Queue</h1>
        <p className="text-sm text-ow-text-muted mt-1">Human oversight for sensitive agent actions</p>
      </div>

      {authError && (
        <div className="glass p-4 border border-ow-denied/30 text-sm text-ow-denied">{authError}</div>
      )}

      {loading ? (
        <div className="glass p-8 text-center text-ow-text-dim">Loading approvals...</div>
      ) : !canOperate ? null : approvals.length === 0 ? (
        <div className="glass p-8 text-center">
          <CheckCircle className="h-8 w-8 text-ow-trusted mx-auto mb-2" strokeWidth={1.5} />
          <p className="text-sm text-ow-text-muted">No pending approvals</p>
        </div>
      ) : (
        <div className="space-y-4">
          {approvals.map((approval) => (
            <div key={approval.id} className="glass-elevated p-6 border-ow-approval/20">
              <div className="flex items-start justify-between mb-4">
                <div>
                  <p className="text-[10px] font-medium text-ow-approval uppercase tracking-wider mb-1">
                    {approval.agent_name} requests approval
                  </p>
                  <h3 className="text-lg font-semibold text-ow-text">{approval.action}</h3>
                </div>
                {approval.risk_level && <StatusBadge status={approval.risk_level} />}
              </div>

              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
                {Object.entries(approval.parameters).map(([key, value]) => (
                  <div key={key}>
                    <p className="text-[10px] text-ow-text-dim uppercase tracking-wider">{key}</p>
                    <p className="text-sm font-medium text-ow-text mt-0.5">
                      {typeof value === "number" ? `₹${value.toLocaleString()}` : String(value)}
                    </p>
                  </div>
                ))}
              </div>

              <div className="flex items-center gap-3">
                <button
                  onClick={() => handleDeny(approval.id)}
                  disabled={processing === approval.id || !canOperate}
                  className="btn-danger flex items-center gap-2 disabled:opacity-50"
                >
                  <XCircle className="h-4 w-4" /> Deny
                </button>
                <button
                  onClick={() => handleApprove(approval.id)}
                  disabled={processing === approval.id || !canOperate}
                  className="btn-approve flex items-center gap-2 disabled:opacity-50"
                >
                  <CheckCircle className="h-4 w-4" /> Approve
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
