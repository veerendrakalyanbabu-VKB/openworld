import { cn } from "@/lib/utils";

const statusStyles: Record<string, string> = {
  active: "badge-trusted",
  verified: "badge-trusted",
  approved: "badge-trusted",
  allow: "badge-trusted",
  pending_approval: "badge-approval",
  pending: "badge-approval",
  require_approval: "badge-approval",
  blocked: "badge-blocked",
  denied: "badge-blocked",
  deny: "badge-blocked",
  failed: "badge-blocked",
  suspended: "badge-blocked",
  inactive: "bg-ow-text-dim/15 text-ow-text-dim",
  executing: "badge-intelligence",
  low: "badge-trusted",
  medium: "badge-approval",
  high: "badge-blocked",
  critical: "badge-blocked",
};

export function StatusBadge({ status, className }: { status: string; className?: string }) {
  const style = statusStyles[status.toLowerCase()] || "bg-ow-text-dim/15 text-ow-text-dim";
  return (
    <span className={cn("badge", style, className)}>
      {status.replace(/_/g, " ")}
    </span>
  );
}
