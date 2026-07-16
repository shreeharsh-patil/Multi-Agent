"use client"

import React, { useRef, useEffect, useState, useCallback } from "react"
import { IntroAnimation, HERO_REVEAL_MS } from "@/app/landing/components/intro-animation"
import { PixelIcon } from "@/app/landing/components/pixel-icon"
import { LiveAgentFeed, LiveAgentCounter } from "@/app/landing/components/live-agent-feed"
import { RevealText } from "@/app/landing/components/reveal-text"
import { StackingAgentCards } from "@/app/landing/components/stacking-agent-cards"
import { MobileNav } from "@/app/landing/components/mobile-nav"
import { DevExSection } from "@/app/landing/components/devex-section"

function useInView(threshold = 0.15) {
  const ref = useRef<HTMLDivElement>(null)
  const [inView, setInView] = useState(false)
  useEffect(() => {
    const el = ref.current
    if (!el) return
    const obs = new IntersectionObserver(      ([e]) => { if (e?.isIntersecting) setInView(true) }, { threshold })
    obs.observe(el)
    return () => obs.disconnect()
  }, [threshold])
  return { ref, inView }
}

function BentoCard({ children, className = "", delay = 0 }: { children: React.ReactNode; className?: string; delay?: number }) {
  const { ref, inView } = useInView(0.1)
  return (
    <div
      ref={ref}
      className={`group relative rounded-2xl border border-black/[0.07] bg-white overflow-hidden transition-all duration-700 hover:border-black/[0.15] hover:bg-[#fafaf8] ${className}`}
      style={{
        opacity: inView ? 1 : 0,
        transform: inView ? "translateY(0)" : "translateY(28px)",
        transition: `opacity 0.7s ease ${delay}ms, transform 0.7s ease ${delay}ms, border-color 0.3s ease, background-color 0.3s ease`,
      }}
    >
      <div className="pointer-events-none absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500"
        style={{ background: "radial-gradient(400px circle at var(--mouse-x, 50%) var(--mouse-y, 50%), rgba(0,0,0,0.03), transparent 60%)" }}
      />
      {children}
    </div>
  )
}

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] tracking-widest font-sans text-black/40 bg-black/[0.04]">
      {children}
    </span>
  )
}

