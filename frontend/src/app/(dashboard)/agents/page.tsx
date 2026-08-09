'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import {
  Bot,
  Search,
  Code2,
  Globe,
  PenTool,
  Palette,
  BarChart2,
  Briefcase,
  Brain,
  Workflow,
  ShieldCheck,
  Loader2,
  Plus,
  Send,
  X,
  Sparkles,
  Layers,
  Terminal,
  Server,
  Database,
  Cpu,
  CheckCircle,
  Zap,
} from 'lucide-react'
import { api } from '@/lib/api'

const DEPARTMENTS = [
  'All 100 Agents',
  'Command and Planning',
  'Coding',
  'Research',
  'Content',
  'Visual',
  'Data',
  'Product',
  'AI and ML',
  'Automation',
  'Business and Quality',
]

const departmentIconMap: Record<string, import('lucide-react').LucideIcon> = {
  'Command and Planning': Workflow,
  Coding: Code2,
  Research: Globe,
  Content: PenTool,
  Visual: Palette,
  Data: BarChart2,
  Product: Briefcase,
  'AI and ML': Brain,
  Automation: Zap,
  'Business and Quality': ShieldCheck,
}

interface AgentItem {
  id: string
  name: string
  department?: string
  description: string
  icon?: string
  capabilities?: string[]
  responsibilities?: string[]
  tools?: string[]
  custom?: boolean
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<AgentItem[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [activeDepartment, setActiveDepartment] = useState('All 100 Agents')
  const [searchQuery, setSearchQuery] = useState('')

  // Test Modal State
  const [testFor, setTestFor] = useState<AgentItem | null>(null)
  const [testMessage, setTestMessage] = useState('')
  const [testOutput, setTestOutput] = useState('')
  const [testRunning, setTestRunning] = useState(false)

  // Custom Agent Builder Modal State
  const [builderOpen, setBuilderOpen] = useState(false)
  const [saving, setSaving] = useState(false)
  const [draft, setDraft] = useState({
    name: '',
    description: '',
    icon: 'Bot',
    system_instruction: '',
    tools: [] as string[],
  })

  useEffect(() => {
    let mounted = true
    const fetchAgents = async () => {
      setLoading(true)
      try {
        const res = await api.agents.list()
        if (mounted && res.success && res.data) {
          setAgents(res.data as any)
        } else if (mounted && Array.isArray(res)) {
          setAgents(res as any)
        } else if (mounted) {
          setError('Failed to load agents')
        }
      } catch (e: any) {
        if (mounted) setError(e.message || 'Failed to load agents')
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchAgents()
    return () => {
      mounted = false
    }
  }, [])

  const filteredAgents = agents.filter((agent) => {
    const matchesDept =
      activeDepartment === 'All 100 Agents' ||
      (agent.department && agent.department.toLowerCase() === activeDepartment.toLowerCase())
    const q = searchQuery.toLowerCase().trim()
    const matchesQuery =
      !q ||
      agent.name.toLowerCase().includes(q) ||
      agent.id.toLowerCase().includes(q) ||
      agent.description.toLowerCase().includes(q) ||
      (agent.capabilities && agent.capabilities.some((c) => c.toLowerCase().includes(q)))

    return matchesDept && matchesQuery
  })

  const runSingleAgentTest = async () => {
    if (!testFor || !testMessage.trim()) return
    setTestRunning(true)
    setTestOutput('')
    try {
      const res = await api.agentPlatform.execute(testMessage.trim(), `test_${testFor.id}`)
      if (res.success && res.data && res.data.output) {
        setTestOutput(res.data.output)
      } else {
        setTestOutput('No output received from agent execution.')
      }
    } catch (err: any) {
      setTestOutput(`Execution Error: ${err.message || err}`)
    } finally {
      setTestRunning(false)
    }
  }

  const handleCreateCustom = async () => {
    if (!draft.name.trim() || !draft.system_instruction.trim()) return
    setSaving(true)
    try {
      const res = await api.agents.create(draft)
      if (res && res.id) {
        setAgents((prev) => [res as any, ...prev])
        setBuilderOpen(false)
        setDraft({ name: '', description: '', icon: 'Bot', system_instruction: '', tools: [] })
      }
    } catch (err: any) {
      alert(`Failed to save custom agent: ${err.message}`)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="container mx-auto p-6 space-y-8 max-w-7xl">
      {/* Header Banner */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 border-b border-border pb-6">
        <div>
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-xl bg-primary/10 text-primary border border-primary/20">
              <Sparkles className="w-6 h-6" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">100 Specialized AI Agents</h1>
              <p className="text-muted-foreground text-sm mt-1">
                Executive Boss Agent Orchestrator with capability-based routing across 10 functional departments
              </p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="px-3 py-1 text-xs border-primary/30 text-primary bg-primary/5">
            <CheckCircle className="w-3.5 h-3.5 mr-1 text-emerald-500" />
            {agents.length} Agents Active
          </Badge>
          <Button onClick={() => setBuilderOpen(true)} className="gap-2 shadow-sm">
            <Plus className="w-4 h-4" /> Create Custom Agent
          </Button>
        </div>
      </div>

      {/* Search & Department Selector */}
      <div className="space-y-4">
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
          <Input
            placeholder="Search agents by name, capability, or slug ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Department Tabs */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2 scrollbar-none">
          {DEPARTMENTS.map((dept) => {
            const Icon = departmentIconMap[dept] || Layers
            const isActive = activeDepartment === dept
            const count =
              dept === 'All 100 Agents'
                ? agents.length
                : agents.filter((a) => a.department && a.department.toLowerCase() === dept.toLowerCase()).length

            return (
              <button
                key={dept}
                onClick={() => setActiveDepartment(dept)}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-medium transition-all whitespace-nowrap border ${
                  isActive
                    ? 'bg-primary text-primary-foreground border-primary shadow-sm'
                    : 'bg-card text-muted-foreground hover:text-foreground hover:bg-accent/50 border-border'
                }`}
              >
                <Icon className="w-3.5 h-3.5" />
                <span>{dept}</span>
                <span
                  className={`ml-1 px-1.5 py-0.5 rounded-full text-[10px] ${
                    isActive ? 'bg-primary-foreground/20 text-primary-foreground' : 'bg-muted text-muted-foreground'
                  }`}
                >
                  {count}
                </span>
              </button>
            )
          })}
        </div>
      </div>

      {/* Agents Grid */}
      {loading ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3 text-muted-foreground">
          <Loader2 className="w-8 h-8 animate-spin text-primary" />
          <p className="text-sm">Loading specialized agent registry...</p>
        </div>
      ) : error ? (
        <div className="p-4 rounded-lg bg-destructive/10 text-destructive text-sm border border-destructive/20">
          {error}
        </div>
      ) : filteredAgents.length === 0 ? (
        <div className="text-center py-16 border rounded-xl border-dashed">
          <Bot className="w-10 h-10 mx-auto text-muted-foreground mb-3 opacity-40" />
          <h3 className="text-base font-semibold">No specialized agents found</h3>
          <p className="text-xs text-muted-foreground mt-1">Try adjusting your search query or department filter.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
          {filteredAgents.map((agent) => {
            const DeptIcon = (agent.department && departmentIconMap[agent.department]) || Bot

            return (
              <Card
                key={agent.id}
                className="group relative flex flex-col justify-between hover:shadow-md transition-all border-border hover:border-primary/40"
              >
                <CardHeader className="pb-3">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-3">
                      <div className="p-2.5 rounded-lg bg-primary/10 text-primary group-hover:scale-105 transition-transform border border-primary/20">
                        <DeptIcon className="w-5 h-5" />
                      </div>
                      <div>
                        <CardTitle className="text-base font-semibold group-hover:text-primary transition-colors">
                          {agent.name}
                        </CardTitle>
                        <span className="font-mono text-[11px] text-muted-foreground">{agent.id}</span>
                      </div>
                    </div>
                    {agent.department && (
                      <Badge variant="outline" className="text-[10px] px-2 py-0.5 whitespace-nowrap bg-muted/50">
                        {agent.department}
                      </Badge>
                    )}
                  </div>
                  <CardDescription className="text-xs line-clamp-2 mt-2 leading-relaxed">
                    {agent.description}
                  </CardDescription>
                </CardHeader>

                <CardContent className="space-y-3 pt-0">
                  {/* Capability Tags */}
                  {agent.capabilities && agent.capabilities.length > 0 && (
                    <div className="flex flex-wrap gap-1.5">
                      {agent.capabilities.slice(0, 4).map((cap) => (
                        <Badge
                          key={cap}
                          variant="secondary"
                          className="text-[10px] px-2 py-0 bg-secondary/60 text-secondary-foreground font-normal"
                        >
                          {cap}
                        </Badge>
                      ))}
                      {agent.capabilities.length > 4 && (
                        <span className="text-[10px] text-muted-foreground self-center">
                          +{agent.capabilities.length - 4} more
                        </span>
                      )}
                    </div>
                  )}

                  {/* Actions */}
                  <div className="pt-2 border-t border-border/50 flex items-center justify-between gap-2">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        setTestFor(agent)
                        setTestMessage('')
                        setTestOutput('')
                      }}
                      className="w-full text-xs gap-1.5"
                    >
                      <Terminal className="w-3.5 h-3.5" /> Test Specialist
                    </Button>
                  </div>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      {/* Single Agent Test Playground Modal */}
      {testFor && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-xl p-6 space-y-4 relative">
            <button
              onClick={() => setTestFor(null)}
              className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>
            <div className="flex items-center gap-3">
              <div className="p-2 rounded-lg bg-primary/10 text-primary">
                <Bot className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">{testFor.name}</h3>
                <p className="text-xs text-muted-foreground font-mono">{testFor.id}</p>
              </div>
            </div>

            <div className="space-y-2">
              <label className="text-xs font-medium">Test Prompt</label>
              <Textarea
                placeholder={`Ask ${testFor.name} a specialized question...`}
                value={testMessage}
                onChange={(e) => setTestMessage(e.target.value)}
                rows={3}
                className="text-xs font-mono"
              />
            </div>

            <Button
              onClick={runSingleAgentTest}
              disabled={testRunning || !testMessage.trim()}
              className="w-full gap-2"
            >
              {testRunning ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
              {testRunning ? 'Executing Specialist Agent...' : 'Run Execution'}
            </Button>

            {testOutput && (
              <div className="space-y-1.5 pt-2">
                <label className="text-xs font-medium text-muted-foreground">Execution Output</label>
                <div className="p-3.5 rounded-lg bg-muted/60 text-xs font-mono max-h-60 overflow-y-auto whitespace-pre-wrap border border-border">
                  {testOutput}
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Create Custom Agent Modal */}
      {builderOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-card border border-border rounded-xl shadow-2xl w-full max-w-md p-6 space-y-4 relative">
            <button
              onClick={() => setBuilderOpen(false)}
              className="absolute right-4 top-4 text-muted-foreground hover:text-foreground"
            >
              <X className="w-5 h-5" />
            </button>
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <Plus className="w-5 h-5 text-primary" /> Create Custom Agent
            </h3>

            <div className="space-y-3">
              <div>
                <label className="text-xs font-medium">Agent Name</label>
                <Input
                  placeholder="e.g. Legal Compliance Analyst"
                  value={draft.name}
                  onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                  className="mt-1 text-xs"
                />
              </div>
              <div>
                <label className="text-xs font-medium">Description</label>
                <Input
                  placeholder="e.g. Analyzes contracts and regulatory frameworks"
                  value={draft.description}
                  onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                  className="mt-1 text-xs"
                />
              </div>
              <div>
                <label className="text-xs font-medium">System Instructions</label>
                <Textarea
                  placeholder="Define the prompt system instructions..."
                  value={draft.system_instruction}
                  onChange={(e) => setDraft({ ...draft, system_instruction: e.target.value })}
                  rows={4}
                  className="mt-1 text-xs font-mono"
                />
              </div>
            </div>

            <Button onClick={handleCreateCustom} disabled={saving} className="w-full gap-2">
              {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
              {saving ? 'Registering Agent...' : 'Register Custom Agent'}
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
