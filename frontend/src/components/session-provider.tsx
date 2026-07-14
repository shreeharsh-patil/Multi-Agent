'use client'

import { useEffect, useRef } from 'react'
import { SessionProvider as NextAuthSessionProvider, useSession } from 'next-auth/react'
import { api } from '@/lib/api'
import { getAccessToken, setAccessToken } from '@/lib/auth-store'
import type { ReactNode } from 'react'

/**
 * Inner component that runs inside NextAuth SessionProvider
 * and exchanges the Google OAuth session for a backend JWT.
 */
function AuthTokenBridge() {
  const { data: session, status } = useSession()
  const exchanged = useRef(false)

  useEffect(() => {
    if (status !== 'authenticated' || !session?.user?.email) return
    if (exchanged.current) return

    const existing = getAccessToken()
    if (existing) {
      exchanged.current = true
      return
    }

    const exchange = async () => {
      try {
        const res = await api.auth.login({
          email: session.user.email!,
          name: session.user.name ?? session.user.email!,
          image: session.user.image ?? undefined,
          google_id: (session.user as { id?: string }).id ?? undefined,
        })
        if (res.success && res.data?.access_token) {
          setAccessToken(res.data.access_token)
          exchanged.current = true
        }
      } catch {
        // Silently fail
      }
    }

    exchange()
  }, [status, session])

  return null
}

export function SessionProvider({ children }: { children: ReactNode }) {
  return (
    <NextAuthSessionProvider>
      <AuthTokenBridge />
      {children}
    </NextAuthSessionProvider>
  )
}
