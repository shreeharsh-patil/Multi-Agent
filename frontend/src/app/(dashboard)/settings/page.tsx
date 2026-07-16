'use client'

import { useState, useEffect } from 'react'
import { useSession, signIn, signOut } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { api } from '@/lib/api'
import { clearAccessToken } from '@/lib/auth-store'
import { User, Bell, Palette, Key, Globe, Database, HardDrive, CalendarDays, CheckCircle2, XCircle, ExternalLink, BookOpen, Loader2, LogOut } from 'lucide-react'

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
      const res = await api.auth.updateMe({
        preferences: updatedPrefs,
      })
      if (!res.success) {
        setSettingsError(res.error || 'Failed to save preference')
        // Revert on failure
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
      const res = await api.auth.updateMe({
        name,
      })
      if (res.success) {
        setSettingsSuccess('Profile updated successfully')
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
      <div className="flex h-[50vh] items-center justify-center bg-background">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in bg-background">
      <div>
        <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-[#26251e]">Settings</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your account and platform preferences
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base text-foreground">
              <User className="h-4.5 w-4.5 text-primary" />
              Profile
            </CardTitle>
            <CardDescription className="text-muted-foreground">Manage your account information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="grid gap-2">
              <Label htmlFor="name" className="text-xs text-foreground">Name</Label>
              <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email" className="text-xs text-foreground">Email</Label>
              <Input id="email" type="email" defaultValue={session?.user?.email || 'user@example.com'} disabled className="opacity-80" />
            </div>
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <CheckCircle2 className="h-4 w-4 text-[#1f8a65]" />
              Signed in with Google
            </div>
            <Button onClick={handleProfileSave} disabled={saving} className="shadow-sm">
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Save Changes
            </Button>
          </CardContent>
        </Card>

      {settingsError && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-[8px] col-span-full">
          {settingsError}
          <Button variant="link" size="sm" className="ml-2 text-red-700 underline" onClick={() => setSettingsError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {settingsSuccess && (
        <div className="bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3 rounded-[8px] col-span-full">
          {settingsSuccess}
          <Button variant="link" size="sm" className="ml-2 text-green-700 underline" onClick={() => setSettingsSuccess(null)}>
            Dismiss
          </Button>
        </div>
      )}

        {/* Google Drive Integration */}
        <Card className="shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base text-foreground">
              <HardDrive className="h-4.5 w-4.5 text-primary" />
              Google Drive
            </CardTitle>
            <CardDescription className="text-muted-foreground">Connect and manage your Google Drive</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="flex items-center gap-3 p-3 rounded-[8px] border border-border bg-secondary">
              <HardDrive className="h-8 w-8 text-primary" />
              <div className="flex-1">
                <p className="font-semibold text-sm text-foreground">Google Drive</p>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {accessToken
                    ? 'Connected — you can access your Drive files'
                    : 'Sign in to access, upload, and manage Drive files'}
                </p>
              </div>
              <Badge variant={accessToken ? 'default' : 'secondary'} className="px-2 py-0.5 text-[9px] uppercase tracking-wider rounded-full">
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
              <Button
                variant="default"
                className="w-full gap-2 shadow-sm"
                onClick={() => signIn('google', { callbackUrl: '/drive' })}
              >
                <HardDrive className="h-4 w-4" />
                Connect Google Drive
              </Button>
            ) : (
              <div className="space-y-3">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  You have Drive access through your Google authentication.
                  Visit the Drive page to manage your files.
                </p>
                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1 gap-2 shadow-sm h-10 text-xs" onClick={() => window.location.href = '/drive'}>
                    <ExternalLink className="h-4 w-4 text-primary" />
                    Open Drive
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base text-foreground">
              <CalendarDays className="h-4.5 w-4.5 text-primary" />
              Google Calendar
            </CardTitle>
            <CardDescription className="text-muted-foreground">Let the Calendar Agent manage your schedule</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="flex items-center gap-3 p-3 rounded-[8px] border border-border bg-secondary">
              <CalendarDays className="h-8 w-8 text-primary" />
              <div className="flex-1">
                <p className="font-semibold text-sm text-foreground">Calendar access</p>
                <p className="text-xs text-muted-foreground mt-0.5">{accessToken ? 'Available to the Calendar Agent' : 'Reconnect Google to grant calendar access'}</p>
              </div>
              <Badge variant={accessToken ? 'default' : 'secondary'} className="px-2 py-0.5 text-[9px] uppercase tracking-wider rounded-full">{accessToken ? 'Connected' : 'Not connected'}</Badge>
            </div>
            <Button variant="outline" className="w-full gap-2 shadow-sm h-10 text-xs" onClick={() => signIn('google', { callbackUrl: '/chat' })}>
              <CalendarDays className="h-4 w-4 text-primary" />
              {accessToken ? 'Reconnect Google Calendar' : 'Connect Google Calendar'}
            </Button>
            <p className="text-[10px] text-muted-foreground leading-relaxed">After connecting, ask the Calendar Agent in Chat to list events, create meetings, check availability, or reschedule.</p>
          </CardContent>
        </Card>

        {/* OpenDocuments Integration */}
        <Card className="shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base text-foreground">
              <BookOpen className="h-4.5 w-4.5 text-primary" />
              OpenDocuments RAG
            </CardTitle>
            <CardDescription className="text-muted-foreground">Use OpenDocuments as your self-hosted RAG backend</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="flex items-center justify-between text-sm">
              <div className="space-y-0.5">
                <Label className="text-foreground text-xs">Enable OpenDocuments</Label>
                <p className="text-xs text-muted-foreground">
                  Route document searches and knowledge base queries to OpenDocuments
                </p>
              </div>
              <Switch
                checked={preferences.useOpendocumentsRag}
                onCheckedChange={(checked) => handleTogglePreference('useOpendocumentsRag', checked)}
              />
            </div>
            <Separator className="bg-border" />
            <div className="grid gap-2">
              <Label htmlFor="opendocuments-url" className="text-xs text-foreground">API URL</Label>
              <Input
                id="opendocuments-url"
                value="http://localhost:5001"
                disabled
                className="opacity-75"
              />
              <p className="text-[10px] text-muted-foreground">
                Configured globally in backend settings.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base text-foreground">
              <Palette className="h-4.5 w-4.5 text-primary" />
              Appearance
            </CardTitle>
            <CardDescription className="text-muted-foreground">Customize your interface</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-xs text-foreground">Warm Cream Theme</Label>
                <p className="text-xs text-muted-foreground">Forced editorial warm-canvas floor</p>
              </div>
              <Switch checked={true} disabled />
            </div>
            <Separator className="bg-border" />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-xs text-foreground">Compact Mode</Label>
                <p className="text-xs text-muted-foreground">Reduce spacing in the interface</p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base text-foreground">
              <Bell className="h-4.5 w-4.5 text-primary" />
              Notifications
            </CardTitle>
            <CardDescription className="text-muted-foreground">Configure notification preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-xs text-foreground">Push Notifications</Label>
                <p className="text-xs text-muted-foreground">Receive push notifications</p>
              </div>
              <Switch checked={preferences.notifications} onCheckedChange={(checked) => handleTogglePreference('notifications', checked)} />
            </div>
            <Separator className="bg-border" />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-xs text-foreground">Email Notifications</Label>
                <p className="text-xs text-muted-foreground">Receive email updates</p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base text-foreground">
              <Globe className="h-4.5 w-4.5 text-primary" />
              Language & Region
            </CardTitle>
            <CardDescription className="text-muted-foreground">Set your preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="grid gap-2">
              <Label className="text-xs text-foreground">Language</Label>
              <Input value={preferences.language} onChange={(e) => setPreferences({ ...preferences, language: e.target.value })} />
            </div>
            <div className="grid gap-2">
              <Label className="text-xs text-foreground">Timezone</Label>
              <Input defaultValue="America/New_York" />
            </div>
          </CardContent>
        </Card>

        <Card className="shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base text-foreground">
              <Key className="h-4.5 w-4.5 text-primary" />
              API Keys
            </CardTitle>
            <CardDescription className="text-muted-foreground">Manage your API integrations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <p className="text-xs text-muted-foreground leading-relaxed">
              No API keys configured. Connect to external services in the integrations settings.
            </p>
            <Button variant="outline" className="shadow-sm">Configure API Keys</Button>
          </CardContent>
        </Card>

        <Card className="shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base text-foreground">
              <Database className="h-4.5 w-4.5 text-primary" />
              Data Management
            </CardTitle>
            <CardDescription className="text-muted-foreground">Manage your data and storage</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <p className="text-xs text-muted-foreground leading-relaxed">
              Manage your stored data, export options, and connected services.
            </p>
            <div className="flex gap-3">
              <Button variant="outline" className="shadow-sm">Export Data</Button>
              <Button variant="outline" className="text-[#c64545] hover:bg-[#c64545]/10 border-border shadow-sm">Clear Cache</Button>
            </div>
          </CardContent>
        </Card>

        {/* Sign Out */}
        <Card className="shadow-xs border-red-200/60 col-span-full">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-base text-foreground">
              <LogOut className="h-4.5 w-4.5 text-red-500" />
              Sign Out
            </CardTitle>
            <CardDescription className="text-muted-foreground">End your current session</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <p className="text-xs text-muted-foreground leading-relaxed">
              You are signed in as{' '}
              <span className="font-semibold text-foreground">{session?.user?.email || 'user@example.com'}</span>.
              Signing out will redirect you to the login page.
            </p>
            <div className="flex gap-3">
              <Button
                variant="outline"
                className="gap-2 border-red-200 text-red-600 hover:bg-red-50 hover:text-red-700 hover:border-red-300 transition-all shadow-sm"
                onClick={handleLogout}
              >
                <LogOut className="h-4 w-4" />
                Sign Out
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
