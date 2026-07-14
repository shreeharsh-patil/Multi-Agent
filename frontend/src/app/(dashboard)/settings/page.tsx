'use client'

import { useState, useEffect } from 'react'
import { useSession, signIn } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Badge } from '@/components/ui/badge'
import { Switch } from '@/components/ui/switch'
import { Separator } from '@/components/ui/separator'
import { api } from '@/lib/api'
import { User, Bell, Palette, Key, Globe, Database, HardDrive, CalendarDays, CheckCircle2, XCircle, ExternalLink, BookOpen, Loader2 } from 'lucide-react'

export default function SettingsPage() {
  const { data: session } = useSession()
  const accessToken = (session as any)?.accessToken

  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [name, setName] = useState('')
  const [preferences, setPreferences] = useState({
    theme: 'system',
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
            theme: res.data.preferences?.theme ?? 'system',
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
    const updatedPrefs = { ...preferences, [key]: value }
    setPreferences(updatedPrefs)
    try {
      await api.auth.updateMe({
        preferences: updatedPrefs,
      })
    } catch (e) {
      console.error('Failed to save preference', e)
    }
  }

  const handleProfileSave = async () => {
    setSaving(true)
    try {
      await api.auth.updateMe({
        name,
      })
    } catch (e) {
      console.error('Failed to update profile', e)
    } finally {
      setSaving(false)
    }
  }

  if (loading) {
    return (
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground mt-1">
          Manage your account and platform preferences
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <User className="h-5 w-5" />
              Profile
            </CardTitle>
            <CardDescription>Manage your account information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label htmlFor="name">Name</Label>
              <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email">Email</Label>
              <Input id="email" type="email" defaultValue={session?.user?.email || 'user@example.com'} disabled />
            </div>
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <CheckCircle2 className="h-4 w-4 text-emerald-500" />
              Signed in with Google
            </div>
            <Button onClick={handleProfileSave} disabled={saving}>
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Save Changes
            </Button>
          </CardContent>
        </Card>

        {/* Google Drive Integration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <HardDrive className="h-5 w-5" />
              Google Drive
            </CardTitle>
            <CardDescription>Connect and manage your Google Drive</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3 p-3 rounded-lg bg-secondary/50">
              <HardDrive className="h-8 w-8 text-green-500" />
              <div className="flex-1">
                <p className="font-medium">Google Drive</p>
                <p className="text-sm text-muted-foreground">
                  {accessToken
                    ? 'Connected — you can access your Drive files'
                    : 'Sign in to access, upload, and manage Drive files'}
                </p>
              </div>
              <Badge variant={accessToken ? 'default' : 'secondary'}>
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
                className="w-full gap-2"
                onClick={() => signIn('google', { callbackUrl: '/drive' })}
              >
                <HardDrive className="h-4 w-4" />
                Connect Google Drive
              </Button>
            ) : (
              <div className="space-y-3">
                <p className="text-sm text-muted-foreground">
                  You have Drive access through your Google authentication.
                  Visit the Drive page to manage your files.
                </p>
                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1 gap-2" onClick={() => window.location.href = '/drive'}>
                    <ExternalLink className="h-4 w-4" />
                    Open Drive
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <CalendarDays className="h-5 w-5" />
              Google Calendar
            </CardTitle>
            <CardDescription>Let the Calendar Agent manage your schedule</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3 rounded-lg bg-secondary/50 p-3">
              <CalendarDays className="h-8 w-8 text-blue-500" />
              <div className="flex-1"><p className="font-medium">Calendar access</p><p className="text-sm text-muted-foreground">{accessToken ? 'Available to the Calendar Agent' : 'Reconnect Google to grant calendar access'}</p></div>
              <Badge variant={accessToken ? 'default' : 'secondary'}>{accessToken ? 'Connected' : 'Not connected'}</Badge>
            </div>
            <Button variant="outline" className="w-full gap-2" onClick={() => signIn('google', { callbackUrl: '/chat' })}>
              <CalendarDays className="h-4 w-4" />
              {accessToken ? 'Reconnect Google Calendar' : 'Connect Google Calendar'}
            </Button>
            <p className="text-xs text-muted-foreground">After connecting, ask the Calendar Agent in Chat to list events, create meetings, check availability, or reschedule.</p>
          </CardContent>
        </Card>

        {/* OpenDocuments Integration */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <BookOpen className="h-5 w-5" />
              OpenDocuments RAG
            </CardTitle>
            <CardDescription>Use OpenDocuments as your self-hosted RAG backend</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
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
            <Separator />
            <div className="grid gap-2">
              <Label htmlFor="opendocuments-url">API URL</Label>
              <Input
                id="opendocuments-url"
                value="http://localhost:5001"
                disabled
                className="bg-secondary/50"
              />
              <p className="text-xs text-muted-foreground">
                Configured globally in backend settings.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Palette className="h-5 w-5" />
              Appearance
            </CardTitle>
            <CardDescription>Customize your interface</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Dark Mode</Label>
                <p className="text-sm text-muted-foreground">Toggle dark mode theme</p>
              </div>
              <Switch checked={preferences.theme === 'dark'} onCheckedChange={(checked) => handleTogglePreference('theme', checked ? 'dark' : 'light')} />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Compact Mode</Label>
                <p className="text-sm text-muted-foreground">Reduce spacing in the interface</p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Bell className="h-5 w-5" />
              Notifications
            </CardTitle>
            <CardDescription>Configure notification preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Push Notifications</Label>
                <p className="text-sm text-muted-foreground">Receive push notifications</p>
              </div>
              <Switch checked={preferences.notifications} onCheckedChange={(checked) => handleTogglePreference('notifications', checked)} />
            </div>
            <Separator />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label>Email Notifications</Label>
                <p className="text-sm text-muted-foreground">Receive email updates</p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Globe className="h-5 w-5" />
              Language & Region
            </CardTitle>
            <CardDescription>Set your preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-2">
              <Label>Language</Label>
              <Input value={preferences.language} onChange={(e) => setPreferences({ ...preferences, language: e.target.value })} />
            </div>
            <div className="grid gap-2">
              <Label>Timezone</Label>
              <Input defaultValue="America/New_York" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Key className="h-5 w-5" />
              API Keys
            </CardTitle>
            <CardDescription>Manage your API integrations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              No API keys configured. Connect to external services in the integrations settings.
            </p>
            <Button variant="outline">Configure API Keys</Button>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Database className="h-5 w-5" />
              Data Management
            </CardTitle>
            <CardDescription>Manage your data and storage</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Manage your stored data, export options, and connected services.
            </p>
            <div className="flex gap-3">
              <Button variant="outline">Export Data</Button>
              <Button variant="outline" className="text-destructive">Clear Cache</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
