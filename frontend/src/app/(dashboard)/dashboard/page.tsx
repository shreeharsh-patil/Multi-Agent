'use client'

import { useState, useEffect } from 'react'
import { Bot, MessageSquare, FileText, BookOpen, Sparkles, Loader2, Compass, ArrowUpRight, FolderUp, NotebookPen, Link2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'
import Link from 'next/link'

const statConfig = [
  { label: 'Specialist Agents', icon: Bot, desc: 'Active multi-agent configs', key: 'agents' as const },
  { label: 'Indexed Documents', icon: FileText, desc: 'Processed vector files', key: 'documents' as const },
  { label: 'Knowledge Notes', icon: BookOpen, desc: 'Saved cards & resources', key: 'notes' as const },
  { label: 'Conversations', icon: MessageSquare, desc: 'Total active sessions', key: 'conversations' as const },
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
    <div className="space-y-12 max-w-7xl mx-auto py-6 px-4 animate-fade-in bg-[#f7f7f4]">
      {/* Header section with generous spacing */}
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-primary/20 bg-primary/5 text-[11px] font-semibold text-primary uppercase tracking-[1.5px] select-none">
          <Sparkles className="h-3 w-3 text-primary" />
          <span>Intelligent Workspace</span>
        </div>
        <h1 className="text-4xl font-sans font-normal tracking-[-0.03em] text-[#26251e]">
          Overview
        </h1>
        <p className="text-sm text-[#5a5852] max-w-lg leading-relaxed font-sans">
          Welcome back. Here is the operational status of your collaborative agent workspace.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-[8px] border border-red-200 bg-red-50 text-xs text-red-700">
          {error}
          <span className="text-[10px] ml-2 font-mono opacity-80">(Some stats may be incomplete)</span>
        </div>
      )}

      {/* Stats Grid using premium border-heavy cards */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statConfig.map((stat) => (
          <div 
            key={stat.label} 
            className="group p-6 rounded-[12px] border border-border bg-card hover:bg-secondary/40 transition-all duration-300 flex flex-col justify-between h-36 shadow-xs"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                {stat.label}
              </span>
              <stat.icon className="h-4.5 w-4.5 text-muted-foreground stroke-[1.25] group-hover:text-primary transition-colors" />
            </div>
            <div>
              <p className="text-4.5xl font-sans font-normal tracking-tight text-[#26251e]">
                {loading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                ) : (
                  stats[stat.key]
                )}
              </p>
              <p className="text-xs text-muted-foreground/80 mt-1">{stat.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid Splits */}
      <div className="grid gap-8 md:grid-cols-3">
        {/* Quick Actions Card */}
        <div className="md:col-span-2 p-8 rounded-[12px] border border-border bg-card flex flex-col justify-between shadow-xs">
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <Compass className="h-4 w-4 stroke-[1.25]" />
                Quick Workspace Actions
              </h3>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Link href="/chat">
                <div className="group p-5 rounded-[12px] border border-border bg-secondary hover:bg-secondary/65 hover:border-primary/30 transition-all duration-200 cursor-pointer flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[8px] border border-border bg-card flex items-center justify-center text-primary">
                      <MessageSquare className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-[#26251e]">Start Chat</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">Converse with specialized agents</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
              </Link>

              <Link href="/documents">
                <div className="group p-5 rounded-[12px] border border-border bg-secondary hover:bg-secondary/65 hover:border-primary/30 transition-all duration-200 cursor-pointer flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[8px] border border-border bg-card flex items-center justify-center text-primary">
                      <FolderUp className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-[#26251e]">Upload Files</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">Index document archives for RAG</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
              </Link>

              <Link href="/notes">
                <div className="group p-5 rounded-[12px] border border-border bg-secondary hover:bg-secondary/65 hover:border-primary/30 transition-all duration-200 cursor-pointer flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[8px] border border-border bg-card flex items-center justify-center text-primary">
                      <NotebookPen className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-[#26251e]">Create Notes</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">Take rich notes and flashcards</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
              </Link>

              <Link href="/drive">
                <div className="group p-5 rounded-[12px] border border-border bg-secondary hover:bg-secondary/65 hover:border-primary/30 transition-all duration-200 cursor-pointer flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[8px] border border-border bg-card flex items-center justify-center text-primary">
                      <Link2 className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-sm font-semibold text-[#26251e]">Google Drive</p>
                      <p className="text-[11px] text-muted-foreground mt-0.5">Connect cloud files & calendar</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
                </div>
              </Link>
            </div>
          </div>
        </div>

        {/* Orchestration Hub Card */}
        <div className="p-8 rounded-[12px] border border-border bg-card flex flex-col justify-between h-full min-h-[300px] shadow-xs">
          <div className="space-y-6">
            <h3 className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Bot className="h-4 w-4 stroke-[1.25]" />
              Orchestration Hub
            </h3>
            
            <div className="space-y-2">
              <p className="text-5xl font-sans font-normal tracking-tight text-[#26251e]">
                {loading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                ) : (
                  stats.agents
                )}
              </p>
              <p className="text-xs text-[#5a5852] leading-relaxed">
                Active specialized collaborative agent roles currently operating.
              </p>
            </div>
            
            <p className="text-xs text-foreground leading-relaxed p-4 rounded-[8px] border border-border bg-secondary">
              Agents can dynamically collaborate on complex research, code analysis, document retrieval, and planning tasks.
            </p>
          </div>
          
          <Link href="/agents" className="w-full mt-6">
            <Button className="w-full shadow-sm">
              Manage Agents
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
