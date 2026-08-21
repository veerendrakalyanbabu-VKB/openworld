"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  Zap,
  Shield,
  CheckCircle,
  ScrollText,
  Brain,
  FlaskConical,
  Settings,
  Hexagon,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/actions", label: "Actions", icon: Zap },
  { href: "/policies", label: "Policies", icon: Shield },
  { href: "/approvals", label: "Approvals", icon: CheckCircle },
  { href: "/audit", label: "Audit", icon: ScrollText },
  { href: "/intelligence", label: "Intelligence", icon: Brain },
  { href: "/simulation", label: "Simulation", icon: FlaskConical },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 flex h-screen w-60 flex-col border-r border-ow-border-subtle bg-ow-surface/50 backdrop-blur-xl">
      <div className="flex items-center gap-2.5 px-5 py-5 border-b border-ow-border-subtle">
        <Hexagon className="h-7 w-7 text-ow-accent" strokeWidth={1.5} />
        <div>
          <h1 className="text-sm font-semibold tracking-wide text-ow-text">OPENWORLD</h1>
          <p className="text-[10px] text-ow-text-dim tracking-wider uppercase">Trust Layer</p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-0.5" aria-label="Main navigation">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors",
                isActive
                  ? "bg-ow-accent/10 text-ow-accent"
                  : "text-ow-text-muted hover:text-ow-text hover:bg-ow-surface-elevated/50"
              )}
              aria-current={isActive ? "page" : undefined}
            >
              <item.icon className="h-4 w-4" strokeWidth={1.5} />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-3 py-4 border-t border-ow-border-subtle">
        <Link
          href="/settings"
          className="flex items-center gap-3 px-3 py-2 rounded-lg text-sm text-ow-text-muted hover:text-ow-text hover:bg-ow-surface-elevated/50 transition-colors"
        >
          <Settings className="h-4 w-4" strokeWidth={1.5} />
          Settings
        </Link>
      </div>
    </aside>
  );
}
