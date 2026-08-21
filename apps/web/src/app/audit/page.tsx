import { api, DEFAULT_OPERATOR_AGENT_ID } from "@/lib/api";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { formatDate } from "@/lib/utils";

export const dynamic = "force-dynamic";

export default async function AuditPage() {
  let events: Awaited<ReturnType<typeof api.audit>>["events"] = [];
  let total = 0;
  try {
    const data = await api.audit(DEFAULT_OPERATOR_AGENT_ID, { limit: "50" });
    events = data.events;
    total = data.total;
  } catch { /* API offline */ }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Audit Trail</h1>
        <p className="text-sm text-ow-text-muted mt-1">{total} immutable events recorded</p>
      </div>

      <div className="glass overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-ow-border-subtle text-left">
                <th className="px-4 py-3 text-xs font-medium text-ow-text-dim uppercase tracking-wider">Time</th>
                <th className="px-4 py-3 text-xs font-medium text-ow-text-dim uppercase tracking-wider">Event</th>
                <th className="px-4 py-3 text-xs font-medium text-ow-text-dim uppercase tracking-wider">Actor</th>
                <th className="px-4 py-3 text-xs font-medium text-ow-text-dim uppercase tracking-wider">Action</th>
                <th className="px-4 py-3 text-xs font-medium text-ow-text-dim uppercase tracking-wider">Decision</th>
                <th className="px-4 py-3 text-xs font-medium text-ow-text-dim uppercase tracking-wider">Risk</th>
              </tr>
            </thead>
            <tbody>
              {events.length === 0 ? (
                <tr><td colSpan={6} className="px-4 py-8 text-center text-ow-text-dim">No audit events</td></tr>
              ) : (
                events.map((event) => (
                  <tr key={event.id} className="border-b border-ow-border-subtle/50 hover:bg-ow-surface-elevated/30 transition-colors">
                    <td className="px-4 py-3 font-mono text-xs text-ow-text-dim whitespace-nowrap">{formatDate(event.timestamp)}</td>
                    <td className="px-4 py-3 text-ow-text-muted">{event.event_type.replace(/_/g, " ")}</td>
                    <td className="px-4 py-3">{event.actor}</td>
                    <td className="px-4 py-3 font-mono text-xs">{event.action || "—"}</td>
                    <td className="px-4 py-3">{event.decision ? <StatusBadge status={event.decision} /> : "—"}</td>
                    <td className="px-4 py-3">{event.risk_level ? <StatusBadge status={event.risk_level} /> : "—"}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
