'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button, buttonVariants } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Bot,
  BookOpen,
  Brain,
  Search,
  FileCode,
  StickyNote,
  GraduationCap,
  Calendar,
  Puzzle,
  Loader2,
  Plus,
  Trash2,
} from 'lucide-react'
import { api } from '@/lib/api'
import Link from 'next/link'

const iconMap: Record<string, import('lucide-react').LucideIcon> = {
  BookOpen: BookOpen,
  Brain: Brain,
  StickyNote: StickyNote,
  GraduationCap: GraduationCap,
  Calendar: Calendar,
  Search: Search,
  FileCode: FileCode,
  Puzzle: Puzzle,
}

const colorMap: Record<string, string> = {
  knowledge: 'text-[#cc785c]',
  drive: 'text-[#cc785c]',
  notes: 'text-[#cc785c]',
  quiz: 'text-[#cc785c]',
  planner: 'text-[#cc785c]',
  research: 'text-[#cc785c]',
  coding: 'text-[#cc785c]',
  memory: 'text-[#cc785c]',
  tool: 'text-[#cc785c]',
}

const tagMap: Record<string, string[]> = {
  knowledge: ['RAG', 'Search', 'Citations'],
  drive: ['Drive', 'Files', 'Sync'],
  notes: ['Notes', 'Flashcards'],
  quiz: ['Quiz', 'MCQ', 'Exam'],
  planner: ['Planning', 'Schedule'],
  research: ['Search', 'Reports'],
  coding: ['Code', 'Debug'],
  memory: ['Memory', 'History'],
  tool: ['Tools', 'APIs'],
}

const availableTools = [
  { id: 'web_search', label: 'Web search' },
  { id: 'calculator', label: 'Calculator' },
  { id: 'google_drive', label: 'Google Drive' },
  { id: 'notes', label: 'Note creator' },
]

