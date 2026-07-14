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
  knowledge: 'text-blue-500',
  drive: 'text-green-500',
  notes: 'text-purple-500',
  quiz: 'text-amber-500',
  planner: 'text-pink-500',
  research: 'text-indigo-500',
  coding: 'text-cyan-500',
  memory: 'text-rose-500',
  tool: 'text-orange-500',
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
      const color = colorMap[agent.id] || 'text-muted-foreground'
      const tags = agent.custom ? (agent.tools || []).map((tool) => availableTools.find((item) => item.id === tool)?.label || tool) : tagMap[agent.id] || []
      return (
        <Card key={agent.id} className="group hover:shadow-md transition-shadow">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className={`p-3 rounded-lg bg-secondary ${color}`}>
                <Icon className="h-6 w-6" />
              </div>
              <Link href="/chat" className={`${buttonVariants({ variant: 'ghost', size: 'sm' })} gap-2 opacity-0 group-hover:opacity-100 transition-opacity`}>
                Chat
              </Link>
            </div>
            <CardTitle className="mt-4">{agent.name}</CardTitle>
            <CardDescription>{agent.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2 mb-4">
              {tags.map((tag) => (
                <Badge key={tag} variant="secondary">{tag}</Badge>
              ))}
            </div>
            {agent.custom && <Button variant="ghost" size="sm" onClick={() => deleteAgent(agent.id)} className="gap-2 text-destructive"><Trash2 className="h-3.5 w-3.5" /> Delete</Button>}
          </CardContent>
        </Card>
      )
    })
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground mt-1">
            Manage your specialized AI agents
          </p>
        </div>
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3" />
            <p>Loading agents...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <div className="flex items-start justify-between gap-4">
          <div><h1 className="text-3xl font-bold tracking-tight">Agent Hub</h1><p className="text-muted-foreground mt-1">{agents.length} agents available · build your own specialist</p></div>
          <Button onClick={() => setBuilderOpen((open) => !open)} className="gap-2"><Plus className="h-4 w-4" /> Create agent</Button>
        </div>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-lg">
          {error}
          <Button variant="link" size="sm" className="ml-2" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {builderOpen && (
        <Card className="border-primary/20 bg-gradient-to-br from-primary/[.06] via-background to-violet-500/[.05]">
          <CardHeader><CardTitle>Build a custom agent</CardTitle><CardDescription>Give it a clear job, personality, and only the tools it needs.</CardDescription></CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <Input placeholder="Agent name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
              <Input placeholder="Short description" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
              <Textarea placeholder="System instructions — what should this agent do?" value={draft.system_instruction} onChange={(e) => setDraft({ ...draft, system_instruction: e.target.value })} className="min-h-32" />
            </div>
            <div className="rounded-lg border bg-background/60 p-4">
              <p className="mb-3 text-sm font-semibold">Tool permissions</p>
              <div className="space-y-3">
                {availableTools.map((tool) => <label key={tool.id} className="flex cursor-pointer items-center gap-3 text-sm"><input type="checkbox" checked={draft.tools.includes(tool.id)} onChange={(e) => setDraft({ ...draft, tools: e.target.checked ? [...draft.tools, tool.id] : draft.tools.filter((id) => id !== tool.id) })} className="h-4 w-4 rounded border" />{tool.label}</label>)}
              </div>
              <Button onClick={createAgent} disabled={saving || !draft.name.trim() || !draft.system_instruction.trim()} className="mt-6 w-full">{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Plus className="mr-2 h-4 w-4" />}Create agent</Button>
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
