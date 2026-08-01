import type { NextAuthOptions } from 'next-auth'
import type { JWT } from 'next-auth/jwt'
import GoogleProvider from 'next-auth/providers/google'
import CredentialsProvider from 'next-auth/providers/credentials'

/**
 * Refresh an expired Google OAuth access token using the stored refresh token.
 * Google access tokens expire after ~1 hour; without this the Drive/Calendar
 * calls start failing with 401 once that hour passes.
 */
async function refreshGoogleAccessToken(token: JWT): Promise<JWT> {
  try {
    const res = await fetch('https://oauth2.googleapis.com/token', {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: new URLSearchParams({
        client_id: process.env.GOOGLE_CLIENT_ID!,
        client_secret: process.env.GOOGLE_CLIENT_SECRET!,
        grant_type: 'refresh_token',
        refresh_token: token.refreshToken as string,
      }),
    })
    const refreshed = await res.json()
    if (!res.ok) throw refreshed

    return {
      ...token,
      accessToken: refreshed.access_token,
      expiresAt: Date.now() + refreshed.expires_in * 1000,
      // Google may not return a new refresh token; keep the old one.
      refreshToken: refreshed.refresh_token ?? token.refreshToken,
      error: undefined,
    }
  } catch {
    return { ...token, error: 'RefreshAccessTokenError' }
  }
}

export const authOptions: NextAuthOptions = {
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
      authorization: {
        params: {
          scope: 'openid email profile https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/tasks https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/contacts.readonly',
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    }),
    CredentialsProvider({
      name: 'Developer Login',
      credentials: {
        username: { label: "Username", type: "text", placeholder: "developer" }
      },
      async authorize(_credentials) {
        // Return a mock developer session profile
        return {
          id: 'dev-user-123',
          name: 'Developer User',
          email: 'developer@example.com',
          image: 'https://api.dicebear.com/7.x/bottts/svg?seed=developer'
        }
      }
    })
  ],
  callbacks: {
    async jwt({ token, user, account }) {
      // Initial sign-in: persist user ID, tokens and expiry.
      if (user) {
        token.sub = user.id || token.sub
        token.name = user.name
        token.email = user.email
        token.picture = user.image
      }
      if (account) {
        token.accessToken = account.access_token
        token.refreshToken = account.refresh_token
        token.expiresAt = account.expires_at
          ? account.expires_at * 1000
          : Date.now() + 30 * 24 * 60 * 60 * 1000 // 30 days
        token.error = undefined
        return token
      }

      // Still valid (60s safety margin) — reuse.
      if (token.expiresAt && Date.now() < (token.expiresAt as number) - 60_000) {
        return token
      }

      // Expired Google OAuth token — attempt refresh.
      if (token.refreshToken) {
        const refreshed = await refreshGoogleAccessToken(token)
        if (!refreshed.error) return refreshed
      }

      // Fallback for Developer/Credentials or persistent sessions: extend JWT validity for 30 days
      token.expiresAt = Date.now() + 30 * 24 * 60 * 60 * 1000
      token.error = undefined
      return token
    },
    async session({ session, token }) {
      return {
        ...session,
        user: {
          id: token.sub || 'user-id',
          name: token.name || session.user?.name || 'User',
          email: token.email || session.user?.email || 'user@example.com',
          image: token.picture || session.user?.image,
        },
        accessToken: token.accessToken,
        refreshToken: token.refreshToken,
        error: token.error,
      }
    },
  },
  pages: {
    signIn: '/login',
  },
  session: {
    strategy: 'jwt',
    maxAge: 30 * 24 * 60 * 60, // 30 days session persistence
  },
  secret: process.env.NEXTAUTH_SECRET || 'multi-agent-platform-jwt-secret-key-30days',
}
