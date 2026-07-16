'use client'

import { useState, useEffect } from 'react'
import { useSession, signIn, signOut } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { api } from '@/lib/api'
import { clearAccessToken } from '@/lib/auth-store'
import { User, Bell, HardDrive, CalendarDays, BookOpen, LogOut, Loader2, CheckCircle2, XCircle, ExternalLink } from 'lucide-react'

export default function SettingsPage() {
  const { data: session } = useSession()
  const accessToken = (session as any)?.accessToken

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [settingsError, setSettingsError] = useState<string | null>(null)
  const [settingsSuccess, setSettingsSuccess] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [preferences, setPreferences] = useState({
    theme: 'light',
    defaultModel: 'gemini-2.0-flash',
    notifications: true,
    language: 'en',
    useOpendocumentsRag: false,
  })

  useEffect(() => {
    const loadPreferences = async () => {
      try {
        const res = await api.auth.getMe()
        if (res.success && res.data) {
          setName(res.data.name || '')
          setPreferences({
            theme: res.data.preferences?.theme ?? 'light',
            defaultModel: res.data.preferences?.defaultModel ?? 'gemini-2.0-flash',
            notifications: res.data.preferences?.notifications ?? true,
            language: res.data.preferences?.language ?? 'en',
            useOpendocumentsRag: res.data.preferences?.useOpendocumentsRag ?? false,
          })
        }
      } catch (e) {
        console.error('Failed to load preferences', e)
      } finally {
        setLoading(false)
      }
    }
    loadPreferences()
  }, [])

  const handleTogglePreference = async (key: string, value: any) => {
    const prevPrefs = preferences
    const updatedPrefs = { ...prevPrefs, [key]: value }
    setPreferences(updatedPrefs)
    setSettingsError(null)
    try {
      const res = await api.auth.updateMe({ preferences: updatedPrefs })
      if (!res.success) {
        setSettingsError(res.error || 'Failed to save preference')
        setPreferences(prevPrefs)
      }
    } catch (e) {
      setSettingsError('Failed to save preference')
      setPreferences(prevPrefs)
    }
  }

  const handleProfileSave = async () => {
    setSaving(true)
    setSettingsError(null)
    setSettingsSuccess(null)
    try {
      const res = await api.auth.updateMe({ name })
      if (res.success) {
        setSettingsSuccess('Profile updated')
      } else {
        setSettingsError(res.error || 'Failed to update profile')
      }
    } catch (e) {
      setSettingsError('Failed to update profile')
    } finally {
      setSaving(false)
    }
  }

  const handleLogout = async () => {
    clearAccessToken()
    await signOut({ callbackUrl: '/login' })
  }

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-8 animate-fade-in pb-12">
      <div>
        <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-[#26251e]">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">Manage your account and platform preferences</p>
      </div>

      {settingsError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-[8px] flex items-center justify-between">
          <span>{settingsError}</span>
          <Button variant="link" size="sm" className="text-red-700 underline p-0 h-auto" onClick={() => setSettingsError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {settingsSuccess && (
        <div className="bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3 rounded-[8px] flex items-center justify-between">
          <span>{settingsSuccess}</span>
          <Button variant="link" size="sm" className="text-green-700 underline p-0 h-auto" onClick={() => setSettingsSuccess(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {/* Profile */}
      <Card>
        <CardHeader className="p-6 pb-0">
          <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base">
            <User className="h-5 w-5 text-primary" />
            Profile
          </CardTitle>
          <CardDescription>Manage your account information</CardDescription>
        </CardHeader>
        <CardContent className="space-y-5 p-6">
          <div className="grid gap-2">
            <Label htmlFor="name">Name</Label>
            <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="email">Email</Label>
            <Input id="email" type="email" value={session?.user?.email || ''} disabled className="opacity-70" />
          </div>
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <CheckCircle2 className="h-4 w-4 text-[#1f8a65]" />
            Signed in with Google
          </div>
          <Button onClick={handleProfileSave} disabled={saving}>
            {saving && <Loader2 className="h-4 w-4 animate-spin mr-2" />}
            Save Changes
          </Button>
        </CardContent>
      </Card>

      {/* Integrations */}
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-sans font-normal tracking-[-0.02em] text-foreground">Integrations</h2>
          <p className="text-sm text-muted-foreground">Connect your accounts and services</p>
        </div>
        <div className="grid gap-6 md:grid-cols-2">
          {/* Google Drive */}
          <Card>
            <CardHeader className="p-5 pb-0">
              <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-sm">
                <HardDrive className="h-4 w-4 text-primary" />
                Google Drive
              </CardTitle>
              <CardDescription className="text-xs">Connect and manage your Google Drive</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 p-5">
              <div className="flex items-center gap-3 p-3 rounded-[8px] border bg-secondary/50">
                <HardDrive className="h-8 w-8 text-primary shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-foreground">Google Drive</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {accessToken
                      ? 'Connected — access your Drive files'
                      : 'Sign in to access and manage Drive files'}
                  </p>
                </div>
                <Badge variant={accessToken ? 'default' : 'secondary'} className="px-2 py-0.5 text-[9px] uppercase tracking-wider rounded-full shrink-0">
                  {accessToken ? (
                    <span className="flex items-center gap-1">
                      <CheckCircle2 className="h-3 w-3" />
                      Connected
                    </span>
                  ) : (
                    <span className="flex items-center gap-1">
                      <XCircle className="h-3 w-3" />
                      Disconnected
                    </span>
                  )}
                </Badge>
              </div>
              {!accessToken ? (
                <Button className="w-full gap-2" onClick={() => signIn('google', { callbackUrl: '/drive' })}>
                  <HardDrive className="h-4 w-4" />
                  Connect Google Drive
                </Button>
              ) : (
                <div className="space-y-3">
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    Drive access is available through your Google authentication.
                  </p>
                  <Button variant="outline" className="w-full gap-2" onClick={() => window.location.href = '/drive'}>
                    <ExternalLink className="h-4 w-4 text-primary" />
                    Open Drive
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Google Calendar */}
          <Card>
            <CardHeader className="p-5 pb-0">
              <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-sm">
                <CalendarDays className="h-4 w-4 text-primary" />
                Google Calendar
              </CardTitle>
              <CardDescription className="text-xs">Let the Calendar Agent manage your schedule</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4 p-5">
              <div className="flex items-center gap-3 p-3 rounded-[8px] border bg-secondary/50">
                <CalendarDays className="h-8 w-8 text-primary shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm text-foreground">Calendar access</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {accessToken ? 'Available to the Calendar Agent' : 'Reconnect Google to grant calendar access'}
                  </p>
                </div>
                <Badge variant={accessToken ? 'default' : 'secondary'} className="px-2 py-0.5 text-[9px] uppercase tracking-wider rounded-full shrink-0">
                  {accessToken ? 'Connected' : 'Not connected'}
                </Badge>
              </div>
              <Button variant="outline" className="w-full gap-2" onClick={() => signIn('google', { callbackUrl: '/chat' })}>
                <CalendarDays className="h-4 w-4 text-primary" />
                {accessToken ? 'Reconnect Google Calendar' : 'Connect Google Calendar'}
              </Button>
              <p className="text-[10px] text-muted-foreground leading-relaxed">
                After connecting, ask the Calendar Agent in Chat to list events, create meetings, check availability, or reschedule.
              </p>
            </CardContent>
          </Card>
        </div>
      </section>

      {/* Knowledge */}
      <section className="space-y-4">
        <div>
          <h2 className="text-lg font-sans font-normal tracking-[-0.02em] text-foreground">Knowledge</h2>
          <p className="text-sm text-muted-foreground">Configure your knowledge sources</p>
        </div>
        <Card>
          <CardHeader className="p-6 pb-0">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base">
              <BookOpen className="h-5 w-5 text-primary" />
              OpenDocuments RAG
            </CardTitle>
            <CardDescription>Use OpenDocuments as your self-hosted RAG backend</CardDescription>
          </CardHeader>
          <CardContent className="space-y-5 p-6">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Enable OpenDocuments</Label>
                <p className="text-sm text-muted-foreground">
                  Route document searches and knowledge base queries to OpenDocuments
                </p>
              </div>
              <Switch
                checked={preferences.useOpendocumentsRag}
                onCheckedChange={(checked) => handleTogglePreference('useOpendocumentsRag', checked)}
              />
            </div>
            <div className="border-t border-border pt-5">
              <div className="grid gap-2">
                <Label htmlFor="opendocuments-url">API URL</Label>
                <Input id="opendocuments-url" value="http://localhost:5001" disabled className="opacity-70" />
                <p className="text-xs text-muted-foreground">Configured globally in backend settings.</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </section>

      {/* Notifications */}
      <Card>
        <CardHeader className="p-6 pb-0">
          <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base">
            <Bell className="h-5 w-5 text-primary" />
            Notifications
          </CardTitle>
          <CardDescription>Configure your notification preferences</CardDescription>
        </CardHeader>
        <CardContent className="p-6">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label>Push Notifications</Label>
              <p className="text-sm text-muted-foreground">Receive push notifications</p>
            </div>
            <Switch
              checked={preferences.notifications}
              onCheckedChange={(checked) => handleTogglePreference('notifications', checked)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Sign Out */}
      <Card className="border-destructive/20">
        <CardHeader className="p-6 pb-0">
          <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base">
            <LogOut className="h-5 w-5 text-destructive" />
            Sign Out
          </CardTitle>
          <CardDescription>End your current session</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4 p-6">
          <p className="text-sm text-muted-foreground leading-relaxed">
            Signed in as <span className="font-semibold text-foreground">{session?.user?.email || 'Unknown'}</span>.
            Signing out will redirect you to the login page.
          </p>
          <Button
            variant="outline"
            className="gap-2 border-destructive/30 text-destructive hover:bg-destructive/5 hover:text-destructive"
            onClick={handleLogout}
          >
            <LogOut className="h-4 w-4" />
            Sign Out
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
