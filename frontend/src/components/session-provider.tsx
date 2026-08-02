'use client'

import { useEffect, useRef } from 'react'
import { SessionProvider as NextAuthSessionProvider, useSession } from 'next-auth/react'
import { api } from '@/lib/api'
import { clearAccessToken, getAccessToken, setAccessToken } from '@/lib/auth-store'
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

    const exchange = async () => {
      try {
        const res = await api.auth.login({
          email: session.user.email!,
          name: session.user.name ?? session.user.email!,
          image: session.user.image ?? undefined,
          google_id: (session.user as { id?: string }).id ?? undefined,
          access_token: (session as any).accessToken ?? undefined,
        })
        if (res.success && res.data?.access_token) {
          setAccessToken(res.data.access_token)
          exchanged.current = true
          window.dispatchEvent(new Event('refresh-conversations-list'))
        }
      } catch {
        // Silently fail
      }
    }

    const existing = getAccessToken()
    if (existing) {
      // Validate persisted tokens so a deleted/stale backend user does not
      // leave features such as Memory stuck on "User not found".
      api.auth.getMe().then((res) => {
        if (res.success) {
          exchanged.current = true
          window.dispatchEvent(new Event('refresh-conversations-list'))
        } else {
          clearAccessToken()
          exchange()
        }
      }).catch(() => {
        clearAccessToken()
        exchange()
      })
      return
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
