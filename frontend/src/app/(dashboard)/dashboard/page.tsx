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
    <div className="space-y-12 max-w-7xl mx-auto py-6 px-4 animate-fade-in bg-[#212121]">
      {/* Header section with generous spacing */}
      <div className="space-y-2">
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded-[24px] border border-[#2F2F2F] bg-[#2F2F2F] text-xs text-[#B4B4B4]">
          <Sparkles className="h-3.5 w-3.5 text-white" />
          <span>Intelligent Workspace</span>
        </div>
        <h1 className="text-3xl font-semibold tracking-[-0.02em] text-[#F9F9F9]">
          Overview
        </h1>
        <p className="text-sm text-[#B4B4B4] max-w-lg leading-relaxed">
          Welcome back. Here is the operational status of your collaborative agent workspace.
        </p>
      </div>

      {error && (
        <div className="p-4 rounded-[16px] border border-red-500/20 bg-red-950/15 text-xs text-red-400">
          {error}
          <span className="text-[10px] ml-2 font-mono opacity-80">(Some stats may be incomplete)</span>
        </div>
      )}

      {/* Stats Grid using premium border-heavy cards */}
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {statConfig.map((stat) => (
          <div 
            key={stat.label} 
            className="group p-6 rounded-[16px] border border-[#2F2F2F] bg-[#2F2F2F] hover:bg-[#3F3F3F]/40 transition-all duration-300 hover:-translate-y-0.5 flex flex-col justify-between h-36"
          >
            <div className="flex items-center justify-between">
              <span className="text-[11px] font-semibold text-[#B4B4B4] uppercase tracking-wider">
                {stat.label}
              </span>
              <stat.icon className="h-4.5 w-4.5 text-[#B4B4B4] stroke-[1.25] group-hover:text-white transition-colors" />
            </div>
            <div>
              <p className="text-3xl font-semibold tracking-tight text-[#F9F9F9]">
                {loading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-[#B4B4B4]" />
                ) : (
                  stats[stat.key]
                )}
              </p>
              <p className="text-xs text-[#B4B4B4]/70 mt-1">{stat.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Main Grid Splits */}
      <div className="grid gap-8 md:grid-cols-3">
        {/* Quick Actions Card */}
        <div className="md:col-span-2 p-8 rounded-[16px] border border-[#2F2F2F] bg-[#2F2F2F] flex flex-col justify-between">
          <div className="space-y-6">
            <div className="flex items-center justify-between">
              <h3 className="text-[11px] font-semibold text-[#B4B4B4] uppercase tracking-wider flex items-center gap-2">
                <Compass className="h-4 w-4 stroke-[1.25]" />
                Quick Workspace Actions
              </h3>
            </div>
            
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Link href="/chat">
                <div className="group p-5 rounded-[16px] border border-[#2F2F2F] bg-[#171717] hover:bg-[#2F2F2F] hover:border-[#3F3F3F] transition-all duration-200 cursor-pointer flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[24px] border border-[#2F2F2F] bg-[#2F2F2F] flex items-center justify-center text-white">
                      <MessageSquare className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-[14px] font-semibold text-[#F9F9F9]">Start Chat</p>
                      <p className="text-[11px] text-[#B4B4B4] mt-0.5">Converse with specialized agents</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-[#B4B4B4] group-hover:text-white transition-colors" />
                </div>
              </Link>

              <Link href="/documents">
                <div className="group p-5 rounded-[16px] border border-[#2F2F2F] bg-[#171717] hover:bg-[#2F2F2F] hover:border-[#3F3F3F] transition-all duration-200 cursor-pointer flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[24px] border border-[#2F2F2F] bg-[#2F2F2F] flex items-center justify-center text-white">
                      <FolderUp className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-[14px] font-semibold text-[#F9F9F9]">Upload Files</p>
                      <p className="text-[11px] text-[#B4B4B4] mt-0.5">Index document archives for RAG</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-[#B4B4B4] group-hover:text-white transition-colors" />
                </div>
              </Link>

              <Link href="/notes">
                <div className="group p-5 rounded-[16px] border border-[#2F2F2F] bg-[#171717] hover:bg-[#2F2F2F] hover:border-[#3F3F3F] transition-all duration-200 cursor-pointer flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[24px] border border-[#2F2F2F] bg-[#2F2F2F] flex items-center justify-center text-white">
                      <NotebookPen className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-[14px] font-semibold text-[#F9F9F9]">Create Notes</p>
                      <p className="text-[11px] text-[#B4B4B4] mt-0.5">Take rich notes and flashcards</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-[#B4B4B4] group-hover:text-white transition-colors" />
                </div>
              </Link>

              <Link href="/drive">
                <div className="group p-5 rounded-[16px] border border-[#2F2F2F] bg-[#171717] hover:bg-[#2F2F2F] hover:border-[#3F3F3F] transition-all duration-200 cursor-pointer flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="h-10 w-10 rounded-[24px] border border-[#2F2F2F] bg-[#2F2F2F] flex items-center justify-center text-white">
                      <Link2 className="h-4.5 w-4.5 stroke-[1.25]" />
                    </div>
                    <div>
                      <p className="text-[14px] font-semibold text-[#F9F9F9]">Google Drive</p>
                      <p className="text-[11px] text-[#B4B4B4] mt-0.5">Connect cloud files & calendar</p>
                    </div>
                  </div>
                  <ArrowUpRight className="h-4 w-4 text-[#B4B4B4] group-hover:text-white transition-colors" />
                </div>
              </Link>
            </div>
          </div>
        </div>

        {/* Orchestration Hub Card */}
        <div className="p-8 rounded-[16px] border border-[#2F2F2F] bg-[#2F2F2F] flex flex-col justify-between h-full min-h-[300px]">
          <div className="space-y-6">
            <h3 className="text-[11px] font-semibold text-[#B4B4B4] uppercase tracking-wider flex items-center gap-2">
              <Bot className="h-4 w-4 stroke-[1.25]" />
              Orchestration Hub
            </h3>
            
            <div className="space-y-2">
              <p className="text-5xl font-light tracking-tight text-[#F9F9F9]">
                {loading ? (
                  <Loader2 className="h-6 w-6 animate-spin text-[#B4B4B4]" />
                ) : (
                  stats.agents
                )}
              </p>
              <p className="text-xs text-[#B4B4B4] leading-relaxed">
                Active specialized collaborative agent roles currently operating.
              </p>
            </div>
            
            <p className="text-[11px] text-[#B4B4B4] leading-normal p-3.5 rounded-[12px] border border-[#2F2F2F] bg-[#171717]">
              Agents can dynamically collaborate on complex research, code analysis, document retrieval, and planning tasks.
            </p>
          </div>
          
          <Link 
            href="/agents" 
            className="w-full h-11 inline-flex items-center justify-center rounded-[24px] border border-[#2F2F2F] bg-[#171717] hover:bg-[#2F2F2F] text-xs font-semibold text-white transition-colors mt-6"
          >
            Manage Agents
          </Link>
        </div>
      </div>
    </div>
  )
}
