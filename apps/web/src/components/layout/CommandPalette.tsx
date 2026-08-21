"use client";

import { useEffect, useState, useCallback } from "react";
import { useRouter } from "next/navigation";
import { Search, Bot, Zap, Shield, CheckCircle, ScrollText, Settings } from "lucide-react";
import { cn } from "@/lib/utils";

const commands = [
  { id: "agents", label: "Search agents", icon: Bot, href: "/agents" },
  { id: "actions", label: "Search actions", icon: Zap, href: "/actions" },
  { id: "blocked", label: "Inspect blocked actions", icon: Zap, href: "/actions?status=blocked" },
  { id: "policies", label: "Create policy", icon: Shield, href: "/policies" },
  { id: "approvals", label: "Open approvals", icon: CheckCircle, href: "/approvals" },
  { id: "audit", label: "View audit", icon: ScrollText, href: "/audit" },
  { id: "settings", label: "Open settings", icon: Settings, href: "/settings" },
];

export function CommandPalette() {
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selected, setSelected] = useState(0);
  const router = useRouter();

  const filtered = commands.filter((c) =>
    c.label.toLowerCase().includes(query.toLowerCase())
  );

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
        setQuery("");
        setSelected(0);
      }
      if (!open) return;
      if (e.key === "Escape") setOpen(false);
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelected((s) => Math.min(s + 1, filtered.length - 1));
      }
      if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelected((s) => Math.max(s - 1, 0));
      }
      if (e.key === "Enter" && filtered[selected]) {
        e.preventDefault();
        router.push(filtered[selected].href);
        setOpen(false);
      }
    },
    [open, filtered, selected, router]
  );

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[20vh]" role="dialog" aria-label="Command palette">
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm" onClick={() => setOpen(false)} />
      <div className="relative w-full max-w-lg glass-elevated shadow-2xl overflow-hidden">
        <div className="flex items-center gap-3 px-4 py-3 border-b border-ow-border-subtle">
          <Search className="h-4 w-4 text-ow-text-dim" />
          <input
            autoFocus
            value={query}
            onChange={(e) => { setQuery(e.target.value); setSelected(0); }}
            placeholder="Type a command..."
            className="flex-1 bg-transparent text-sm text-ow-text placeholder:text-ow-text-dim outline-none"
            aria-label="Command search"
          />
        </div>
        <ul className="py-2 max-h-64 overflow-y-auto" role="listbox">
          {filtered.map((cmd, i) => (
            <li key={cmd.id} role="option" aria-selected={i === selected}>
              <button
                onClick={() => { router.push(cmd.href); setOpen(false); }}
                className={cn(
                  "flex items-center gap-3 w-full px-4 py-2.5 text-sm transition-colors",
                  i === selected ? "bg-ow-accent/10 text-ow-accent" : "text-ow-text-muted hover:bg-ow-surface-elevated/50"
                )}
              >
                <cmd.icon className="h-4 w-4" strokeWidth={1.5} />
                {cmd.label}
              </button>
            </li>
          ))}
          {filtered.length === 0 && (
            <li className="px-4 py-6 text-center text-sm text-ow-text-dim">No commands found</li>
          )}
        </ul>
      </div>
    </div>
  );
}
