'use client'

import { useEffect, useRef } from 'react'

const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

/** Minimum interval between health pings (5 minutes). */
const PING_INTERVAL_MS = 5 * 60 * 1000

/**
 * Invisible component that periodically pings the backend `/api/health`
 * endpoint to keep the Render free-tier server warm.  Cold starts can take
 * 15–60 s, during which all API calls fail with `ERR_INTERNET_DISCONNECTED`
 * or `ERR_QUIC_PROTOCOL_ERROR`.
 *
 * The first ping fires immediately on mount so the server wakes up as soon
 * as the user opens the app.
 */
export function HealthPing() {
  const pingedRef = useRef(false)

  useEffect(() => {
    const ping = () => {
      fetch(`${BACKEND_URL}/api/health`, {
        method: 'GET',
        // Short timeout — if the server is already warm this resolves fast.
        // On cold start the request itself serves as the wake-up signal.
        signal: AbortSignal.timeout(30_000),
      }).catch(() => {
        // Silently ignored — the purpose is to warm the server, not to
        // report health status to the user.
      })
    }

    // Ping immediately on first mount
    if (!pingedRef.current) {
      pingedRef.current = true
      ping()
    }

    // Then keep the server warm with periodic pings
    const interval = setInterval(ping, PING_INTERVAL_MS)
    return () => clearInterval(interval)
  }, [])

  // Render nothing — this is a purely side-effect component
  return null
}
