"use client";

import { useEffect, useState } from "react";
import { api, type DemoAgentAuth } from "@/lib/api";
import { getActiveAgentId, setActiveAgentId, hasRole } from "@/lib/session";

export default function SettingsPage() {
  const [agents, setAgents] = useState<DemoAgentAuth[]>([]);
  const [activeId, setActiveId] = useState(getActiveAgentId());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.demoAgents().then((list) => {
      setAgents(list);
      setLoading(false);
    });
  }, []);

  const active = agents.find((a) => a.agent_id === activeId);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Settings</h1>
        <p className="text-sm text-ow-text-muted mt-1">Demo identity and configuration</p>
      </div>
      <div className="glass p-5 space-y-4 max-w-lg">
        <div>
          <label className="text-xs text-ow-text-muted uppercase tracking-wider">API URL</label>
          <input
            readOnly
            value={process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}
            className="input-field mt-1 font-mono text-sm"
          />
        </div>
        <div>
          <label className="text-xs text-ow-text-muted uppercase tracking-wider">Active identity</label>
          {loading ? (
            <p className="text-sm text-ow-text-dim mt-1">Loading demo agents...</p>
          ) : (
            <select
              className="input-field mt-1 text-sm"
              value={activeId}
              onChange={(e) => {
                setActiveAgentId(e.target.value);
                setActiveId(e.target.value);
              }}
            >
              {agents.map((a) => (
                <option key={a.agent_id} value={a.agent_id}>
                  {a.agent_name} ({a.agent_id})
                </option>
              ))}
            </select>
          )}
        </div>
        {active && (
          <div>
            <label className="text-xs text-ow-text-muted uppercase tracking-wider">Roles</label>
            <div className="flex flex-wrap gap-2 mt-2">
              {active.roles.map((role) => (
                <span
                  key={role}
                  className="px-2 py-0.5 rounded text-xs font-mono bg-ow-surface-elevated border border-ow-border-subtle text-ow-accent"
                >
                  {role}
                </span>
              ))}
            </div>
            <p className="text-xs text-ow-text-dim mt-2">
              Operator: {hasRole(active.roles, "operator") ? "yes" : "no"} · Policy admin:{" "}
              {hasRole(active.roles, "policy_admin") ? "yes" : "no"} · System admin:{" "}
              {hasRole(active.roles, "system_admin") ? "yes" : "no"}
            </p>
          </div>
        )}
        <div>
          <label className="text-xs text-ow-text-muted uppercase tracking-wider">Mode</label>
          <p className="text-sm text-ow-approval mt-1">DEMO MODE — SYNTHETIC DATA</p>
        </div>
      </div>
    </div>
  );
}
