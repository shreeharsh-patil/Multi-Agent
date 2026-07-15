'use client'

import { useState, useEffect } from 'react'
import { Bot, MessageSquare, FileText, BookOpen, Sparkles, Loader2, Compass, ArrowUpRight, FolderUp, NotebookPen, Link2 } from 'lucide-react'
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
    <div className="space-y-12 max-w-7xl mx-auto py-6 px-4 animate-fade-in bg-[#faf9f5]">
      {/* Header section with generous spacing */}
      <div className="space-y-3">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full border border-[#cc785c]/20 bg-[#cc785c]/5 text-[11px] font-medium text-[#cc785c] uppercase tracking-[1.5px] select-none">
          <Sparkles className="h-3 w-3 text-[#cc785c]" />
          <span>Intelligent Workspace</span>
        </div>
        <h1 className="text-4xl font-serif font-normal tracking-tight text-[#141413]">
          Overview
        </h1>
        <p className="text-sm text-[#6c6a64] max-w-lg leading-relaxed font-sans">
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
            className="group p-6 rounded-[12px] border border-[#e6dfd8] bg-[#efe9de] hover:bg-[#e8e0d2]/75 transition-all duration-300 flex flex-col justify-between h-36 shadow-xs"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold text-[#6c6a64] uppercase tracking-wider">
                {stat.label}
              </span>
              <stat.icon className="h-4.5 w-4.5 text-[#6c6a64] stroke-[1.25] group-hover:text-[#cc785c] transition-colors" />
            </div>
            <div>
              <p className="text-4.5xl font-serif font-normal tracking-tight text-[#141413]">
                {loading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-[#6c6a64]" />
                ) : (
                  stats[stat.key]
                )}
              </p>
              <p className="text-xs text-[#6c6a64]/85 mt-1">{stat.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid Splits */}
      <div className="grid gap-8 md:grid-cols-3">
        {/* Quick Actions Card */}
        <div className="md:col-span-2 p-8 rounded-[12px] border border-[#e6dfd8] bg-[#efe9de] flex flex-col justify-between shadow-xs">
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-[10px] font-semibold text-[#6c6a64] uppercase tracking-wider flex items-center gap-2">
                <Compass className="h-4 w-4 stroke-[1.25]" />
                Quick Workspace Actions
              </h3>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Link href="/chat">
                <div className="group p-5 rounded-[12px] border border-[#e6dfd8] bg-[#faf9f5] hover:bg-[#f5f0e8] hover:border-[#cc785c]/35 transition-all duration-200 cursor-pointer flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[8px] border border-[#e6dfd8] bg-[#efe9de] flex items-center justify-center text-[#cc785c]">
                      <MessageSquare className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#141413]">Start Chat</p>
                      <p className="text-[11px] text-[#6c6a64] mt-0.5">Converse with specialized agents</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-[#6c6a64] group-hover:text-[#cc785c] transition-colors" />
                </div>
              </Link>

              <Link href="/documents">
                <div className="group p-5 rounded-[12px] border border-[#e6dfd8] bg-[#faf9f5] hover:bg-[#f5f0e8] hover:border-[#cc785c]/35 transition-all duration-200 cursor-pointer flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[8px] border border-[#e6dfd8] bg-[#efe9de] flex items-center justify-center text-[#cc785c]">
                      <FolderUp className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#141413]">Upload Files</p>
                      <p className="text-[11px] text-[#6c6a64] mt-0.5">Index document archives for RAG</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-[#6c6a64] group-hover:text-[#cc785c] transition-colors" />
                </div>
              </Link>

              <Link href="/notes">
                <div className="group p-5 rounded-[12px] border border-[#e6dfd8] bg-[#faf9f5] hover:bg-[#f5f0e8] hover:border-[#cc785c]/35 transition-all duration-200 cursor-pointer flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[8px] border border-[#e6dfd8] bg-[#efe9de] flex items-center justify-center text-[#cc785c]">
                      <NotebookPen className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#141413]">Create Notes</p>
                      <p className="text-[11px] text-[#6c6a64] mt-0.5">Take rich notes and flashcards</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-[#6c6a64] group-hover:text-[#cc785c] transition-colors" />
                </div>
              </Link>

              <Link href="/drive">
                <div className="group p-5 rounded-[12px] border border-[#e6dfd8] bg-[#faf9f5] hover:bg-[#f5f0e8] hover:border-[#cc785c]/35 transition-all duration-200 cursor-pointer flex items-center justify-between shadow-xs">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[8px] border border-[#e6dfd8] bg-[#efe9de] flex items-center justify-center text-[#cc785c]">
                      <Link2 className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-sm font-medium text-[#141413]">Google Drive</p>
                      <p className="text-[11px] text-[#6c6a64] mt-0.5">Connect cloud files & calendar</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-[#6c6a64] group-hover:text-[#cc785c] transition-colors" />
                </div>
              </Link>
            </div>
          </div>
        </div>

        {/* Orchestration Hub Card */}
        <div className="p-8 rounded-[12px] border border-[#e6dfd8] bg-[#efe9de] flex flex-col justify-between h-full min-h-[300px] shadow-xs">
          <div className="space-y-6">
            <h3 className="text-[10px] font-semibold text-[#6c6a64] uppercase tracking-wider flex items-center gap-2">
              <Bot className="h-4 w-4 stroke-[1.25]" />
              Orchestration Hub
            </h3>
            
            <div className="space-y-2">
              <p className="text-5xl font-serif font-normal tracking-tight text-[#141413]">
                {loading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-[#6c6a64]" />
                ) : (
                  stats.agents
                )}
              </p>
              <p className="text-xs text-[#6c6a64] leading-relaxed">
                Active specialized collaborative agent roles currently operating.
              </p>
            </div>
            
            <p className="text-xs text-[#141413] leading-relaxed p-4 rounded-[8px] border border-[#e6dfd8] bg-[#faf9f5]">
              Agents can dynamically collaborate on complex research, code analysis, document retrieval, and planning tasks.
            </p>
          </div>
          
          <Link 
            href="/agents" 
            className="w-full h-10 inline-flex items-center justify-center rounded-[8px] border border-[#cc785c] bg-[#cc785c] text-white hover:bg-[#a9583e] text-xs font-semibold transition-colors mt-6 shadow-sm"
          >
            Manage Agents
          </Link>
        </div>
      </div>
    </div>
  )
}
