"use client";

import { useState, useRef } from "react";
import { Sparkles, ListChecks, CheckCircle2, Circle, Play, RefreshCw, Loader2 } from "lucide-react";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { getAccessToken } from "@/lib/auth-store";

interface TaskStep {
  index: number;
  title: string;
  status: "pending" | "running" | "completed";
  output?: string;
}

export default function TaskRunnerPage() {
  const [prompt, setPrompt] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [steps, setSteps] = useState<TaskStep[]>([]);
  const [progress, setProgress] = useState(0);
  const [finalOutput, setFinalOutput] = useState("");
  const outputEndRef = useRef<HTMLDivElement>(null);

  const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  const handleRun = async () => {
    if (!prompt.trim() || isRunning) return;

    setIsRunning(true);
    setSteps([]);
    setProgress(0);
    setFinalOutput("");

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      const token = getAccessToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(`${API_BASE}/api/task/run`, {
        method: "POST",
        headers,
        body: JSON.stringify({ prompt }),
      });

      if (!response.ok) {
        const text = await response.text().catch(() => '');
        let errMsg = `Task execution failed (${response.status})`;
        try {
          const parsed = JSON.parse(text);
          errMsg = parsed.detail || parsed.error || errMsg;
        } catch {
          if (text) errMsg = text.slice(0, 150);
        }
        throw new Error(errMsg);
      }

      if (!response.body) throw new Error("No response body");

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || "";

        for (const block of blocks) {
          let event = "message";
          const dataLines: string[] = [];
          for (const line of block.split("\n")) {
            if (line.startsWith("event:")) event = line.slice(6).trim();
            if (line.startsWith("data:")) dataLines.push(line.slice(5).trimStart());
          }
          if (!dataLines.length) continue;

          try {
            const data = JSON.parse(dataLines.join("\n"));

            if (event === "task_start" && data.total_steps) {
              setSteps(
                Array.from({ length: data.total_steps }, (_, i) => ({
                  index: i + 1,
                  title: `Step ${i + 1}`,
                  status: "pending" as const,
                })),
              );
            } else if (event === "task_step") {
              setSteps((prev) =>
                prev.map((s) =>
                  s.index === data.step_index
                    ? {
                        ...s,
                        title: data.title || s.title,
                        status: data.status === "running" ? "running" : "completed",
                        output: data.output || s.output,
                      }
                    : s,
                ),
              );
            } else if (event === "task_progress") {
              setProgress(data.percent || 0);
            } else if (event === "task_complete") {
              setFinalOutput(data.output || "");
              setProgress(100);
              setSteps((prev) =>
                prev.map((s) => (s.status === "running" ? { ...s, status: "completed" } : s)),
              );
            }
          } catch (err) {
            console.error("SSE parse error", err, block);
          }
        }
      }
    } catch (err) {
      console.error("Task run error", err);
      setFinalOutput("Network error. Ensure the backend is running on port 8000.");
    } finally {
      setIsRunning(false);
      outputEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="flex-1 p-6 max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <ListChecks className="w-6 h-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">Multi-Step Task Runner</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Give it a complex goal — it plans, executes each step, and verifies the final deliverable in real-time.
          </p>
        </div>
      </div>

      {/* Input Panel */}
      <div className="bg-card border rounded-xl p-5 shadow-sm space-y-4">
        <label className="text-sm font-medium text-foreground block">
          Describe your goal or task:
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Research the latest advances in solid-state batteries, then summarize the top 3 companies working on them with their latest funding and commercial milestones."
          className="w-full h-24 p-3 bg-background border rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={isRunning}
        />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
            <span>Autonomous pipeline: Planner → Executor → Verifier</span>
          </div>
          <button
            onClick={handleRun}
            disabled={!prompt.trim() || isRunning}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-5 py-2.5 bg-primary text-primary-foreground font-medium text-sm rounded-lg hover:opacity-90 transition disabled:opacity-50 min-h-[44px]"
          >
            {isRunning ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                Running...
              </>
            ) : (
              <>
                <Play className="w-4 h-4" />
                Run Task
              </>
            )}
          </button>
        </div>
      </div>

      {/* Progress */}
      {(steps.length > 0 || isRunning) && (
        <div className="bg-card border rounded-xl p-4 shadow-sm space-y-3">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <span className="font-medium text-foreground">
              {isRunning ? "Executing plan..." : "Plan complete"}
            </span>
            <span>{progress}%</span>
          </div>
          <div className="h-2 w-full bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>

          <ul className="space-y-2 pt-1">
            {steps.map((step) => (
              <li
                key={step.index}
                className={`flex items-start gap-3 p-3 rounded-lg border transition-all ${
                  step.status === "running"
                    ? "border-primary bg-primary/5 ring-2 ring-primary/20"
                    : step.status === "completed"
                      ? "border-emerald-500/30 bg-emerald-500/5"
                      : "border-border bg-background/50"
                }`}
              >
                <span className="mt-0.5 shrink-0">
                  {step.status === "running" && <Loader2 className="w-4 h-4 text-primary animate-spin" />}
                  {step.status === "completed" && <CheckCircle2 className="w-4 h-4 text-emerald-500" />}
                  {step.status === "pending" && <Circle className="w-4 h-4 text-muted-foreground/40" />}
                </span>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-muted-foreground">Step {step.index}</span>
                    <h3 className="text-sm font-medium text-foreground truncate">{step.title}</h3>
                  </div>
                  {step.output && (
                    <p className="mt-1.5 text-xs text-foreground/80 whitespace-pre-wrap break-words max-h-40 overflow-y-auto">
                      {step.output}
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Final Deliverable */}
      {finalOutput && (
        <div className="bg-card border-2 border-primary/30 rounded-xl p-4 sm:p-6 shadow-lg space-y-4 max-w-full overflow-x-hidden">
          <div className="flex items-center gap-2 border-b pb-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
            <h2 className="text-lg font-bold text-foreground">Final Deliverable</h2>
          </div>
          <MarkdownRenderer content={finalOutput} />
        </div>
      )}
      <div ref={outputEndRef} />
    </div>
  );
}