export default function AgentsPage() {
  const [agents, setAgents] = useState<Array<{ id: string; name: string; description: string; icon: string; capabilities?: string[]; tools?: string[]; systemInstruction?: string; custom?: boolean }>>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [builderOpen, setBuilderOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [draft, setDraft] = useState({ name: '', description: '', icon: 'Bot', system_instruction: '', tools: [] as string[] })

  useEffect(() => {
    let mounted = true
    const fetchAgents = async () => {
      setLoading(true)
      try {
        const res = await api.agents.list()
        if (mounted && res.success && res.data) {
          setAgents(res.data)
        } else if (mounted) {
          setError(res.error || 'Failed to load agents')
        }
      } catch (e) {
        if (mounted) setError('Failed to connect to backend')
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchAgents()
    return () => { mounted = false }
  }, [])

  const refreshAgents = async () => {
    const res = await api.agents.list()
    if (res.success && res.data) setAgents(res.data)
  }

  const createAgent = async () => {
    if (!draft.name.trim() || !draft.system_instruction.trim()) return
    setSaving(true)
    const res = await api.agents.create(draft)
    if (res.success) {
      setDraft({ name: '', description: '', icon: 'Bot', system_instruction: '', tools: [] })
      setBuilderOpen(false)
      await refreshAgents()
    } else setError(res.error || 'Could not create agent')
    setSaving(false)
  }

  const deleteAgent = async (id: string) => {
    if (!confirm('Delete this custom agent?')) return
    const res = await api.agents.delete(id)
    if (res.success) await refreshAgents()
    else setError(res.error || 'Could not delete agent')
  }

  const renderAgentList = () => {
    return agents.map((agent) => {
      const Icon = iconMap[agent.icon] || Bot
      const color = colorMap[agent.id] || 'text-[#6c6a64]'
      const tags = agent.custom ? (agent.tools || []).map((tool) => availableTools.find((item) => item.id === tool)?.label || tool) : tagMap[agent.id] || []
      return (
        <Card key={agent.id} className="group border-[#e6dfd8] bg-[#efe9de] hover:bg-[#e8e0d2]/75 hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between shadow-xs">
          <CardHeader className="p-5">
            <div className="flex items-start justify-between">
              <div className={`p-2.5 rounded-[8px] bg-[#faf9f5] border border-[#e6dfd8] shadow-xs ${color}`}>
                <Icon className="h-5 w-5 stroke-[1.5]" />
              </div>
              <Link 
                href={`/chat?agent=${agent.id}`} 
                className={`${buttonVariants({ variant: 'outline', size: 'sm' })} text-xs h-7 px-2.5 rounded-[8px] opacity-0 group-hover:opacity-100 transition-opacity`}
              >
                Chat
              </Link>
            </div>
            <CardTitle className="mt-4 text-base font-semibold text-[#141413]">{agent.name}</CardTitle>
            <CardDescription className="text-xs text-[#6c6a64] leading-normal mt-1 min-h-[32px] line-clamp-2">{agent.description}</CardDescription>
          </CardHeader>
          <CardContent className="p-5 pt-0">
            <div className="flex flex-wrap gap-1.5 mb-4">
              {tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="bg-[#faf9f5] text-[#6c6a64] font-normal text-[10px] px-2.5 py-0.5 border border-[#e6dfd8]">{tag}</Badge>
              ))}
            </div>
            {agent.custom && (
              <Button 
                variant="ghost" 
                size="sm" 
                onClick={() => deleteAgent(agent.id)} 
                className="gap-1.5 text-xs text-[#c64545] hover:bg-[#c64545]/10 h-8 px-2 rounded-[8px]"
              >
                <Trash2 className="h-3.5 w-3.5" /> 
                Delete
              </Button>
            )}
          </CardContent>
        </Card>
      )
    })
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in bg-[#faf9f5]">
        <div>
          <h1 className="text-3xl font-serif font-normal text-[#141413]">Agents</h1>
          <p className="text-sm text-[#6c6a64] mt-1">
            Manage your specialized AI agents
          </p>
        </div>
        <Card className="border-[#e6dfd8] bg-[#efe9de]">
          <CardContent className="py-16 text-center text-[#6c6a64]">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-[#cc785c]" />
            <p>Loading agents...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in bg-[#faf9f5]">
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-serif font-normal text-[#141413]">Agent Hub</h1>
            <p className="text-sm text-[#6c6a64] mt-1">{agents.length} agents available · build your own specialist</p>
          </div>
          <Button onClick={() => setBuilderOpen((open) => !open)} className="gap-2 shadow-sm">
            <Plus className="h-4 w-4" /> Create agent
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-[8px]">
          {error}
          <Button variant="link" size="sm" className="ml-2 text-red-700 underline" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {builderOpen && (
        <Card className="border-[#cc785c]/25 bg-[#efe9de]/75 shadow-xs">
          <CardHeader>
            <CardTitle className="font-serif font-normal text-lg">Build a custom agent</CardTitle>
            <CardDescription className="text-[#6c6a64]">Give it a clear job, personality, and only the tools it needs.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <Input placeholder="Agent name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
              <Input placeholder="Short description" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
              <Textarea placeholder="System instructions — what should this agent do?" value={draft.system_instruction} onChange={(e) => setDraft({ ...draft, system_instruction: e.target.value })} className="min-h-32" />
            </div>
            <div className="rounded-[12px] border border-[#e6dfd8] bg-[#faf9f5] p-4 flex flex-col justify-between">
              <div>
                <p className="mb-3 text-sm font-semibold text-[#141413]">Tool permissions</p>
                <div className="space-y-3">
                  {availableTools.map((tool) => (
                    <label key={tool.id} className="flex cursor-pointer items-center gap-3 text-sm text-[#6c6a64] hover:text-[#141413] transition-colors">
                      <input 
                        type="checkbox" 
                        checked={draft.tools.includes(tool.id)} 
                        onChange={(e) => setDraft({ ...draft, tools: e.target.checked ? [...draft.tools, tool.id] : draft.tools.filter((id) => id !== tool.id) })} 
                        className="h-4 w-4 rounded border-[#e6dfd8] text-[#cc785c] focus:ring-[#cc785c]" 
                      />
                      {tool.label}
                    </label>
                  ))}
                </div>
              </div>
              <Button onClick={createAgent} disabled={saving || !draft.name.trim() || !draft.system_instruction.trim()} className="mt-6 w-full shadow-sm">
                {saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}Create agent
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {renderAgentList()}
      </div>
    </div>
  )
}
