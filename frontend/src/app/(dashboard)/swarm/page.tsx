"use client";

import { useState, useRef } from "react";
import { Sparkles, Users, Network, CheckCircle2, Play, RefreshCw } from "lucide-react";
import { MarkdownRenderer } from "@/components/markdown-renderer";

interface SwarmAgent {
  id: string;
  name: string;
  role: string;
  avatar: string;
  output?: string;
  status: "idle" | "running" | "completed";
}

const DEFAULT_AGENTS: SwarmAgent[] = [
  { id: "researcher", name: "Research Agent", role: "Domain Knowledge", avatar: "🔍", status: "idle", output: "" },
  { id: "architect", name: "System Architect", role: "Lead Architect & Coder", avatar: "💻", status: "idle", output: "" },
  { id: "critic", name: "Security Auditor", role: "Quality & Security Critic", avatar: "🛡️", status: "idle", output: "" },
  { id: "synthesizer", name: "Swarm Orchestrator", role: "Consensus Lead", avatar: "🤖", status: "idle", output: "" },
];

export default function SwarmPage() {
  const [prompt, setPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [agents, setAgents] = useState<SwarmAgent[]>(DEFAULT_AGENTS);
  const [consensus, setConsensus] = useState<string>("");
  const outputEndRef = useRef<HTMLDivElement>(null);

  const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  const handleStartSwarm = async () => {
    if (!prompt.trim() || isRunning) return;

    setIsRunning(true);
    setConsensus("");
    setAgents(DEFAULT_AGENTS.map((a) => ({ ...a, status: "idle", output: "" })));

    try {
      const response = await fetch(`${API_BASE}/api/swarm/stream`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const parts = buffer.split("\n\n");
        buffer = parts.pop() || "";

        for (const part of parts) {
          const trimmed = part.trim();
          if (trimmed.startsWith("data: ")) {
            try {
              const data = JSON.parse(trimmed.slice(6));
              
              if (data.type === "agent_start") {
                setAgents((prev) =>
                  prev.map((a) =>
                    a.id === data.agent_id ? { ...a, status: "running", output: "" } : a
                  )
                );
              } else if (data.type === "agent_token") {
                setAgents((prev) =>
                  prev.map((a) =>
                    a.id === data.agent_id ? { ...a, output: (a.output || "") + data.token } : a
                  )
                );
              } else if (data.type === "agent_complete") {
                setAgents((prev) =>
                  prev.map((a) =>
                    a.id === data.agent_id ? { ...a, status: "completed", output: data.output } : a
                  )
                );
              } else if (data.type === "swarm_complete") {
                setConsensus(data.consensus);
              }
            } catch (err) {
              console.error("SSE parse error", err, part);
            }
          }
        }
      }
    } catch (err) {
      console.error("Swarm execution error", err);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="flex-1 p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <Users className="w-6 h-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">Multi-Agent Swarm Collaboration</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Watch specialized AI agents debate, critique, and synthesize complex technical solutions in real-time.
          </p>
        </div>
      </div>

      {/* Input Panel */}
      <div className="bg-card border rounded-xl p-5 shadow-sm space-y-4">
        <label className="text-sm font-medium text-foreground block">
          Define Swarm Challenge or System Problem:
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Design a fault-tolerant multi-tenant microservices architecture with OAuth2, rate limiting, and Redis caching."
          className="w-full h-24 p-3 bg-background border rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={isRunning}
        />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
            <span>Runs 4 Specialized Agents: Researcher → Architect → Auditor → Synthesizer</span>
          </div>
          <button
            onClick={handleStartSwarm}
            disabled={!prompt.trim() || isRunning}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground font-medium text-sm rounded-lg hover:opacity-90 transition disabled:opacity-50 min-h-[44px]"
          >
            {isRunning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Swarm Collaborating...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Launch Agent Swarm
              </>
            )}
          </button>
        </div>
      </div>

      {/* Live Collaboration Graph */}
      <div className="bg-card border rounded-xl p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Network className="w-4 h-4 text-primary" />
            <h2 className="text-sm font-semibold text-foreground">Collaboration Flow</h2>
          </div>
          <div className="flex items-center gap-3 text-[10px] text-muted-foreground">
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-muted-foreground/40" /> Idle
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-amber-500" /> Working
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-2 w-2 rounded-full bg-emerald-500" /> Done
            </span>
          </div>
        </div>
        <div className="overflow-x-auto">
          <svg viewBox="0 0 1000 200" className="w-full min-w-[720px] h-48">
            <defs>
              <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
                <path d="M0,0 L8,3 L0,6 Z" fill="#94a3b8" />
              </marker>
            </defs>
            {agents.slice(0, -1).map((_, i) => {
              const next = agents[i + 1]!;
              const x1 = 140 + i * 240;
              const x2 = 140 + (i + 1) * 240;
              const active = next?.status === "running";
              const done = next?.status === "completed";
              const stroke = done ? "#10b981" : active ? "#f54e00" : "#cbd5e1";
              return (
                <g key={`edge-${i}`}>
                  <line
                    x1={x1 + 40}
                    y1={90}
                    x2={x2 - 42}
                    y2={90}
                    stroke={stroke}
                    strokeWidth={active ? 2.5 : 1.5}
                    markerEnd="url(#arrowhead)"
                  />
                  {active && (
                    <circle cx={(x1 + x2) / 2} cy={90} r={4} fill="#f54e00">
                      <animate attributeName="r" values="3;7;3" dur="1.2s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="1;0.2;1" dur="1.2s" repeatCount="indefinite" />
                    </circle>
                  )}
                </g>
              );
            })}
            {agents.map((agent, i) => {
              const cx = 140 + i * 240;
              const status = agent.status;
              const ring = status === "running" ? "#f54e00" : status === "completed" ? "#10b981" : "#cbd5e1";
              return (
                <g key={agent.id}>
                  {status === "running" && (
                    <circle cx={cx} cy={90} r={34} fill="none" stroke="#f54e00" strokeWidth={2}>
                      <animate attributeName="r" values="32;46;32" dur="1.4s" repeatCount="indefinite" />
                      <animate attributeName="opacity" values="0.7;0;0.7" dur="1.4s" repeatCount="indefinite" />
                    </circle>
                  )}
                  <circle cx={cx} cy={90} r={32} fill="white" stroke={ring} strokeWidth={status === "running" ? 3 : 2} />
                  <text x={cx} y={90} textAnchor="middle" dominantBaseline="central" fontSize="20">
                    {agent.avatar}
                  </text>
                  <text x={cx} y={138} textAnchor="middle" fontSize="12" fontWeight="600" fill="#26251e">
                    {agent.name}
                  </text>
                  <text x={cx} y={154} textAnchor="middle" fontSize="9.5" fill="#77756e">
                    {agent.role}
                  </text>
                </g>
              );
            })}
          </svg>
        </div>
      </div>

      {/* Live Agent Execution Graph */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {agents.map((agent) => (
          <div
            key={agent.id}
            className={`border rounded-xl p-4 flex flex-col justify-between space-y-3 transition-all max-w-full overflow-hidden ${
              agent.status === "running"
                ? "border-primary ring-2 ring-primary/20 bg-primary/5 shadow-md"
                : agent.status === "completed"
                ? "border-emerald-500/40 bg-emerald-500/5"
                : "border-border bg-card/50"
            }`}
          >
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                <span className="text-xl shrink-0">{agent.avatar}</span>
                <div className="min-w-0">
                  <h3 className="font-semibold text-sm truncate">{agent.name}</h3>
                  <span className="text-xs text-muted-foreground block truncate">{agent.role}</span>
                </div>
              </div>
              {agent.status === "running" && (
                <span className="flex items-center gap-1.5 text-xs text-primary font-medium animate-pulse shrink-0">
                  <RefreshCw className="w-3.5 h-3.5 animate-spin" /> Live
                </span>
              )}
              {agent.status === "completed" && (
                <span className="flex items-center gap-1 text-xs text-emerald-600 font-medium shrink-0">
                  <CheckCircle2 className="w-4 h-4" /> Ready
                </span>
              )}
            </div>

            <div className="h-48 overflow-y-auto bg-background/80 rounded-lg p-3 border text-xs text-foreground font-mono space-y-1 max-w-full overflow-x-auto">
              {agent.output ? (
                <pre className="whitespace-pre-wrap font-sans break-words">{agent.output}</pre>
              ) : (
                <span className="text-muted-foreground italic">Waiting for swarm dispatch...</span>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Final Synthesized Consensus */}
      {consensus && (
        <div className="bg-card border-2 border-primary/30 rounded-xl p-4 sm:p-6 shadow-lg space-y-4 max-w-full overflow-x-hidden">
          <div className="flex items-center gap-2 border-b pb-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
            <h2 className="text-lg font-bold text-foreground">Synthesized Swarm Consensus Report</h2>
          </div>
          <MarkdownRenderer content={consensus} />
        </div>
      )}
      <div ref={outputEndRef} />
    </div>
  );
}
