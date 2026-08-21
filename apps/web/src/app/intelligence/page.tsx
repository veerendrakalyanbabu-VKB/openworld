"use client";

import { useState } from "react";
import { api, type IntelligenceResponse } from "@/lib/api";
import { getActiveAgentId } from "@/lib/session";
import { Brain, Search, FileText } from "lucide-react";

const suggestions = [
  "Why was this action blocked?",
  "Which agents have unusual behavior?",
  "Show me failed verifications.",
  "Which policies caused the most approvals?",
  "What changed today?",
];

export default function IntelligencePage() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<IntelligenceResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleQuery = async (q: string) => {
    setQuery(q);
    setLoading(true);
    try {
      const data = await api.intelligence(q, getActiveAgentId());
      setResult(data);
    } catch {
      setResult({ query: q, answer: "Unable to reach API.", evidence: null, evidence_based: false, demo_mode: true });
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold flex items-center gap-2">
          <Brain className="h-6 w-6 text-ow-intelligence" strokeWidth={1.5} />
          Intelligence
        </h1>
        <p className="text-sm text-ow-text-muted mt-1">Evidence-based answers about your agent ecosystem</p>
      </div>

      <div className="glass p-4">
        <div className="flex gap-3">
          <Search className="h-5 w-5 text-ow-text-dim mt-2.5 shrink-0" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && query.length >= 3 && handleQuery(query)}
            placeholder="Ask about your agent ecosystem..."
            className="input-field border-0 bg-transparent focus:ring-0"
            aria-label="Intelligence query"
          />
          <button onClick={() => query.length >= 3 && handleQuery(query)} className="btn-primary shrink-0" disabled={loading}>
            {loading ? "Analyzing..." : "Query"}
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        {suggestions.map((s) => (
          <button key={s} onClick={() => handleQuery(s)} className="text-xs px-3 py-1.5 rounded-full border border-ow-border-subtle text-ow-text-muted hover:text-ow-accent hover:border-ow-accent/30 transition-colors">
            {s}
          </button>
        ))}
      </div>

      {result && (
        <div className="glass p-5 space-y-4">
          <div>
            <p className="text-sm text-ow-text">{result.answer}</p>
            {result.evidence_based && (
              <p className="text-[10px] text-ow-trusted mt-1 flex items-center gap-1">
                <FileText className="h-3 w-3" /> Evidence-based response
              </p>
            )}
          </div>
          {result.evidence != null ? (
            <pre className="p-4 rounded-lg bg-ow-bg text-xs font-mono text-ow-text-muted overflow-x-auto max-h-96">
              {JSON.stringify(result.evidence, null, 2)}
            </pre>
          ) : null}
        </div>
      )}
    </div>
  );
}
