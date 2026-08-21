import { cn } from "@/lib/utils";

interface StatCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  variant?: "default" | "accent" | "trusted" | "approval" | "blocked";
  className?: string;
}

const variantStyles = {
  default: "text-ow-text",
  accent: "text-ow-accent",
  trusted: "text-ow-trusted",
  approval: "text-ow-approval",
  blocked: "text-ow-blocked",
};

export function StatCard({ label, value, subtext, variant = "default", className }: StatCardProps) {
  return (
    <div className={cn("stat-card", className)}>
      <span className="text-xs font-medium text-ow-text-dim uppercase tracking-wider">{label}</span>
      <span className={cn("text-2xl font-semibold tabular-nums", variantStyles[variant])}>{value}</span>
      {subtext && <span className="text-xs text-ow-text-muted">{subtext}</span>}
    </div>
  );
}
