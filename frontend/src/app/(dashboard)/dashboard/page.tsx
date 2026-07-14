'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Bot, MessageSquare, FileText, BookOpen, Activity, Sparkles, Loader2 } from 'lucide-react'
import { api } from '@/lib/api'
import Link from 'next/link'

const statConfig = [
  { label: 'Specialist Agents', icon: Bot, bg: 'bg-indigo-50/40 dark:bg-indigo-950/15', color: 'text-indigo-650 dark:text-indigo-400 border-indigo-200/20 dark:border-indigo-800/20', key: 'agents' as const },
  { label: 'Indexed Documents', icon: FileText, bg: 'bg-violet-50/40 dark:bg-violet-950/15', color: 'text-violet-650 dark:text-violet-400 border-violet-200/20 dark:border-violet-800/20', key: 'documents' as const },
  { label: 'Knowledge Notes', icon: BookOpen, bg: 'bg-amber-50/40 dark:bg-amber-950/15', color: 'text-amber-650 dark:text-amber-400 border-amber-200/20 dark:border-amber-800/20', key: 'notes' as const },
  { label: 'Conversations', icon: MessageSquare, bg: 'bg-emerald-50/40 dark:bg-emerald-950/15', color: 'text-emerald-650 dark:text-emerald-400 border-emerald-200/20 dark:border-emerald-800/20', key: 'conversations' as const },
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
        const [agentsRes, docsRes, notesRes, convsRes] = await Promise.all([
          api.agents.list(),
          api.documents.list(),
          api.notes.list(),
          api.chat.listConversations()
        ])
        if (mounted) {
          setStats({
            agents: (agentsRes.success && agentsRes.data ? agentsRes.data.length : 0),
            documents: (docsRes.success && docsRes.data ? docsRes.data.length : 0),
            notes: (notesRes.success && notesRes.data ? notesRes.data.length : 0),
            conversations: (convsRes.success && convsRes.data ? convsRes.data.length : 0),
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
    <div className="space-y-10 animate-fade-in max-w-7xl mx-auto py-2">
      <div>
        <h1 className="text-2xl md:text-3xl font-medium tracking-tight text-zinc-900 dark:text-zinc-50">Overview</h1>
        <p className="text-xs md:text-sm text-zinc-550 dark:text-zinc-400 mt-1">
          Welcome back. Here is the active status of your collaborative AI workspace.
        </p>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive text-xs px-4 py-3 rounded-lg border border-destructive/20">
          {error}
          <span className="text-[10px] ml-2 font-mono opacity-80">(Some stats may be incomplete)</span>
        </div>
      )}

      {/* Stats Grid */}
      <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
        {statConfig.map((stat) => (
          <Card key={stat.label} className="border-zinc-200/50 dark:border-zinc-900 bg-card/40 backdrop-blur-md hover:-translate-y-0.5 transition-all duration-200 hover:border-zinc-350 dark:hover:border-zinc-800 shadow-xs">
            <CardContent className="p-5 flex items-center justify-between">
              <div className="space-y-1">
                <p className="text-[11px] font-medium tracking-wider uppercase text-zinc-450 dark:text-zinc-500">{stat.label}</p>
                <p className="text-2xl md:text-3xl font-medium tracking-tight text-zinc-900 dark:text-zinc-50">
                  {loading ? (
                    <Loader2 className="h-5 w-5 animate-spin text-zinc-400 inline-block" />
                  ) : (
                    stats[stat.key]
                  )}
                </p>
              </div>
              <div className={`p-2.5 rounded-lg border ${stat.bg} ${stat.color}`}>
                <stat.icon className="h-4.5 w-4.5 stroke-[1.5]" />
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Main Grid split */}
      <div className="grid gap-6 md:grid-cols-3">
        {/* Quick Actions Card */}
        <Card className="md:col-span-2 border-zinc-200/50 dark:border-zinc-900 bg-card/40 backdrop-blur-md shadow-xs">
          <CardHeader className="px-6 pt-6 pb-2">
            <CardTitle className="flex items-center gap-2 text-sm font-medium tracking-wider uppercase text-zinc-450 dark:text-zinc-500">
              <Sparkles className="h-4 w-4 text-zinc-500" />
              Quick Workspace Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6">
            <div className="grid grid-cols-2 gap-4">
              <Link href="/chat">
                <div className="p-5 rounded-xl border border-zinc-200/40 dark:border-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-800 hover:bg-zinc-100/30 dark:hover:bg-zinc-900/30 transition-all duration-200 cursor-pointer text-center group">
                  <div className="h-10 w-10 mx-auto mb-3 rounded-lg bg-indigo-50/50 dark:bg-indigo-950/15 flex items-center justify-center border border-indigo-100/20 dark:border-indigo-900/20 text-indigo-650 dark:text-indigo-400">
                    <MessageSquare className="h-5 w-5 stroke-[1.5] transition-transform duration-200 group-hover:scale-105" />
                  </div>
                  <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">Start Chat</p>
                  <p className="text-[11px] text-zinc-400 dark:text-zinc-500 mt-1">Converse with specialized agents</p>
                </div>
              </Link>
              <Link href="/documents">
                <div className="p-5 rounded-xl border border-zinc-200/40 dark:border-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-800 hover:bg-zinc-100/30 dark:hover:bg-zinc-900/30 transition-all duration-200 cursor-pointer text-center group">
                  <div className="h-10 w-10 mx-auto mb-3 rounded-lg bg-violet-50/50 dark:bg-violet-950/15 flex items-center justify-center border border-violet-100/20 dark:border-violet-900/20 text-violet-650 dark:text-violet-400">
                    <FileText className="h-5 w-5 stroke-[1.5] transition-transform duration-200 group-hover:scale-105" />
                  </div>
                  <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">Upload Files</p>
                  <p className="text-[11px] text-zinc-400 dark:text-zinc-500 mt-1">Index document archives for RAG</p>
                </div>
              </Link>
              <Link href="/notes">
                <div className="p-5 rounded-xl border border-zinc-200/40 dark:border-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-800 hover:bg-zinc-100/30 dark:hover:bg-zinc-900/30 transition-all duration-200 cursor-pointer text-center group">
                  <div className="h-10 w-10 mx-auto mb-3 rounded-lg bg-amber-50/50 dark:bg-amber-950/15 flex items-center justify-center border border-amber-100/20 dark:border-amber-900/20 text-amber-650 dark:text-amber-400">
                    <BookOpen className="h-5 w-5 stroke-[1.5] transition-transform duration-200 group-hover:scale-105" />
                  </div>
                  <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">Create Notes</p>
                  <p className="text-[11px] text-zinc-400 dark:text-zinc-500 mt-1">Take rich notes and flashcards</p>
                </div>
              </Link>
              <Link href="/drive">
                <div className="p-5 rounded-xl border border-zinc-200/40 dark:border-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-800 hover:bg-zinc-100/30 dark:hover:bg-zinc-900/30 transition-all duration-200 cursor-pointer text-center group">
                  <div className="h-10 w-10 mx-auto mb-3 rounded-lg bg-emerald-50/50 dark:bg-emerald-950/15 flex items-center justify-center border border-emerald-100/20 dark:border-emerald-900/20 text-emerald-650 dark:text-emerald-400">
                    <Activity className="h-5 w-5 stroke-[1.5] transition-transform duration-200 group-hover:scale-105" />
                  </div>
                  <p className="text-sm font-medium text-zinc-800 dark:text-zinc-200">Google Drive</p>
                  <p className="text-[11px] text-zinc-400 dark:text-zinc-500 mt-1">Connect cloud files & calendar</p>
                </div>
              </Link>
            </div>
          </CardContent>
        </Card>

        {/* Active Agents Card */}
        <Card className="border-zinc-200/50 dark:border-zinc-900 bg-card/40 backdrop-blur-md shadow-xs flex flex-col justify-between">
          <div>
            <CardHeader className="px-6 pt-6 pb-2">
              <CardTitle className="flex items-center gap-2 text-sm font-medium tracking-wider uppercase text-zinc-450 dark:text-zinc-500">
                <Bot className="h-4 w-4 text-zinc-500" />
                Orchestration Hub
              </CardTitle>
            </CardHeader>
            <CardContent className="px-6 pt-2 pb-6">
              <div className="space-y-4 mt-2">
                <div>
                  {loading ? (
                    <div className="h-10 w-10 flex items-center justify-center">
                      <Loader2 className="h-5 w-5 animate-spin text-zinc-400" />
                    </div>
                  ) : (
                    <p className="text-5xl font-light tracking-tight text-zinc-900 dark:text-zinc-50">{stats.agents}</p>
                  )}
                  <p className="text-[11px] text-zinc-550 dark:text-zinc-400 mt-1">
                    Specialized collaborative agent roles configured and active.
                  </p>
                </div>
                <div className="text-xs text-zinc-400 dark:text-zinc-500 leading-relaxed font-normal bg-zinc-50/50 dark:bg-zinc-900/40 border border-zinc-200/40 dark:border-zinc-900 p-3 rounded-lg">
                  Agents can dynamically collaborate on complex research, code analysis, document retrieval, and planning.
                </div>
              </div>
            </CardContent>
          </div>
          <div className="p-6 pt-0">
            <Link href="/agents" className="w-full inline-flex h-9 items-center justify-center rounded-lg border border-zinc-200 hover:border-zinc-300 dark:border-zinc-900 dark:hover:border-zinc-800 bg-transparent text-xs font-medium text-zinc-800 dark:text-zinc-200 hover:bg-zinc-50/50 dark:hover:bg-zinc-900/50 transition-colors">
              Manage Agents →
            </Link>
          </div>
        </Card>
      </div>
    </div>
  )
}
