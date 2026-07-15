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
      <div className="flex h-[50vh] items-center justify-center bg-[#faf9f5]">
        <Loader2 className="h-8 w-8 animate-spin text-[#cc785c]" />
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in bg-[#faf9f5]">
      <div>
        <h1 className="text-3xl font-serif font-normal text-[#141413]">Settings</h1>
        <p className="text-sm text-[#6c6a64] mt-1">
          Manage your account and platform preferences
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-serif font-normal text-base text-[#141413]">
              <User className="h-4.5 w-4.5 text-[#cc785c]" />
              Profile
            </CardTitle>
            <CardDescription className="text-[#6c6a64]">Manage your account information</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="grid gap-2">
              <Label htmlFor="name" className="text-xs text-[#141413]">Name</Label>
              <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
            </div>
            <div className="grid gap-2">
              <Label htmlFor="email" className="text-xs text-[#141413]">Email</Label>
              <Input id="email" type="email" defaultValue={session?.user?.email || 'user@example.com'} disabled className="opacity-80" />
            </div>
            <div className="flex items-center gap-2 text-xs text-[#6c6a64]">
              <CheckCircle2 className="h-4 w-4 text-[#5db872]" />
              Signed in with Google
            </div>
            <Button onClick={handleProfileSave} disabled={saving} className="shadow-sm">
              {saving ? <Loader2 className="h-4 w-4 animate-spin mr-2" /> : null}
              Save Changes
            </Button>
          </CardContent>
        </Card>

        {/* Google Drive Integration */}
        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-serif font-normal text-base text-[#141413]">
              <HardDrive className="h-4.5 w-4.5 text-[#cc785c]" />
              Google Drive
            </CardTitle>
            <CardDescription className="text-[#6c6a64]">Connect and manage your Google Drive</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="flex items-center gap-3 p-3 rounded-[8px] border border-[#e6dfd8] bg-[#faf9f5]">
              <HardDrive className="h-8 w-8 text-[#cc785c]" />
              <div className="flex-1">
                <p className="font-semibold text-sm text-[#141413]">Google Drive</p>
                <p className="text-xs text-[#6c6a64] mt-0.5">
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
                <p className="text-xs text-[#6c6a64] leading-relaxed">
                  You have Drive access through your Google authentication.
                  Visit the Drive page to manage your files.
                </p>
                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1 gap-2 shadow-sm h-10 text-xs" onClick={() => window.location.href = '/drive'}>
                    <ExternalLink className="h-4 w-4 text-[#cc785c]" />
                    Open Drive
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-serif font-normal text-base text-[#141413]">
              <CalendarDays className="h-4.5 w-4.5 text-[#cc785c]" />
              Google Calendar
            </CardTitle>
            <CardDescription className="text-[#6c6a64]">Let the Calendar Agent manage your schedule</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="flex items-center gap-3 p-3 rounded-[8px] border border-[#e6dfd8] bg-[#faf9f5]">
              <CalendarDays className="h-8 w-8 text-[#cc785c]" />
              <div className="flex-1">
                <p className="font-semibold text-sm text-[#141413]">Calendar access</p>
                <p className="text-xs text-[#6c6a64] mt-0.5">{accessToken ? 'Available to the Calendar Agent' : 'Reconnect Google to grant calendar access'}</p>
              </div>
              <Badge variant={accessToken ? 'default' : 'secondary'} className="px-2 py-0.5 text-[9px] uppercase tracking-wider rounded-full">{accessToken ? 'Connected' : 'Not connected'}</Badge>
            </div>
            <Button variant="outline" className="w-full gap-2 shadow-sm h-10 text-xs" onClick={() => signIn('google', { callbackUrl: '/chat' })}>
              <CalendarDays className="h-4 w-4 text-[#cc785c]" />
              {accessToken ? 'Reconnect Google Calendar' : 'Connect Google Calendar'}
            </Button>
            <p className="text-[10px] text-[#6c6a64] leading-relaxed">After connecting, ask the Calendar Agent in Chat to list events, create meetings, check availability, or reschedule.</p>
          </CardContent>
        </Card>

        {/* OpenDocuments Integration */}
        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-serif font-normal text-base text-[#141413]">
              <BookOpen className="h-4.5 w-4.5 text-[#cc785c]" />
              OpenDocuments RAG
            </CardTitle>
            <CardDescription className="text-[#6c6a64]">Use OpenDocuments as your self-hosted RAG backend</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="flex items-center justify-between text-sm">
              <div className="space-y-0.5">
                <Label className="text-[#141413] text-xs">Enable OpenDocuments</Label>
                <p className="text-xs text-[#6c6a64]">
                  Route document searches and knowledge base queries to OpenDocuments
                </p>
              </div>
              <Switch
                checked={preferences.useOpendocumentsRag}
                onCheckedChange={(checked) => handleTogglePreference('useOpendocumentsRag', checked)}
              />
            </div>
            <Separator className="bg-[#e6dfd8]" />
            <div className="grid gap-2">
              <Label htmlFor="opendocuments-url" className="text-xs text-[#141413]">API URL</Label>
              <Input
                id="opendocuments-url"
                value="http://localhost:5001"
                disabled
                className="opacity-75"
              />
              <p className="text-[10px] text-[#6c6a64]">
                Configured globally in backend settings.
              </p>
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-serif font-normal text-base text-[#141413]">
              <Palette className="h-4.5 w-4.5 text-[#cc785c]" />
              Appearance
            </CardTitle>
            <CardDescription className="text-[#6c6a64]">Customize your interface</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-xs text-[#141413]">Warm Cream Theme</Label>
                <p className="text-xs text-[#6c6a64]">Forced editorial warm-canvas floor</p>
              </div>
              <Switch checked={true} disabled />
            </div>
            <Separator className="bg-[#e6dfd8]" />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-xs text-[#141413]">Compact Mode</Label>
                <p className="text-xs text-[#6c6a64]">Reduce spacing in the interface</p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-serif font-normal text-base text-[#141413]">
              <Bell className="h-4.5 w-4.5 text-[#cc785c]" />
              Notifications
            </CardTitle>
            <CardDescription className="text-[#6c6a64]">Configure notification preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-xs text-[#141413]">Push Notifications</Label>
                <p className="text-xs text-[#6c6a64]">Receive push notifications</p>
              </div>
              <Switch checked={preferences.notifications} onCheckedChange={(checked) => handleTogglePreference('notifications', checked)} />
            </div>
            <Separator className="bg-[#e6dfd8]" />
            <div className="flex items-center justify-between">
              <div className="space-y-0.5">
                <Label className="text-xs text-[#141413]">Email Notifications</Label>
                <p className="text-xs text-[#6c6a64]">Receive email updates</p>
              </div>
              <Switch />
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-serif font-normal text-base text-[#141413]">
              <Globe className="h-4.5 w-4.5 text-[#cc785c]" />
              Language & Region
            </CardTitle>
            <CardDescription className="text-[#6c6a64]">Set your preferences</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <div className="grid gap-2">
              <Label className="text-xs text-[#141413]">Language</Label>
              <Input value={preferences.language} onChange={(e) => setPreferences({ ...preferences, language: e.target.value })} />
            </div>
            <div className="grid gap-2">
              <Label className="text-xs text-[#141413]">Timezone</Label>
              <Input defaultValue="America/New_York" />
            </div>
          </CardContent>
        </Card>

        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-serif font-normal text-base text-[#141413]">
              <Key className="h-4.5 w-4.5 text-[#cc785c]" />
              API Keys
            </CardTitle>
            <CardDescription className="text-[#6c6a64]">Manage your API integrations</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <p className="text-xs text-[#6c6a64] leading-relaxed">
              No API keys configured. Connect to external services in the integrations settings.
            </p>
            <Button variant="outline" className="shadow-sm">Configure API Keys</Button>
          </CardContent>
        </Card>

        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader className="p-5">
            <CardTitle className="flex items-center gap-2 font-serif font-normal text-base text-[#141413]">
              <Database className="h-4.5 w-4.5 text-[#cc785c]" />
              Data Management
            </CardTitle>
            <CardDescription className="text-[#6c6a64]">Manage your data and storage</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 p-5 pt-0">
            <p className="text-xs text-[#6c6a64] leading-relaxed">
              Manage your stored data, export options, and connected services.
            </p>
            <div className="flex gap-3">
              <Button variant="outline" className="shadow-sm">Export Data</Button>
              <Button variant="outline" className="text-[#c64545] hover:bg-[#c64545]/10 border-[#e6dfd8] shadow-sm">Clear Cache</Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
