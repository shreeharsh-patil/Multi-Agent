"use client"

/**
 * Simple JWT token store backed by localStorage.
 *
 * Provides functions to read / write / clear the backend-issued JWT
 * access token across page reloads.
 */

const STORAGE_KEY = "freebuff_access_token"

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null
  return localStorage.getItem(STORAGE_KEY)
}

export function setAccessToken(token: string): void {
  localStorage.setItem(STORAGE_KEY, token)
}

export function clearAccessToken(): void {
  localStorage.removeItem(STORAGE_KEY)
}

export function isAuthenticated(): boolean {
  return !!getAccessToken()
}
