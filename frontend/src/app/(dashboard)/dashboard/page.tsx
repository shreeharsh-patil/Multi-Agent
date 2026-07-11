'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Bot, MessageSquare, FileText, BookOpen, Activity, Sparkles, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import Link from 'next/link'

const statConfig = [
  { label: 'Active Agents', icon: Bot, color: 'text-blue-500', key: 'agents' as const },
  { label: 'Documents', icon: FileText, color: 'text-purple-500', key: 'documents' as const },
  { label: 'Notes', icon: BookOpen, color: 'text-amber-500', key: 'notes' as const },
  { label: 'Conversations', icon: MessageSquare, color: 'text-green-500', key: 'conversations' as const },
]

export default function DashboardPage() {
  const [stats, setStats] = useState({ agents: 0, documents: 0, notes: 0, conversations: 0 })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    const fetchStats = async () => {
      setLoading(true)
      try {
        const [agentsRes, docsRes, notesRes] = await Promise.all([
          api.agents.list(),
          api.documents.list(),
          api.notes.list(),
        ])
        if (mounted) {
          setStats({
            agents: (agentsRes.success && agentsRes.data ? agentsRes.data.length : 0),
            documents: (docsRes.success && docsRes.data ? docsRes.data.length : 0),
            notes: (notesRes.success && notesRes.data ? notesRes.data.length : 0),
            conversations: 0,
          })
        }
      } catch (e) {
        if (mounted) setError('Failed to load dashboard data')
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchStats()
    return () => { mounted = false }
  }, [])

  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Welcome to your Multi-Agent AI Platform
        </p>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-lg">
          {error}
          <span className="text-xs ml-2">(Some stats may be incomplete)</span>
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {statConfig.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-3xl font-bold mt-1">
                    {loading ? (
                      <Loader2 className="h-6 w-6 animate-spin inline-block" />
                    ) : (
                      stats[stat.key]
                    )}
                  </p>
                </div>
                <div className={`p-3 rounded-full bg-secondary ${stat.color}`}>
                  <stat.icon className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Sparkles className="h-5 w-5" />
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 gap-3">
              <Link href="/chat">
                <div className="p-4 rounded-lg border hover:bg-secondary/50 transition-colors cursor-pointer text-center">
                  <MessageSquare className="h-6 w-6 mx-auto mb-2 text-primary" />
                  <p className="text-sm font-medium">Start Chat</p>
                </div>
              </Link>
              <Link href="/documents">
                <div className="p-4 rounded-lg border hover:bg-secondary/50 transition-colors cursor-pointer text-center">
                  <FileText className="h-6 w-6 mx-auto mb-2 text-purple-500" />
                  <p className="text-sm font-medium">Upload Document</p>
                </div>
              </Link>
              <Link href="/notes">
                <div className="p-4 rounded-lg border hover:bg-secondary/50 transition-colors cursor-pointer text-center">
                  <BookOpen className="h-6 w-6 mx-auto mb-2 text-amber-500" />
                  <p className="text-sm font-medium">Create Notes</p>
                </div>
              </Link>
              <Link href="/drive">
                <div className="p-4 rounded-lg border hover:bg-secondary/50 transition-colors cursor-pointer text-center">
                  <Activity className="h-6 w-6 mx-auto mb-2 text-green-500" />
                  <p className="text-sm font-medium">Google Drive</p>
                </div>
              </Link>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <Bot className="h-5 w-5" />
              Active Agents
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="flex justify-center py-4">
                <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <p className="text-4xl font-bold text-primary">{stats.agents}</p>
            )}
            <p className="text-sm text-muted-foreground mt-1">
              Specialized agents ready to help
            </p>
            <Link href="/agents">
              <p className="text-sm text-primary hover:underline mt-3 inline-block">View all agents →</p>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
