import Link from "next/link"

export default function DocsPage() {
  return (
    <div className="min-h-screen min-h-[100svh] w-full min-w-0 bg-[#F5F4F0] font-sans text-[#111] antialiased supports-[height:100dvh]:min-h-dvh">
      {/* Simple top nav */}
      <div className="fixed top-4 inset-x-0 z-50 flex justify-center px-4 pointer-events-none">
        <nav className="pointer-events-auto w-full max-w-6xl flex items-center justify-between px-5 py-3 rounded-2xl border border-black/[0.06] bg-[#F5F4F0]/30"
          style={{ backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)", boxShadow: "0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.06)" }}
        >
          <Link href="/" className="font-pixel text-xs tracking-[0.25em] text-black/70 hover:text-black transition-colors">AGENTIC</Link>
          <Link href="/" className="text-[11px] text-black/60 hover:text-black transition-colors tracking-wide">
            ← Back to home
          </Link>
        </nav>
      </div>

      <div className="px-4 pb-16 pt-24 sm:px-6 sm:pb-20 md:px-12 lg:px-20">
        <div className="max-w-3xl mx-auto">
          <div className="mb-12">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] tracking-widest font-sans text-black/40 bg-black/[0.04]">
              DOCUMENTATION
            </span>
            <h1 className="mt-5 text-3xl font-light leading-[1.05] tracking-tight sm:text-4xl md:text-5xl">
              Getting Started
            </h1>
            <p className="mt-4 text-sm text-black/45 leading-relaxed">
              Everything you need to know about using the Agentic platform — from chatting 
              with agents to building custom workflows.
            </p>
          </div>

          <div className="space-y-10 text-sm text-black/55 leading-relaxed">
            {/* Overview */}
            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">What is Agentic?</h2>
              <p className="mb-3">
                Agentic is a multi-agent AI workspace where you can chat with specialized AI agents, 
                upload documents for RAG-powered search, generate quizzes and study materials, 
                conduct web research, write code, and create custom agents — all in one place.
              </p>
              <p>
                Each agent is purpose-built for a specific domain. Use them individually or combine 
                them in a single conversation with Teamwork mode.
              </p>
            </section>

            {/* Agents */}
            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">Available Agents</h2>
              <div className="space-y-4">
                {[
                  { name: "Auto (Orchestrator)", desc: "Automatically routes your request to the best agent for the task." },
                  { name: "Knowledge Agent", desc: "Answers questions using your uploaded documents with citations." },
                  { name: "Research Agent", desc: "Conducts internet research, compares sources, and generates reports." },
                  { name: "Coding Agent", desc: "Writes code, explains programming concepts, debugs issues." },
                  { name: "Quiz Agent", desc: "Generates MCQs, exams, and practice questions with answer keys." },
                  { name: "Notes Agent", desc: "Creates structured notes, summaries, and revision materials." },
                  { name: "Planner Agent", desc: "Helps with study planning, task management, and scheduling." },
                  { name: "Drive Agent", desc: "Manages Google Drive files, uploads, and folder organization." },
                  { name: "Calendar Agent", desc: "Manages Google Calendar events and scheduling." },
                  { name: "Memory Agent", desc: "Manages long-term memory, conversation history, and preferences." },
                ].map((agent) => (
                  <div key={agent.name} className="p-5 rounded-2xl border border-black/[0.07] bg-white">
                    <h3 className="font-pixel text-[11px] tracking-widest text-black/40 mb-1.5">{agent.name.toUpperCase().replace(/\s+/g, '-')}</h3>
                    <p className="text-sm text-black/45">{agent.desc}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* RAG Knowledge Base */}
            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">Knowledge Base (RAG)</h2>
              <p className="mb-3">
                Upload PDFs, documents, and images to your knowledge base. The RAG engine indexes 
                everything automatically, allowing you to query your documents with natural language 
                and get cited answers from your own data.
              </p>
              <div className="p-5 rounded-2xl border border-black/[0.07] bg-white">
                <p className="font-mono text-[12px] text-black/60 leading-relaxed">
                  <span className="text-black/25"># Example: Query your knowledge base</span><br />
                  <span className="text-blue-600/70">curl</span> -X POST <span className="text-amber-700/70">/api/knowledge/query</span> \<br />
                  &nbsp;&nbsp;-H <span className="text-green-700/70">&quot;Authorization: Bearer $KEY&quot;</span> \<br />
                  &nbsp;&nbsp;-d <span className="text-green-700/70">{`{"query": "explain transformer architecture"}`}</span>
                </p>
              </div>
            </section>

            {/* Custom Agents */}
            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">Custom Agents</h2>
              <p className="mb-3">
                Create your own specialized agents with custom instructions, tools, and knowledge 
                sources. Deploy them instantly into your workspace and share with your team.
              </p>
              <div className="p-5 rounded-2xl border border-black/[0.07] bg-white">
                <p className="font-mono text-[12px] text-black/60 leading-relaxed">
                  <span className="text-black/25"># Create a custom agent via API</span><br />
                  <span className="text-blue-600/70">curl</span> -X POST <span className="text-amber-700/70">/api/agents</span> \<br />
                  &nbsp;&nbsp;-H <span className="text-green-700/70">&quot;Authorization: Bearer $KEY&quot;</span> \<br />
                  &nbsp;&nbsp;-d <span className="text-green-700/70">{`{"name": "Market Researcher", "description": "Researches market trends", "tools": ["web_search", "scrape_page"]}`}</span>
                </p>
              </div>
            </section>

            {/* Teamwork Mode */}
            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">Teamwork Mode</h2>
              <p>
                Enable Teamwork mode to assign multiple agents to a single task. Each agent contributes 
                their specialized skills in sequence, allowing for complex multi-step workflows. 
                Select which agents participate and they&apos;ll collaborate to achieve your goal.
              </p>
            </section>

            {/* API */}
            <section>
              <h2 className="text-lg font-light text-[#111] mb-3">API & Integrations</h2>
              <p className="mb-3">
                Agentic provides REST and WebSocket APIs for programmatic access. Integrate with 
                Google Drive for file management and Google Calendar for scheduling. Stream agent 
                outputs directly into your own applications.
              </p>
              <p>
                Full API documentation is available with endpoint references, request/response 
                schemas, and code examples for TypeScript and Python.
              </p>
            </section>
          </div>

          {/* Footer */}
          <div className="mt-20 pt-8 border-t border-black/[0.04]">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
              <span className="font-pixel text-xs tracking-[0.25em] text-black/40">AGENTIC</span>
              <div className="flex items-center gap-6">
                <Link href="/privacy" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">Privacy</Link>
                <Link href="/terms" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">Terms</Link>
                <Link href="/docs" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">Docs</Link>
                <a href="https://github.com/shreeharsh-patil/Multi-Agent" target="_blank" rel="noopener noreferrer" className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">GitHub</a>
              </div>
            </div>
            <div className="mt-4">
              <span className="text-xs text-black/20">&copy; 2026 Agentic. All rights reserved.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
