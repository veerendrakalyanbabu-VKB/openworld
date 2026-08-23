"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { fetchBackendState, type BackendState } from "@/lib/backend-state";

interface BackendStateContextType {
  state: BackendState | null;
  demoMode: boolean;
  loading: boolean;
}

const BackendStateContext = createContext<BackendStateContextType | undefined>(undefined);

export function BackendStateProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<BackendState | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const backendState = await fetchBackendState();
        setState(backendState);
      } catch (error) {
        console.error("[BackendStateProvider] Failed to load backend state:", error);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const value: BackendStateContextType = {
    state,
    demoMode: state?.demo_mode ?? true, // Default to demo if we can't determine
    loading,
  };

  return (
    <BackendStateContext.Provider value={value}>
      {children}
    </BackendStateContext.Provider>
  );
}

export function useBackendState(): BackendStateContextType {
  const context = useContext(BackendStateContext);
  if (context === undefined) {
    throw new Error("useBackendState must be used within BackendStateProvider");
  }
  return context;
}
