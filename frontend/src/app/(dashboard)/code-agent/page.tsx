"use client";

import { useState, useRef } from "react";
import { FileCode, Sparkles, Play, RefreshCw, Loader2, TerminalSquare, CheckCircle2, AlertTriangle, XCircle } from "lucide-react";
import { MarkdownRenderer } from "@/components/markdown-renderer";
import { getAccessToken } from "@/lib/auth-store";

const LANGUAGE_OPTIONS = [
  "Auto",
  "Python",
  "JavaScript",
  "TypeScript",
  "Java",
  "C++",
  "C",
  "Rust",
  "Go",
  "Ruby",
  "PHP",
  "Bash",
];

interface RunEntry {
  iteration: number;
  language: string;
  code: string;
  description: string;
  exitCode: number | null;
  stdout: string;
  stderr: string;
}

interface RetryEntry {
  iteration: number;
  reason: string;
}

export default function CodeAgentPage() {
  const [prompt, setPrompt] = useState("");
  const [language, setLanguage] = useState("Auto");
  const [isRunning, setIsRunning] = useState(false);
  const [plan, setPlan] = useState("");
  const [runs, setRuns] = useState<RunEntry[]>([]);
  const [retries, setRetries] = useState<RetryEntry[]>([]);
  const [finalExplanation, setFinalExplanation] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const outputEndRef = useRef<HTMLDivElement>(null);

  const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

  const handleRun = async () => {
    if (!prompt.trim() || isRunning) return;

    setIsRunning(true);
    setPlan("");
    setRuns([]);
    setRetries([]);
    setFinalExplanation("");
    setErrorMsg("");

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      const token = getAccessToken();
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const response = await fetch(`${API_BASE}/api/code-agent/run`, {
        method: "POST",
        headers,
        body: JSON.stringify({
          prompt,
          language: language === "Auto" ? undefined : language.toLowerCase(),
        }),
      });

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

            if (event === "code_plan") {
              setPlan(data.plan || "");
            } else if (event === "code_write") {
              setRuns((prev) => {
                const next = prev.filter((r) => r.iteration !== data.iteration);
                return [
                  ...next,
                  {
                    iteration: data.iteration,
                    language: data.language || "python",
                    code: data.code || "",
                    description: data.description || "",
                    exitCode: null,
                    stdout: "",
                    stderr: "",
                  },
                ];
              });
            } else if (event === "code_run") {
              setRuns((prev) =>
                prev.map((r) =>
                  r.iteration === data.iteration
                    ? { ...r, exitCode: data.exit_code, stdout: data.stdout || "", stderr: data.stderr || "" }
                    : r,
                ),
              );
            } else if (event === "code_retry") {
              setRetries((prev) => [...prev, { iteration: data.iteration, reason: data.reason || "Code failed to run" }]);
            } else if (event === "code_complete") {
              if (data.error) {
                setErrorMsg(data.error);
              } else {
                setFinalExplanation(data.explanation || "");
                setRuns((prev) =>
                  prev.map((r, idx) =>
                    idx === prev.length - 1
                      ? { ...r, language: data.language || r.language, code: data.code || r.code }
                      : r,
                  ),
                );
              }
            }
          } catch (err) {
            console.error("SSE parse error", err, block);
          }
        }
      }
    } catch (err) {
      console.error("Code agent error", err);
      setErrorMsg("Network error. Ensure the backend is running on port 8000.");
    } finally {
      setIsRunning(false);
      outputEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  };

  return (
    <div className="mx-auto w-full min-w-0 max-w-7xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-border/40 pb-4">
        <div>
          <div className="flex items-center gap-2">
            <FileCode className="w-6 h-6 text-primary" />
            <h1 className="text-2xl font-bold tracking-tight">Code Agent</h1>
          </div>
          <p className="text-sm text-muted-foreground mt-1">
            Describe a program — it writes the code, runs it in a sandbox, and iterates on errors until it works.
          </p>
        </div>
      </div>

      {/* Input Panel */}
      <div className="bg-card border rounded-xl p-5 shadow-sm space-y-4">
        <label className="text-sm font-medium text-foreground block">
          What program should I build?
        </label>
        <textarea
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="e.g. Write a Python script that computes the first 20 Fibonacci numbers, and a function that checks if a number is prime."
          className="w-full h-24 p-3 bg-background border rounded-lg text-sm resize-none focus:outline-none focus:ring-2 focus:ring-primary"
          disabled={isRunning}
        />
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div className="flex min-w-0 flex-wrap items-center gap-2 text-xs text-muted-foreground">
            <Sparkles className="w-4 h-4 text-amber-500 shrink-0" />
            <span>Sandboxed execution — writes, runs, and self-corrects</span>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              disabled={isRunning}
              className="h-10 min-w-0 rounded-lg border border-border bg-background px-2 text-base text-foreground focus:outline-none focus:ring-1 focus:ring-primary sm:ml-1 sm:h-8 sm:text-xs"
            >
              {LANGUAGE_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt === "Auto" ? "Language: Auto" : opt}
                </option>
              ))}
            </select>
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
                Run Code
              </>
            )}
          </button>
        </div>
      </div>

      {/* Plan */}
      {plan && (
        <div className="bg-card border rounded-xl p-4 shadow-sm">
          <div className="flex items-center gap-2 mb-2">
            <Sparkles className="w-4 h-4 text-amber-500" />
            <h3 className="text-sm font-semibold text-foreground">Approach</h3>
          </div>
          <p className="text-xs text-foreground/80 whitespace-pre-wrap">{plan}</p>
        </div>
      )}

      {/* Code + terminal per iteration */}
      {runs.map((run) => {
        const succeeded = run.exitCode === 0;
        const failed = run.exitCode !== null && run.exitCode !== 0;
        return (
          <div key={run.iteration} className="space-y-3">
            <div className="bg-card border rounded-xl shadow-sm overflow-hidden">
              <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-muted/30">
                <div className="flex items-center gap-2">
                  <FileCode className="w-4 h-4 text-primary" />
                  <span className="text-xs font-semibold text-foreground uppercase tracking-wider">
                    Iteration {run.iteration} — {run.language}
                  </span>
                </div>
                {run.exitCode !== null && (
                  <span
                    className={`inline-flex items-center gap-1.5 text-[11px] font-semibold px-2 py-0.5 rounded-md ${
                      succeeded
                        ? "bg-emerald-500/10 text-emerald-600"
                        : failed
                          ? "bg-red-500/10 text-red-600"
                          : "bg-muted text-muted-foreground"
                    }`}
                  >
                    {succeeded ? (
                      <CheckCircle2 className="w-3 h-3" />
                    ) : failed ? (
                      <XCircle className="w-3 h-3" />
                    ) : (
                      <Loader2 className="w-3 h-3 animate-spin" />
                    )}
                    {succeeded ? `Exit 0` : failed ? `Exit ${run.exitCode}` : "Running…"}
                  </span>
                )}
              </div>
              {run.description && (
                <div className="px-4 pt-3 text-xs text-foreground/70">{run.description}</div>
              )}
              <pre className="p-4 text-[12.5px] leading-relaxed font-mono text-foreground overflow-x-auto max-h-96 bg-background/40 whitespace-pre">
                {run.code || "Generating code…"}
              </pre>
            </div>

            {(run.stdout || run.stderr || run.exitCode !== null) && (
              <div className="bg-[#0f1115] border rounded-xl shadow-sm overflow-hidden">
                <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/10">
                  <TerminalSquare className="w-4 h-4 text-emerald-400" />
                  <span className="text-xs font-semibold text-white/80 uppercase tracking-wider">
                    Output
                  </span>
                </div>
                <pre className="p-4 text-[12.5px] leading-relaxed font-mono overflow-x-auto max-h-64 whitespace-pre">
                  {run.stdout && <span className="text-emerald-300">{run.stdout}</span>}
                  {run.stderr && (
                    <>
                      {run.stdout ? "\n" : ""}
                      <span className="text-red-400">{run.stderr}</span>
                    </>
                  )}
                  {!run.stdout && !run.stderr && (
                    <span className="text-white/40">{succeeded ? "(no output)" : "(awaiting execution…)"}</span>
                  )}
                </pre>
              </div>
            )}
          </div>
        );
      })}

      {/* Retry notices */}
      {retries.length > 0 && (
        <div className="space-y-2">
          {retries.map((r, idx) => (
            <div
              key={idx}
              className="flex items-start gap-3 p-3 rounded-lg border border-amber-500/30 bg-amber-500/5"
            >
              <AlertTriangle className="w-4 h-4 text-amber-500 mt-0.5 shrink-0" />
              <div className="min-w-0">
                <p className="text-xs font-semibold text-amber-600">
                  Iteration {r.iteration} failed — auto-fixing
                </p>
                <p className="text-xs text-foreground/70 mt-0.5 whitespace-pre-wrap break-words">{r.reason}</p>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {errorMsg && (
        <div className="flex items-start gap-3 p-4 rounded-xl border border-red-500/30 bg-red-500/5">
          <XCircle className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
          <p className="text-sm text-red-600">{errorMsg}</p>
        </div>
      )}

      {/* Final explanation */}
      {finalExplanation && (
        <div className="w-full min-w-0 max-w-full space-y-4 rounded-xl border-2 border-emerald-500/30 bg-card p-4 shadow-lg sm:p-6">
          <div className="flex items-center gap-2 border-b pb-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-500 shrink-0" />
            <h2 className="text-lg font-bold text-foreground">Solution Summary</h2>
          </div>
          <MarkdownRenderer content={finalExplanation} />
        </div>
      )}
      <div ref={outputEndRef} />
    </div>
  );
}
