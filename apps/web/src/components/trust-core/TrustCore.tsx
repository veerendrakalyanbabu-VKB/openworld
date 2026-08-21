"use client";

import dynamic from "next/dynamic";
import { Suspense } from "react";

const TrustCoreCanvas = dynamic(() => import("./TrustCoreCanvas"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-full flex items-center justify-center">
      <div className="h-32 w-32 rounded-full border border-ow-accent/20 animate-pulse-slow" />
    </div>
  ),
});

interface TrustCoreProps {
  activeAgents?: number;
  pendingApprovals?: number;
  blockedActions?: number;
}

export function TrustCore({ activeAgents = 0, pendingApprovals = 0, blockedActions = 0 }: TrustCoreProps) {
  return (
    <div className="relative w-full h-[320px] glass overflow-hidden" aria-label="Trust Core visualization">
      <div className="absolute top-4 left-4 z-10">
        <h3 className="text-xs font-medium text-ow-text-dim uppercase tracking-wider">Trust Core</h3>
        <p className="text-[10px] text-ow-text-dim mt-0.5">Agent ecosystem state</p>
      </div>
      <Suspense fallback={null}>
        <TrustCoreCanvas
          activeAgents={activeAgents}
          pendingApprovals={pendingApprovals}
          blockedActions={blockedActions}
        />
      </Suspense>
    </div>
  );
}
