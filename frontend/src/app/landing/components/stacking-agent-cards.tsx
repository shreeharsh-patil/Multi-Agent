"use client"

import { useEffect, useRef, useState } from "react"

const AGENTS = [
  {
    label: "DEEP RESEARCHER",
    title: "Web & multi-page academic research",
    desc: "Autonomously crawls the web, extracts structured data, and synthesizes multi-page research reports with numbered citations.",
    stats: [{ v: "Live", l: "web crawling" }, { v: "Multi-page", l: "report export" }],
    img: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/researcher-CvhqOuV6irGwBOnJoTGFlXdbyYBRjb.png",
  },
  {
    label: "CODER",
    title: "Code generation & review",
    desc: "Writes, refactors, and reviews code across 40+ languages. Fixes bugs, explains logic, and formats snippets cleanly.",
    stats: [{ v: "40+ Languages", l: "supported" }, { v: "Instant", l: "code review" }],
    img: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/coder-9bItvCegU6TXUqbX3tUXGBAtvkBkXp.png",
  },
  {
    label: "DATA ANALYST",
    title: "Data analysis & insights",
    desc: "Analyzes uploaded CSV and Excel datasets, generates statistical charts, tables, and surfaces key insights.",
    stats: [{ v: "CSV & Excel", l: "data analysis" }, { v: "Charts", l: "visualization" }],
    img: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/analyst-Ysxnqg7Fpy2cfA56PiIttv1KximMhT.png",
  },
  {
    label: "GOOGLE EXECUTOR",
    title: "Google Workspace automation",
    desc: "Integrates with Google Drive, Google Calendar, Google Contacts, and Gmail to manage schedule and files.",
    stats: [{ v: "OAuth 2.0", l: "Google Integration" }, { v: "4 Suite Apps", l: "connected" }],
    img: "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/executor-o1q6509qMLXMtpBIGo49vcgOu34sI1.png",
  },
]

const STICKY_TOP   = 80   // matches top: 80px on first card
const STICKY_STEP  = 16   // each card stacks 16px lower
const SCALE_STEP   = 0.04 // scale reduction per card stacked on top
const OFFSET_STEP  = 8    // px pushed down per card stacked on top

function Tag({ children }: { children: React.ReactNode }) {
  return (
    <span className="inline-flex items-center px-3 py-1 rounded-full text-[11px] tracking-widest font-sans text-black/40 bg-black/[0.04]">
      {children}
    </span>
  )
}

export function StackingAgentCards() {
  const cardRefs = useRef<(HTMLDivElement | null)[]>([])
  // depth[i] = 0..N how many cards are currently stacked on top of card i
  const [depth, setDepth] = useState<number[]>(AGENTS.map(() => 0))

  useEffect(() => {
    function onScroll() {
      const nextDepth = AGENTS.map((_, i) => {
        // Count how many cards j > i are currently in sticky position (i.e. have scrolled past card i)
        let count = 0
        for (let j = i + 1; j < AGENTS.length; j++) {
          const el = cardRefs.current[j]
          if (!el) continue
          const rect = el.getBoundingClientRect()
          const stickyTopJ = STICKY_TOP + j * STICKY_STEP
          // Card j is "on top of" card i when it has reached its sticky position
          if (rect.top <= stickyTopJ + 2) count++
        }
        return count
      })
      setDepth(nextDepth)
    }

    window.addEventListener("scroll", onScroll, { passive: true })
    onScroll()
    return () => window.removeEventListener("scroll", onScroll)
  }, [])

  return (
    <div className="flex flex-col" style={{ perspective: "1400px", perspectiveOrigin: "50% 0%" }}>
      {AGENTS.map((agent, i) => {
        const d         = depth[i] ?? 0
        const scale     = 1 - d * SCALE_STEP
        const translateY = d * OFFSET_STEP

        return (
          <div
            key={agent.label}
            ref={el => { cardRefs.current[i] = el }}
            className="sticky mb-4"
            style={{ top: `${STICKY_TOP + i * STICKY_STEP}px`, zIndex: 10 + i }}
          >
            <div
              style={{
                transform:      `scale(${scale}) translateY(${translateY}px)`,
                transformOrigin: "top center",
                transition:     "transform 0.3s cubic-bezier(0.16,1,0.3,1)",
                willChange:     "transform",
              }}
            >
              <div className="group relative bg-[#faf9f7] rounded-2xl border border-black/[0.07] overflow-hidden cursor-pointer">

                {/* ── MOBILE: image top, fades out at bottom ── */}
                {agent.img && (
                  <div className="relative h-44 w-full pointer-events-none min-[390px]:h-52 md:hidden">
                    <img
                      src={agent.img}
                      alt={agent.label}
                      className="absolute inset-0 w-full h-full object-cover object-center"
                      style={{
                        maskImage: "linear-gradient(to bottom, black 0%, black 35%, transparent 85%)",
                        WebkitMaskImage: "linear-gradient(to bottom, black 0%, black 35%, transparent 85%)",
                      }}
                    />
                  </div>
                )}

                {/* ── DESKTOP: image right, fades out at left (absolute) ── */}
                {agent.img && (
                  <div className="hidden md:block absolute inset-y-0 right-0 w-1/2 pointer-events-none">
                    <img
                      src={agent.img}
                      alt={agent.label}
                      className="w-full h-full object-cover object-center"
                    />
                    <div
                      className="absolute inset-0"
                      style={{
                        background: "linear-gradient(to right, #faf9f7 0%, transparent 55%)",
                      }}
                    />
                  </div>
                )}

                {/* Text content */}
                <div
                  className="relative z-10 p-5 sm:p-6 md:p-8"
                  style={{ maxWidth: agent.img ? undefined : "100%" }}
                  // On desktop limit to left 60% so text doesn't overlap image
                >
                  <div className="md:max-w-[60%]">
                    <div className="mb-5 flex min-w-0 flex-wrap items-start justify-between gap-2 sm:mb-6">
                      <Tag>{agent.label}</Tag>
                    </div>
                    <h3 className="text-xl font-light mb-3">{agent.title}</h3>
                    <p className="text-sm text-black/45 leading-relaxed mb-8">{agent.desc}</p>
                  </div>
                  <div className="flex flex-wrap gap-x-6 gap-y-3 border-t border-black/[0.06] pt-5 sm:gap-8 sm:pt-6">
                    {agent.stats.map(s => (
                      <div key={s.l}>
                        <div className="text-xl font-light sm:text-2xl">{s.v}</div>
                        <div className="text-[11px] text-black/35 tracking-widest mt-0.5">{s.l}</div>
                      </div>
                    ))}
                  </div>
                </div>

              </div>
            </div>
          </div>
        )
      })}
    </div>
  )
}
