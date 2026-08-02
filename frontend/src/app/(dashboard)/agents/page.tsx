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
  Image as ImageIcon,
  Loader2,
  Plus,
  Trash2,
  Workflow,
  Send,
  X,
} from 'lucide-react'
import { api } from '@/lib/api'
import { getAccessToken } from '@/lib/auth-store'
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
  Image: ImageIcon,
}

const colorMap: Record<string, string> = {
  image: 'text-[#1f8a65]',
  knowledge: 'text-primary',
  drive: 'text-primary',
  notes: 'text-primary',
  quiz: 'text-primary',
  planner: 'text-primary',
  research: 'text-primary',
  coding: 'text-primary',
  memory: 'text-primary',
  tool: 'text-primary',
}

const tagMap: Record<string, string[]> = {
  image: ['Text to image', 'Visual assets'],
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
  const [testFor, setTestFor] = useState<{ id: string; name: string } | null>(null)
  const [testMessage, setTestMessage] = useState('')
  const [testOutput, setTestOutput] = useState('')
  const [testRunning, setTestRunning] = useState(false)
  const [testTools, setTestTools] = useState<string[]>([])

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
    if (res.success && res.data) {
      setAgents(res.data)
    } else {
      setError(res.error || 'Failed to refresh agents')
    }
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

  const startTest = (id: string, name: string, tools: string[] = []) => {
    setTestFor({ id, name })
    setTestMessage('')
    setTestOutput('')
    setTestRunning(false)
    setTestTools(tools)
  }

  const runTest = async () => {
    if (!testFor || !testMessage.trim() || testRunning) return
    setTestRunning(true)
    setTestOutput('')
    setTestTools([])

    const API_BASE = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
    try {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      const token = getAccessToken()
      if (token) headers['Authorization'] = `Bearer ${token}`

      const response = await fetch(`${API_BASE}/api/agents/${testFor.id}/run`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ message: testMessage }),
      })
      if (!response.body) throw new Error('No response body')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = ''
      let streamed = ''

      while (true) {
        const { value, done } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() || ''
        for (const block of blocks) {
          let event = 'message'
          const dataLines: string[] = []
          for (const line of block.split('\n')) {
            if (line.startsWith('event:')) event = line.slice(6).trim()
            if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
          }
          if (!dataLines.length) continue
          try {
            const data = JSON.parse(dataLines.join('\n'))
            if (event === 'agent_run_token') {
              streamed += data.token || ''
              setTestOutput(streamed)
            } else if (event === 'agent_run_complete') {
              setTestOutput(data.output || streamed)
              setTestTools(data.tools || [])
            }
          } catch (err) {
            console.error('SSE parse error', err, block)
          }
        }
      }
    } catch (err) {
      console.error('Agent test error', err)
      setTestOutput('Network error. Ensure the backend is running on port 8000.')
    } finally {
      setTestRunning(false)
    }
  }

  const renderAgentList = () => {
    return agents.map((agent) => {
      const Icon = iconMap[agent.icon] || Bot
      const color = colorMap[agent.id] || 'text-[#6c6a64]'
      const tags = agent.custom ? (agent.tools || []).map((tool) => availableTools.find((item) => item.id === tool)?.label || tool) : tagMap[agent.id] || []
      return (
        <Card key={agent.id} className="group hover:bg-secondary/40 hover:-translate-y-0.5 transition-all duration-200 flex flex-col justify-between shadow-xs">
          <CardHeader className="p-5">
            <div className="flex items-start justify-between">
              <div className={`p-2.5 rounded-[8px] bg-secondary border border-border shadow-xs ${color}`}>
                <Icon className="h-5 w-5 stroke-[1.5]" />
              </div>
              <Link 
                href={`/chat?agent=${agent.id}`} 
                className={`${buttonVariants({ variant: 'outline', size: 'sm' })} text-xs h-7 px-2.5 rounded-[8px] opacity-0 group-hover:opacity-100 transition-opacity`}
              >
                Chat
              </Link>
            </div>
            <CardTitle className="mt-4 text-base font-semibold text-foreground">{agent.name}</CardTitle>
            <CardDescription className="text-xs text-muted-foreground leading-normal mt-1 min-h-[32px] line-clamp-2">{agent.description}</CardDescription>
          </CardHeader>
          <CardContent className="p-5 pt-0">
            <div className="flex flex-wrap gap-1.5 mb-4">
              {tags.map((tag) => (
                <Badge key={tag} variant="secondary" className="bg-secondary text-muted-foreground font-normal text-[10px] px-2.5 py-0.5 border border-border shadow-none">{tag}</Badge>
              ))}
            </div>
            {agent.custom && (
              <div className="flex items-center gap-2">
                <Button 
                  variant="outline" 
                  size="sm" 
                  onClick={() => startTest(agent.id, agent.name, agent.tools || [])} 
                  className="gap-1.5 text-xs h-8 px-2 rounded-[8px]"
                >
                  <Send className="h-3.5 w-3.5" /> 
                  Test
                </Button>
                <Button 
                  variant="ghost" 
                  size="sm" 
                  onClick={() => deleteAgent(agent.id)} 
                  className="gap-1.5 text-xs text-[#c64545] hover:bg-[#c64545]/10 h-8 px-2 rounded-[8px]"
                >
                  <Trash2 className="h-3.5 w-3.5" /> 
                  Delete
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      )
    })
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in bg-background">
        <div>
          <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-foreground">Agents</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Manage your specialized AI agents
          </p>
        </div>
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-primary" />
            <p>Loading agents...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in bg-background">
      <div>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-[#26251e]">Agent Hub</h1>
            <p className="text-sm text-muted-foreground mt-1">{agents.length} agents available · build your own specialist</p>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/workflows" className={buttonVariants({ variant: 'outline', size: 'default' })}>
              <Workflow className="mr-2 h-4 w-4" /> Build workflow
            </Link>
            <Button onClick={() => setBuilderOpen((open) => !open)} className="gap-2 shadow-sm">
              <Plus className="h-4 w-4" /> Create agent
            </Button>
          </div>
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

      {testFor && (
        <Card className="border-primary/30 shadow-sm">
          <CardHeader className="pb-3">
            <div className="flex items-start justify-between">
              <div>
                <CardTitle className="font-sans font-normal tracking-[-0.02em] text-lg">
                  Test agent — {testFor.name}
                </CardTitle>
                <CardDescription className="text-muted-foreground">
                  {testTools.length > 0 && (
                    <span className="text-xs">Tools used: {testTools.join(', ')}</span>
                  )}
                </CardDescription>
              </div>
              <Button variant="ghost" size="sm" onClick={() => setTestFor(null)} className="h-7 w-7 p-0">
                <X className="h-4 w-4" />
              </Button>
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-end gap-2">
              <Textarea
                placeholder="Send a message to this agent..."
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                className="min-h-16 flex-1"
                disabled={testRunning}
              />
              <Button onClick={runTest} disabled={!testMessage.trim() || testRunning} className="shrink-0 gap-2">
                {testRunning ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                {testRunning ? 'Running…' : 'Run'}
              </Button>
            </div>
            {testOutput && (
              <div className="rounded-[10px] border border-border bg-background p-4">
                <p className="whitespace-pre-wrap text-sm text-foreground leading-relaxed">{testOutput}</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {builderOpen && (
        <Card className="border-primary/20 hover:bg-card shadow-xs">
          <CardHeader>
            <CardTitle className="font-sans font-normal tracking-[-0.02em] text-lg">Build a custom agent</CardTitle>
            <CardDescription className="text-muted-foreground">Give it a clear job, personality, and only the tools it needs.</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4 md:grid-cols-2">
            <div className="space-y-3">
              <Input placeholder="Agent name" value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })} />
              <Input placeholder="Short description" value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} />
              <Textarea placeholder="System instructions — what should this agent do?" value={draft.system_instruction} onChange={(e) => setDraft({ ...draft, system_instruction: e.target.value })} className="min-h-32" />
            </div>
            <div className="rounded-[12px] border border-border bg-secondary p-4 flex flex-col justify-between">
              <div>
                <p className="mb-3 text-sm font-semibold text-foreground">Tool permissions</p>
                <div className="space-y-3">
                  {availableTools.map((tool) => (
                    <label key={tool.id} className="flex cursor-pointer items-center gap-3 text-sm text-muted-foreground hover:text-foreground transition-colors">
                      <input 
                        type="checkbox" 
                        checked={draft.tools.includes(tool.id)} 
                        onChange={(e) => setDraft({ ...draft, tools: e.target.checked ? [...draft.tools, tool.id] : draft.tools.filter((id) => id !== tool.id) })} 
                        className="h-4 w-4 rounded border-border text-primary focus:ring-primary cursor-pointer" 
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
