"use client";

import { useEffect, useState } from "react";
import { Search, Command } from "lucide-react";
import { DemoBanner } from "./DemoBanner";
import { ProductionBanner } from "./ProductionBanner";
import { api, type DemoAgentAuth } from "@/lib/api";
import { getActiveAgentId } from "@/lib/session";
import { useBackendState } from "@/components/providers/BackendStateProvider";

export function TopBar() {
  const [time, setTime] = useState("");
  const [identity, setIdentity] = useState<DemoAgentAuth | null>(null);
  const { demoMode, loading } = useBackendState();

  useEffect(() => {
    const update = () => {
      setTime(
        new Intl.DateTimeFormat("en-US", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
          hour12: false,
        }).format(new Date())
      );
    };
    update();
    const interval = setInterval(update, 1000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const load = () => {
      api.demoAgents().then((agents) => {
        const activeId = getActiveAgentId();
        setIdentity(agents.find((a) => a.agent_id === activeId) ?? agents[0] ?? null);
      });
    };
    load();
    window.addEventListener("storage", load);
    return () => window.removeEventListener("storage", load);
  }, []);

  return (
    <header className="sticky top-0 z-30 flex items-center justify-between px-6 py-3 border-b border-ow-border-subtle bg-ow-bg/80 backdrop-blur-xl">
      {!loading && (demoMode ? <DemoBanner /> : <ProductionBanner />)}

      <div className="flex items-center gap-4 ml-auto">
        {identity && (
          <div className="hidden md:block text-right">
            <p className="text-xs text-ow-text-muted">{identity.agent_name}</p>
            <p className="text-[10px] font-mono text-ow-text-dim">
              {identity.roles.slice(0, 3).join(", ")}
            </p>
          </div>
        )}
        <button
          onClick={() => {
            window.dispatchEvent(new KeyboardEvent("keydown", { key: "k", ctrlKey: true }));
          }}
          className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-ow-border-subtle bg-ow-surface text-ow-text-muted text-sm hover:border-ow-border transition-colors"
          aria-label="Open command palette"
        >
          <Search className="h-3.5 w-3.5" />
          <span className="hidden sm:inline">Search...</span>
          <kbd className="hidden sm:inline-flex items-center gap-0.5 px-1.5 py-0.5 rounded bg-ow-bg text-[10px] font-mono text-ow-text-dim border border-ow-border-subtle">
            <Command className="h-2.5 w-2.5" />K
          </kbd>
        </button>
        <time className="text-xs font-mono text-ow-text-dim tabular-nums">{time}</time>
      </div>
    </header>
  );
}
