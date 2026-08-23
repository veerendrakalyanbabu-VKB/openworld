"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type GatewayState = "loading" | "production" | "demo" | "unavailable";

export function DemoBanner() {
  const [gatewayState, setGatewayState] = useState<GatewayState>("loading");

  useEffect(() => {
    let active = true;

    api
      .health()
      .then((health) => {
        if (!active) return;
        setGatewayState(health.demo_mode ? "demo" : "production");
      })
      .catch(() => {
        if (!active) return;
        setGatewayState("unavailable");
      });

    return () => {
      active = false;
    };
  }, []);

  const label =
    gatewayState === "production"
      ? "Production Mode — Live Gateway"
      : gatewayState === "demo"
        ? "Demo Mode — Synthetic Data"
        : gatewayState === "unavailable"
          ? "Gateway Status Unavailable"
          : "Checking Gateway Status";

  return (
    <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-ow-approval/10 border border-ow-approval/20">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-ow-approval opacity-75" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-ow-approval" />
      </span>

      <span className="text-[11px] font-medium text-ow-approval tracking-wide uppercase">
        {label}
      </span>
    </div>
  );
}
