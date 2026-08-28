"use client"

import { useEffect, useState } from "react"

const NAV_LINKS = [
  { label: "Platform",     href: "#platform" },
  { label: "Agents",       href: "#agents" },
  { label: "Workflow",     href: "#workflow" },
  { label: "Integrations", href: "#integrations" },
  { label: "Pricing",      href: "#pricing" },
]

const NAV_STYLE = {
  backdropFilter: "blur(16px)",
  WebkitBackdropFilter: "blur(16px)",
  background: "rgba(245,244,240,0.30)",
  boxShadow: "0 8px 32px rgba(0,0,0,0.08), 0 2px 8px rgba(0,0,0,0.06)",
} as const

export function MobileNav() {
  const [open, setOpen] = useState(false)

  const close = () => setOpen(false)

  useEffect(() => {
    if (!open) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    const onEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false)
    }
    window.addEventListener("keydown", onEscape)
    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener("keydown", onEscape)
    }
  }, [open])

  return (
    <div className="pointer-events-none fixed inset-x-0 top-[max(0.75rem,env(safe-area-inset-top))] z-50 flex justify-center px-3 sm:px-4">
      <div className="pointer-events-auto w-full max-w-3xl">

        {/* Main bar */}
        <nav
          className="flex min-h-14 min-w-0 items-center justify-between rounded-2xl border border-black/[0.06] px-4 py-2 sm:px-5 sm:py-3"
          style={NAV_STYLE}
        >
          <span className="font-pixel text-xs tracking-[0.25em] text-black/70">AGENTIC</span>

          {/* Desktop links */}
          <div className="hidden md:flex items-center gap-7" style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
            {NAV_LINKS.map(l => (
              <a
                key={l.label}
                href={l.href}
                className="text-[11px] text-black/60 hover:text-black transition-colors duration-200 tracking-wide"
              >
                {l.label}
              </a>
            ))}
          </div>

          <div className="flex items-center gap-2">
            <a href="/login" className="text-[11px] px-4 py-2 rounded-xl border border-black/10 text-black/60 hover:text-black hover:border-black/20 hover:bg-black/[0.03] transition-all duration-200 tracking-wide hidden md:block" style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
              START BUILDING
            </a>

            {/* Burger — mobile only */}
            <button
              onClick={() => setOpen(v => !v)}
              className="flex h-11 w-11 flex-col items-center justify-center gap-[5px] rounded-lg transition-colors hover:bg-black/[0.04] md:hidden"
              aria-label={open ? "Close menu" : "Open menu"}
              aria-expanded={open}
              aria-controls="landing-mobile-menu"
            >
              <span
                className="block h-px bg-black/60 transition-all duration-300 origin-center"
                style={{
                  width: "18px",
                  transform: open ? "translateY(6px) rotate(45deg)" : "none",
                }}
              />
              <span
                className="block h-px bg-black/60 transition-all duration-300"
                style={{
                  width: "18px",
                  opacity: open ? 0 : 1,
                  transform: open ? "scaleX(0)" : "none",
                }}
              />
              <span
                className="block h-px bg-black/60 transition-all duration-300 origin-center"
                style={{
                  width: "18px",
                  transform: open ? "translateY(-6px) rotate(-45deg)" : "none",
                }}
              />
            </button>
          </div>
        </nav>

        {/* Mobile dropdown */}
        <div
          id="landing-mobile-menu"
          className="mt-2 max-h-[calc(100dvh-5rem)] overflow-y-auto transition-all duration-300 ease-in-out md:hidden"
          style={{ maxHeight: open ? "320px" : "0px", opacity: open ? 1 : 0 }}
        >
          <div
            className="rounded-2xl border border-black/[0.06] px-2 py-2 flex flex-col"
            style={NAV_STYLE}
          >
            {NAV_LINKS.map(l => (
              <a
                key={l.label}
                href={l.href}
                onClick={close}
                className="flex min-h-11 items-center rounded-xl px-4 py-3 text-sm tracking-wide text-black/60 transition-colors hover:bg-black/[0.03] hover:text-black"
                style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}
              >
                {l.label}
              </a>
            ))}
            <div className="mt-1 px-2 pb-1">
              <a href="/login" className="w-full text-center text-[11px] px-4 py-2.5 rounded-xl border border-black/10 text-black/60 hover:text-black hover:border-black/20 hover:bg-black/[0.03] transition-all duration-200 tracking-wide block" style={{ fontFamily: "system-ui, -apple-system, sans-serif" }}>
                START BUILDING
              </a>
            </div>
          </div>
        </div>

      </div>
    </div>
  )
}
