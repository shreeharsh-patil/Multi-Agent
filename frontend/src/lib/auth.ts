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
          scope: 'openid email profile https://www.googleapis.com/auth/drive https://www.googleapis.com/auth/calendar https://mail.google.com/ https://www.googleapis.com/auth/tasks https://www.googleapis.com/auth/documents https://www.googleapis.com/auth/spreadsheets https://www.googleapis.com/auth/contacts.readonly https://www.googleapis.com/auth/youtube.readonly',
          access_type: 'offline',
          prompt: 'consent',
          include_granted_scopes: 'true',
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
    async jwt({ token, account }) {
      // Initial sign-in: persist tokens and expiry.
      if (account) {
        token.accessToken = account.access_token
        token.refreshToken = account.refresh_token
        token.expiresAt = account.expires_at
          ? account.expires_at * 1000
          : Date.now() + 3600 * 1000
        token.error = undefined
        return token
      }

      // Still valid (60s safety margin) — reuse.
      if (token.expiresAt && Date.now() < (token.expiresAt as number) - 60_000) {
        return token
      }

      // Expired — refresh if we have a refresh token.
      if (token.refreshToken) {
        return refreshGoogleAccessToken(token)
      }

      return { ...token, error: 'RefreshAccessTokenError' }
    },
    async session({ session, token }) {
      return {
        ...session,
        user: session.user ? { ...session.user, id: token.sub! } : undefined,
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
  },
  secret: process.env.NEXTAUTH_SECRET,
}