export default function LandingPage() {
  const [email, setEmail] = useState("")
  const [submitted, setSubmitted] = useState(false)
  const [heroReady, setHeroReady] = useState(false)
  const [videoReady, setVideoReady] = useState(false)
  const handleIntroDone = useCallback(() => { setHeroReady(true) }, [])

  useEffect(() => { const t = setTimeout(() => setVideoReady(true), HERO_REVEAL_MS); return () => clearTimeout(t) }, [])

  const handleMouse = (e: React.MouseEvent<HTMLDivElement>) => {
    const el = e.currentTarget
    const rect = el.getBoundingClientRect()
    el.style.setProperty("--mouse-x", `${e.clientX - rect.left}px`)
    el.style.setProperty("--mouse-y", `${e.clientY - rect.top}px`)
  }

  return (
    <div className="bg-[#F5F4F0] text-[#111] min-h-screen font-sans antialiased landing-page">
      <IntroAnimation onDone={handleIntroDone} />
      <MobileNav />

      <section className="relative h-screen overflow-hidden">
        <video
          autoPlay loop muted playsInline
          className="absolute inset-0 w-full h-full object-cover z-0"
          src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/agentic-hero-9yW3wnTNMfn2U6lsVhTTZSJFEvAoSj.mp4"
          style={{
            transform: videoReady ? "scale(1.05)" : "scale(0.85)",
            transition: "transform 2s cubic-bezier(0.16, 1, 0.3, 1)",
          }}
        />

        <div className="absolute inset-x-0 bottom-0 z-10 pointer-events-none" style={{ height: "65%", background: "linear-gradient(to top, #F5F4F0 0%, #F5F4F0 18%, rgba(245,244,240,0.85) 35%, rgba(245,244,240,0.5) 55%, rgba(245,244,240,0.15) 75%, transparent 100%)" }} />
        <div className="absolute inset-x-0 bottom-0 z-10 pointer-events-none" style={{ height: "20%", backdropFilter: "blur(12px)", WebkitBackdropFilter: "blur(12px)", maskImage: "linear-gradient(to top, black 0%, transparent 100%)", WebkitMaskImage: "linear-gradient(to top, black 0%, transparent 100%)" }} />
        <div className="absolute inset-x-0 bottom-0 z-10 pointer-events-none" style={{ height: "38%", backdropFilter: "blur(6px)", WebkitBackdropFilter: "blur(6px)", maskImage: "linear-gradient(to top, black 0%, transparent 100%)", WebkitMaskImage: "linear-gradient(to top, black 0%, transparent 100%)" }} />
        <div className="absolute inset-x-0 bottom-0 z-10 pointer-events-none" style={{ height: "55%", backdropFilter: "blur(2px)", WebkitBackdropFilter: "blur(2px)", maskImage: "linear-gradient(to top, black 0%, transparent 100%)", WebkitMaskImage: "linear-gradient(to top, black 0%, transparent 100%)" }} />

        <div className="h-20" />

        <div className="absolute inset-x-0 z-30 flex flex-col justify-end px-6 md:px-12 pb-4 max-w-3xl"
          style={{ top: '35vh', bottom: 0 }}
        >
          <h1
            className="text-4xl sm:text-5xl md:text-8xl font-light text-[#111] leading-[1.0] tracking-tight mb-4 sm:mb-8"
            style={{
              fontFamily: '"IBM Plex Sans", sans-serif',
              opacity: heroReady ? 1 : 0,
              filter: heroReady ? "blur(0px)" : "blur(24px)",
              transform: heroReady ? "translateY(0px)" : "translateY(32px)",
              transition: "opacity 1s cubic-bezier(0.16,1,0.3,1) 0ms, filter 1s cubic-bezier(0.16,1,0.3,1) 0ms, transform 1s cubic-bezier(0.16,1,0.3,1) 0ms",
            }}
          >
            Chat, research &amp;<br />create with AI<br />agents that<br />work with you.
          </h1>

          <p className="text-base text-black/55 leading-relaxed max-w-md mb-10"
            style={{
              opacity: heroReady ? 1 : 0,
              filter: heroReady ? "blur(0px)" : "blur(16px)",
              transform: heroReady ? "translateY(0px)" : "translateY(20px)",
              transition: `opacity 0.8s cubic-bezier(0.16,1,0.3,1) 100ms, filter 0.8s cubic-bezier(0.16,1,0.3,1) 100ms, transform 0.8s cubic-bezier(0.16,1,0.3,1) 100ms`,
            }}
          >
            Upload documents, research the web, generate quizzes, and build custom agents — all in one collaborative workspace.
          </p>

          <div className="flex gap-8 sm:gap-12">
            {[
              { value: "10K+", label: "Active users" },
              { value: "50+", label: "Specialized agents" },
              { value: "500K+", label: "Tasks completed" },
            ].map((stat, i) => (
              <div
                key={i}
                style={{
                  opacity: heroReady ? 1 : 0,
                  filter: heroReady ? "blur(0px)" : "blur(16px)",
                  transform: heroReady ? "translateY(0px)" : "translateY(20px)",
                  transition: `opacity 0.8s cubic-bezier(0.16,1,0.3,1) ${120 + i * 80}ms, filter 0.8s cubic-bezier(0.16,1,0.3,1) ${120 + i * 80}ms, transform 0.8s cubic-bezier(0.16,1,0.3,1) ${120 + i * 80}ms`,
                }}
              >
                <div className="text-3xl sm:text-4xl text-[#111] font-light tracking-tight">{stat.value}</div>
                <div className="text-xs text-black/40 tracking-widest uppercase mt-1">{stat.label}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section id="platform" className="py-32 px-6 md:px-12 lg:px-20">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16">
            <PixelIcon type="platform" size={40} />
            <div className="mt-4"><Tag>PLATFORM</Tag></div>
            <RevealText className="mt-5 text-4xl md:text-5xl lg:text-6xl font-light tracking-tight leading-[1.05]">
              {"Everything you need\nto work with agents."}
            </RevealText>
          </div>

          <div className="grid grid-cols-12 grid-rows-auto gap-3" onMouseMove={handleMouse}>
            <BentoCard className="col-span-12 p-8 min-h-[200px] flex flex-col justify-between relative overflow-hidden" delay={0}>
              <img src="/images/arc.png" alt="" aria-hidden="true" className="absolute inset-0 w-full h-full object-cover" style={{ objectPosition: "center 70%" }} />
              <div className="absolute inset-0" style={{ maskImage: "linear-gradient(to bottom, transparent 45%, black 100%)", WebkitMaskImage: "linear-gradient(to bottom, transparent 45%, black 100%)", backdropFilter: "blur(16px)", WebkitBackdropFilter: "blur(16px)" }} />
              <div className="absolute inset-0" style={{ background: "linear-gradient(to bottom, transparent 35%, rgba(245,244,240,0.3) 50%, rgba(245,244,240,0.75) 65%, rgba(245,244,240,0.95) 80%, rgb(245,244,240) 100%)" }} />
              <div className="relative z-10">
                <div className="w-10 h-10 rounded-xl border border-black/10 bg-white/60 flex items-center justify-center mb-6" style={{ backdropFilter: "blur(8px)" }}>
                  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3"/><path d="m4.93 4.93 2.12 2.12M16.95 16.95l2.12 2.12M4.93 19.07l2.12-2.12M16.95 7.05l2.12-2.12"/></svg>
                </div>
                <h3 className="text-xl font-light mb-3">Multi-Agent Chat</h3>
                <p className="text-sm text-black/45 leading-relaxed max-w-sm">Talk to multiple specialized agents in one conversation. Research the web, query your documents, generate quizzes, and write code — all without switching tabs.</p>
              </div>
            </BentoCard>

            <BentoCard className="col-span-12 md:col-span-4 p-8 min-h-[200px]" delay={120}>
              <div className="w-10 h-10 rounded-xl border border-black/10 flex items-center justify-center mb-5">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>
              </div>
              <h3 className="text-lg font-light mb-2">Knowledge Base (RAG)</h3>
              <p className="text-sm text-black/45 leading-relaxed">Upload PDFs, documents, and images. Query your knowledge base with AI-powered search and get cited answers from your own data.</p>
            </BentoCard>

            <BentoCard className="col-span-12 md:col-span-4 p-8 min-h-[200px]" delay={160}>
              <div className="w-10 h-10 rounded-xl border border-black/10 flex items-center justify-center mb-5">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><rect x="3" y="3" width="18" height="18" rx="2"/><path d="M8 10h8M8 14h5"/></svg>
              </div>
              <h3 className="text-lg font-light mb-2">Study & Quiz Tools</h3>
              <p className="text-sm text-black/45 leading-relaxed">Generate notes, flashcards, and revision materials. Create practice quizzes and exams with answer keys and explanations.</p>
            </BentoCard>

            <BentoCard className="col-span-12 md:col-span-4 p-8 min-h-[200px]" delay={200}>
              <div className="w-10 h-10 rounded-xl border border-black/10 flex items-center justify-center mb-5">
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
              </div>
              <h3 className="text-lg font-light mb-2">Custom Agents</h3>
              <p className="text-sm text-black/45 leading-relaxed">Create your own specialized agents with custom instructions, tools, and knowledge sources. Deploy them instantly into your workspace.</p>
            </BentoCard>
          </div>
        </div>
      </section>

      <section id="agents" className="py-32 px-6 md:px-12 lg:px-20 border-t border-black/[0.06]">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-8 mb-16">
            <div>
              <PixelIcon type="agents" size={40} />
              <div className="mt-4"><Tag>AGENT TYPES</Tag></div>
              <RevealText className="mt-5 text-4xl md:text-5xl font-light tracking-tight leading-[1.05]">
                {"Specialized agents\nfor every task."}
              </RevealText>
            </div>
            <p className="text-sm text-black/45 leading-relaxed max-w-xs">Each agent is purpose-built for a specific domain. Use them individually or combine them in a single conversation.</p>
          </div>
          <StackingAgentCards />
        </div>
      </section>

      <section id="workflow" className="py-32 px-6 md:px-12 lg:px-20 border-t border-black/[0.06] overflow-hidden">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16">
            <PixelIcon type="workflow" size={40} />
            <div className="mt-4"><Tag>WORKFLOW</Tag></div>
            <RevealText className="mt-5 text-4xl md:text-5xl font-light tracking-tight leading-[1.05]">
              {"From curiosity to answers\nin four steps."}
            </RevealText>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-4 gap-3" onMouseMove={handleMouse}>
            {[
              { n: "01", title: "Upload",  desc: "Upload PDFs, documents, and images to your knowledge base. The RAG engine indexes everything automatically.", delay: 0,   img: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/define-5aafAmGBrxZpOqJ3XLHY3n3qzC2I5K.png" },
              { n: "02", title: "Ask", desc: "Chat with any agent — research the web, query documents, generate code, or create study materials in natural language.", delay: 80,  img: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/compose-5RT5VR4f1Y3GoFmovqTKLTG4UXp3g2.png" },
              { n: "03", title: "Create",    desc: "Generate quizzes, flashcards, study plans, reports, and notes from your conversations and documents.", delay: 140, img: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/test-zm8guZwxJHtwWsJ7XO4B0CF7GzlNK8.png" },
              { n: "04", title: "Build",  desc: "Create custom agents with your own instructions and tools. Add them to your workspace and share with your team.", delay: 200, img: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/deploy-an8fgHSLzniojkcmRyGGIFQUJF9T5J.png" },
            ].map((step) => (
              <BentoCard key={step.n} className="relative overflow-hidden flex flex-col min-h-[320px]" delay={step.delay}>
                <div className="absolute inset-x-0 top-0 h-56 pointer-events-none">
                  <img src={step.img} alt={step.title} className="w-full h-full object-cover object-top" style={{ maskImage: "linear-gradient(to bottom, black 0%, black 30%, transparent 80%)", WebkitMaskImage: "linear-gradient(to bottom, black 0%, black 30%, transparent 80%)" }} />
                </div>
                <div className="relative z-10 p-7"><span className="font-pixel text-[11px] text-black/20 tracking-widest block">{step.n}</span></div>
                <div className="relative z-10 px-7 pb-7 mt-auto pt-16">
                  <h3 className="text-2xl font-light mb-3">{step.title}</h3>
                  <p className="text-sm text-black/45 leading-relaxed">{step.desc}</p>
                </div>
              </BentoCard>
            ))}
          </div>
        </div>
      </section>

      <section id="integrations" className="py-32 px-6 md:px-12 lg:px-20 border-t border-black/[0.06]">
        <div className="max-w-6xl mx-auto">
          <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-8 mb-16">
            <div>
              <PixelIcon type="integrations" size={40} />
              <div className="mt-4"><Tag>INTEGRATIONS</Tag></div>
              <RevealText className="mt-5 text-4xl md:text-5xl font-light tracking-tight leading-[1.05]">
              {"Connect your tools.\nExtend your agents."}
            </RevealText>
            </div>
            <p className="text-sm text-black/45 leading-relaxed max-w-xs">Integrate with Google Drive, Google Calendar, and web search. Build custom tools with our SDK and API in minutes.</p>
          </div>

          <div className="rounded-2xl overflow-hidden border border-black/[0.07] flex flex-col md:block md:relative" onMouseMove={handleMouse}>
            <div className="relative w-full h-[280px] md:h-[480px] shrink-0">
              <img src="https://hebbkx1anhila5yf.public.blob.vercel-storage.com/Org%20Arc%20-%20Upscaled-Sk90jShfu7nltLnhoQbaMJC1YaQKuU.png" alt="Agent orchestration architecture" className="absolute inset-0 w-full h-full object-cover object-center" />
            </div>
            <div className="flex flex-col gap-3 p-4 md:absolute md:bottom-4 md:right-4 md:p-0 md:w-72">
              <div className="rounded-xl border border-white/50 p-6" style={{ backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)", background: "rgba(255,255,255,0.60)" }}>
                <Tag>API</Tag>
                <h3 className="mt-3 text-lg font-light mb-2">REST & WebSocket API</h3>
                <p className="text-xs text-black/45 leading-relaxed mb-4">Query agents, search knowledge bases, and stream responses through a simple API.</p>
                <div className="bg-black/[0.05] rounded-lg border border-black/[0.07] p-3 font-mono text-[11px] text-black/50 leading-relaxed">
                  <span className="text-black/25"># query knowledge base</span><br />
                  <span className="text-blue-600/70">curl</span> -X POST <span className="text-amber-700/70">/api/knowledge/query</span><br />
                  -H <span className="text-green-700/70">&quot;Authorization: Bearer $KEY&quot;</span> \<br />
                  -d <span className="text-green-700/70">{`{"query": "explain RAG"}`}</span>
                </div>
              </div>
              <div className="rounded-xl border border-white/50 p-6" style={{ backdropFilter: "blur(24px)", WebkitBackdropFilter: "blur(24px)", background: "rgba(255,255,255,0.60)" }}>
                <div className="flex items-center gap-2 mb-2">
                  <div className="w-2 h-2 rounded-full bg-emerald-500/80 animate-pulse" />
                  <span className="text-xs text-black/40 tracking-widest">LIVE API</span>
                </div>
                <p className="text-sm text-black/45">Full REST + WebSocket API. Stream agent outputs directly into your product.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="security" className="py-32 px-6 md:px-12 lg:px-20 border-t border-black/[0.06]">
        <div className="max-w-6xl mx-auto">
          <div className="mb-16">
            <PixelIcon type="platform" size={40} />
            <div className="mt-4"><Tag>SECURITY</Tag></div>
            <RevealText className="mt-5 text-4xl md:text-5xl font-light tracking-tight leading-[1.05]">
              {"Enterprise-grade\nfrom day one."}
            </RevealText>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            <div className="space-y-6">
              <p className="text-sm text-black/45 leading-relaxed">Every action is logged, every decision is traceable. Built for teams that need compliance without compromise.</p>
              <div className="space-y-4">
                {[
                  { label: "SOC 2 Type II", desc: "Independently audited security controls" },
                  { label: "Full Audit Trail", desc: "Every decision logged with full traceability" },
                  { label: "Real-time Observability", desc: "Monitor, debug, and replay any execution" },
                ].map((item) => (
                  <div key={item.label} className="flex gap-4">
                    <div className="w-1 bg-black/10 rounded-full shrink-0" />
                    <div>
                      <h3 className="text-sm font-light mb-1">{item.label}</h3>
                      <p className="text-xs text-black/35">{item.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="pt-4 flex flex-col gap-2">
                {["SOC 2", "GDPR", "HIPAA Ready", "ISO 27001"].map((badge) => (
                  <div key={badge} className="flex items-center gap-2 text-xs text-black/25">
                    <span className="w-1 h-1 rounded-full bg-black/25" />{badge}
                  </div>
                ))}
              </div>
            </div>

            <BentoCard className="p-6 lg:row-span-1" delay={0}>
              <div className="text-xs text-black/30 tracking-widest uppercase mb-4">Live Audit Trail</div>
              <div className="space-y-2">
                {[
                  { time: "12:34:21", action: "agent_executed", status: "success" },
                  { time: "12:34:18", action: "decision_logged", status: "success" },
                  { time: "12:34:15", action: "tool_called", status: "success" },
                  { time: "12:34:12", action: "memory_updated", status: "success" },
                  { time: "12:34:09", action: "output_generated", status: "success" },
                ].map((log, i) => (
                  <div key={i} className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-black/[0.02] hover:bg-black/[0.04] transition-colors border border-black/[0.04] group cursor-pointer"
                    style={{ animation: `fadeInUp 0.5s cubic-bezier(0.16,1,0.3,1) ${i * 80}ms both` }}
                  >
                    <span className="text-[10px] text-black/25 font-mono min-w-[60px]">{log.time}</span>
                    <span className="text-[11px] text-black/50 font-light flex-1">{log.action}</span>
                    <span className="w-1.5 h-1.5 rounded-full bg-green-500/60 group-hover:bg-green-500 transition-colors" />
                  </div>
                ))}
              </div>
              <style>{`
                @keyframes fadeInUp { from { opacity: 0; transform: translateY(8px); } to { opacity: 1; transform: translateY(0); } }
              `}</style>
            </BentoCard>
          </div>
        </div>
      </section>

      <DevExSection />

      <section className="py-0 border-t border-black/[0.06] overflow-hidden select-none">
        <div className="flex border-b border-black/[0.06]" style={{ animation: "marquee-left 28s linear infinite" }}>
          {[...Array(3)].map((_, rep) => (
            <div key={rep} className="flex shrink-0">
              {["RAG Search", "Web Research", "Quiz Generation", "Code Writing", "Note Taking", "Study Planning", "Flashcard Creation", "Document Analysis", "Report Writing", "Google Drive"].map((cap) => (
                <div key={cap} className="flex items-center gap-6 px-10 py-5 border-r border-black/[0.06] shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-black/20 shrink-0" />
                  <span className="text-sm text-black/45 whitespace-nowrap tracking-wide">{cap}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
        <div className="flex" style={{ animation: "marquee-right 22s linear infinite" }}>
          {[...Array(3)].map((_, rep) => (
            <div key={rep} className="flex shrink-0">
              {["MCQ Generation", "Exam Creation", "Revision Notes", "Source Citation", "Knowledge Graph", "Task Management", "Calendar Sync", "File Upload", "Custom Tools", "Multi-Agent Chat"].map((cap) => (
                <div key={cap} className="flex items-center gap-6 px-10 py-5 border-r border-black/[0.06] shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-black/12 shrink-0" />
                  <span className="text-sm text-black/30 whitespace-nowrap tracking-wide">{cap}</span>
                </div>
              ))}
            </div>
          ))}
        </div>
      </section>

      <section id="live" className="py-32 px-6 md:px-12 lg:px-20 border-t border-black/[0.06]">
        <div className="max-w-6xl mx-auto">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-20 items-center">
            <div>
              <PixelIcon type="agents" size={40} />
              <div className="mt-4"><Tag>LIVE RIGHT NOW</Tag></div>
              <RevealText className="mt-5 text-4xl md:text-5xl lg:text-6xl font-light tracking-tight leading-[1.05]">
                {"Agents helping you\nright now, in real time."}
              </RevealText>
              <p className="mt-6 text-base text-black/40 leading-relaxed max-w-sm">Our platform processes thousands of queries daily — from document searches to quiz generations to web research tasks.</p>
              <div className="mt-10 flex items-end gap-2">
                <LiveAgentCounter />
                <span className="text-black/30 text-sm mb-1 tracking-wide">queries processed today</span>
              </div>
            </div>
            <div className="relative">
              <LiveAgentFeed />
            </div>
          </div>
        </div>
      </section>

      <section id="pricing" className="py-32 px-6 md:px-12 lg:px-20 border-t border-black/[0.06]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16 flex flex-col items-center">
            <PixelIcon type="pricing" size={40} />
            <div className="mt-4"><Tag>PRICING</Tag></div>
            <RevealText className="mt-5 text-4xl md:text-5xl font-light tracking-tight leading-[1.05]">
              {"Start free. Scale as you go."}
            </RevealText>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3" onMouseMove={handleMouse}>
            {[
              { name: "Starter", price: "Free", sub: "Get started instantly", features: ["All built-in agents", "500 queries/mo", "RAG knowledge base", "Community support"], delay: 0 },
              { name: "Pro", price: "$19", period: "/mo", sub: "For power users", features: ["Unlimited queries", "Custom agents", "Google Drive sync", "Priority support", "Advanced RAG", "Study tools"], highlight: true, delay: 80 },
              { name: "Team", price: "$49", period: "/mo", sub: "For teams & classrooms", features: ["Everything in Pro", "Team workspaces", "Shared knowledge bases", "Admin dashboard", "Usage analytics", "Dedicated support"], delay: 140 },
            ].map((plan) => (
              <BentoCard key={plan.name} className={`p-8 flex flex-col ${plan.highlight ? "border-black/20 bg-[#F0EEE8]" : ""}`} delay={plan.delay}>
                <div className="mb-8">
                  <div className="font-pixel text-[11px] tracking-widest text-black/40 mb-4">{plan.name}</div>
                  <div className="flex items-baseline gap-1 mb-1">
                    <span className="text-4xl font-light">{plan.price}</span>
                    {plan.period && <span className="text-black/40 text-sm">{plan.period}</span>}
                  </div>
                  <p className="text-xs text-black/35 tracking-wide">{plan.sub}</p>
                </div>
                <ul className="space-y-3 flex-1 mb-8">
                  {plan.features.map(f => (
                    <li key={f} className="flex items-center gap-3 text-sm text-black/55">
                      <div className="w-1 h-1 rounded-full bg-black/25 shrink-0" />{f}
                    </li>
                  ))}
                </ul>
                <a href="/login" className="w-full block">
                  <button className={`w-full py-3 rounded-xl text-sm tracking-widest transition-all duration-200 ${plan.highlight ? "bg-[#111] text-white hover:bg-[#333]" : "border border-black/10 text-black/60 hover:border-black/25 hover:text-black hover:bg-black/[0.04]"}`}>
                    {plan.name === "Team" ? "CONTACT SALES" : "GET STARTED"}
                  </button>
                </a>
              </BentoCard>
            ))}
          </div>
        </div>
      </section>

      <section className="relative py-32 px-6 md:px-12 lg:px-20 border-t border-black/[0.06] overflow-hidden">
        <img src="/images/footer.png" alt="" aria-hidden="true" className="absolute bottom-0 left-0 w-full object-cover object-bottom pointer-events-none select-none" style={{ opacity: 0.85 }} />
        <div className="absolute inset-0 pointer-events-none" style={{ maskImage: "linear-gradient(to top, transparent 0%, black 55%)", WebkitMaskImage: "linear-gradient(to top, transparent 0%, black 55%)", backdropFilter: "blur(18px)", WebkitBackdropFilter: "blur(18px)" }} />
        <div className="absolute inset-0 pointer-events-none" style={{ background: "linear-gradient(to top, rgb(245,244,240) 0%, rgba(245,244,240,0.92) 18%, rgba(245,244,240,0.55) 35%, transparent 55%)" }} />
        <div className="relative z-10 max-w-2xl mx-auto text-center">
          <h2 className="text-4xl md:text-5xl lg:text-6xl font-light tracking-tight leading-[1.05] mb-6">Start working with<br />AI agents today.</h2>
          <p className="text-sm text-black/45 leading-relaxed mb-10">Join users leveraging AI agents for research, learning, and productivity.</p>
          {!submitted ? (
            <form onSubmit={e => { e.preventDefault(); if (email) setSubmitted(true) }} className="flex flex-col sm:flex-row gap-2 max-w-md mx-auto">
              <input type="email" placeholder="your@email.com" value={email} onChange={e => setEmail(e.target.value)} required
                className="flex-1 bg-white border border-black/10 rounded-xl px-4 py-3 text-sm text-[#111] placeholder:text-black/25 focus:outline-none focus:border-black/25 transition-colors" />
              <button type="submit" className="px-8 py-3 bg-[#111] text-white text-sm rounded-xl hover:bg-[#333] transition-colors tracking-widest font-medium">JOIN</button>
            </form>
          ) : (
            <div className="inline-flex items-center gap-2 px-6 py-3 rounded-xl border border-emerald-600/20 bg-emerald-50 text-emerald-700 text-sm">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
              {"You're on the list. We'll be in touch."}
            </div>
          )}
        </div>
      </section>

      <footer className="py-10 px-6 md:px-12 lg:px-20 border-t border-black/[0.06]">
        <div className="max-w-6xl mx-auto flex flex-col md:flex-row items-start md:items-center justify-between gap-8">
          <span className="font-pixel text-xs tracking-[0.25em] text-black/50">AGENTIC</span>
          <div className="flex flex-wrap items-center gap-x-8 gap-y-3">
            {[
              { label: "Platform",     href: "#platform" },
              { label: "Agents",       href: "#agents" },
              { label: "Workflow",     href: "#workflow" },
              { label: "Integrations", href: "#integrations" },
              { label: "Live",         href: "#live" },
              { label: "Pricing",      href: "#pricing" },
            ].map(l => (
              <a key={l.label} href={l.href} className="text-xs text-black/35 hover:text-black/70 transition-colors tracking-widest">{l.label}</a>
            ))}
          </div>
          <div className="flex items-center gap-6">
            {[
              { label: "Privacy", href: "#" },
              { label: "Terms",   href: "#" },
              { label: "Docs",    href: "#" },
              { label: "GitHub",  href: "#" },
            ].map(l => (
              <a key={l.label} href={l.href} className="text-xs text-black/25 hover:text-black/55 transition-colors tracking-widest">{l.label}</a>
            ))}
          </div>
        </div>
        <div className="max-w-6xl mx-auto mt-8 pt-6 border-t border-black/[0.04]">
          <span className="text-xs text-black/20">&copy; 2026 Agentic. All rights reserved.</span>
        </div>
      </footer>
    </div>
  )
}
