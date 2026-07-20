'use client'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useSession } from 'next-auth/react'
import {
  ArrowRight,
  Bot,
  BookOpen,
  Brain,
  Calendar,
  CalendarDays,
  Check,
  ChevronRight,
  CircleStop,
  FileCode,
  GripVertical,
  HardDrive,
  Image as ImageIcon,
  Loader2,
  Play,
  Plus,
  Puzzle,
  RotateCcw,
  Save,
  Search,
  StickyNote,
  Trash2,
  Workflow,
  X,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { api } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { cn } from '@/lib/utils'

type AgentInfo = {
  id: string
  name: string
  description: string
  icon: string
  capabilities?: string[]
  custom?: boolean
}

type WorkflowDefinition = {
  name: string
  agentIds: string[]
  updatedAt: string
}

type RunState = 'idle' | 'running' | 'complete' | 'error'

const STORAGE_KEY = 'agentic_workflow_v1'
const DEFAULT_AGENT_IDS = ['research', 'knowledge', 'notes']

const iconMap: Record<string, LucideIcon> = {
  Bot,
  BookOpen,
  Brain,
  Calendar,
  CalendarDays,
  FileCode,
  HardDrive,
  Image: ImageIcon,
  Puzzle,
  Search,
  StickyNote,
}

const nodeAccents = ['#f54e00', '#1877a8', '#1f8a65', '#8755a5', '#b06c19']

function loadWorkflow(): WorkflowDefinition | null {
  if (typeof window === 'undefined') return null
  try {
    const value = window.localStorage.getItem(STORAGE_KEY)
    return value ? JSON.parse(value) as WorkflowDefinition : null
  } catch {
    return null
  }
}

function AgentGlyph({ agent, className }: { agent: AgentInfo; className?: string }) {
  const Icon = iconMap[agent.icon] || Bot
  return <Icon className={cn('h-4 w-4', className)} strokeWidth={1.8} />
}

function CanvasNode({
  agent,
  index,
  selected,
  runState,
  draggable,
  onSelect,
  onDragStart,
  onDragOver,
  onDrop,
  onRemove,
}: {
  agent: AgentInfo
  index: number
  selected: boolean
  runState: RunState
  draggable: boolean
  onSelect: () => void
  onDragStart: () => void
  onDragOver: (event: React.DragEvent) => void
  onDrop: () => void
  onRemove: () => void
}) {
  const accent = nodeAccents[index % nodeAccents.length]
  return (
    <div className="flex shrink-0 items-center">
      {index > 0 ? (
        <div className="relative h-px w-12 bg-[#b9c1c7] sm:w-16" aria-hidden="true">
          <ArrowRight className="absolute -right-1.5 -top-2 h-4 w-4 text-[#62717b]" />
          <span className="absolute -top-3 left-1/2 h-1.5 w-1.5 -translate-x-1/2 rounded-full bg-[#1877a8]" />
        </div>
      ) : null}
      <div
        draggable={draggable}
        onDragStart={onDragStart}
        onDragOver={onDragOver}
        onDrop={onDrop}
        onClick={onSelect}
        role="button"
        tabIndex={0}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') onSelect()
        }}
        className={cn(
          'group relative h-[164px] w-[224px] cursor-pointer border bg-white text-left shadow-[0_8px_24px_rgba(38,37,30,0.06)] outline-none transition-[border-color,box-shadow,transform] duration-150',
          'focus-visible:ring-2 focus-visible:ring-[#f54e00] focus-visible:ring-offset-2',
          selected ? 'border-[#26251e] shadow-[0_10px_32px_rgba(38,37,30,0.12)]' : 'border-[#d8d8d2] hover:border-[#aaa9a1]',
          draggable ? 'active:cursor-grabbing active:scale-[0.98]' : '',
        )}
        style={{ borderTop: `3px solid ${accent}` }}
      >
        <div className="flex h-9 items-center justify-between border-b border-[#ecece7] px-3">
          <span className="font-mono text-[10px] font-semibold text-[#78766f]">STEP {String(index + 1).padStart(2, '0')}</span>
          <div className="flex items-center gap-1">
            {runState === 'running' ? <Loader2 className="h-3.5 w-3.5 animate-spin text-[#1877a8]" /> : null}
            {runState === 'complete' ? <Check className="h-3.5 w-3.5 text-[#1f8a65]" /> : null}
            <GripVertical className="h-4 w-4 text-[#aaa9a1]" />
          </div>
        </div>
        <div className="p-3.5">
          <div className="mb-3 flex h-8 w-8 items-center justify-center border border-[#deded8] bg-[#f7f7f4]" style={{ color: accent }}>
            <AgentGlyph agent={agent} />
          </div>
          <p className="truncate text-sm font-semibold text-[#26251e]">{agent.name}</p>
          <p className="mt-1 line-clamp-2 text-[11px] leading-4 text-[#6c6a64]">{agent.description}</p>
        </div>
        <button
          type="button"
          title="Remove stage"
          aria-label={`Remove ${agent.name}`}
          onClick={(event) => { event.stopPropagation(); onRemove() }}
          className="absolute -right-2 -top-2 hidden h-7 w-7 items-center justify-center border border-[#d8d8d2] bg-white text-[#6c6a64] shadow-sm hover:text-[#c64545] group-hover:flex group-focus-within:flex"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  )
}

export default function WorkflowsPage() {
  const { data: session } = useSession()
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [agentIds, setAgentIds] = useState<string[]>(DEFAULT_AGENT_IDS)
  const [workflowName, setWorkflowName] = useState('Research brief pipeline')
  const [selectedIndex, setSelectedIndex] = useState(0)
  const [dragIndex, setDragIndex] = useState<number | null>(null)
  const [query, setQuery] = useState('')
  const [prompt, setPrompt] = useState('Research the topic, verify the key claims, and turn the findings into concise structured notes.')
  const [runState, setRunState] = useState<RunState>('idle')
  const [activeStage, setActiveStage] = useState<number | null>(null)
  const [output, setOutput] = useState('')
  const [error, setError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    const saved = loadWorkflow()
    if (saved) {
      setWorkflowName(saved.name)
      setAgentIds(saved.agentIds)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    api.agents.list().then((response) => {
      if (!cancelled && response.success && response.data) {
        setAgents(response.data.filter((agent) => !agent.custom))
      } else if (!cancelled) {
        setError(response.error || 'Could not load agents')
      }
    }).catch(() => {
      if (!cancelled) setError('Could not connect to the agent service')
    })
    return () => { cancelled = true }
  }, [])

  const agentById = useMemo(() => new Map(agents.map((agent) => [agent.id, agent])), [agents])
  const chain = useMemo(
    () => agentIds.map((id) => agentById.get(id)).filter((agent): agent is AgentInfo => Boolean(agent)),
    [agentById, agentIds],
  )
  const availableAgents = useMemo(() => {
    const selected = new Set(agentIds)
    const normalized = query.trim().toLowerCase()
    return agents.filter((agent) => {
      if (selected.has(agent.id)) return false
      if (!normalized) return true
      return `${agent.name} ${agent.description}`.toLowerCase().includes(normalized)
    })
  }, [agentIds, agents, query])
  const selectedAgent = chain[selectedIndex]

  const addAgent = useCallback((agentId: string) => {
    setAgentIds((current) => current.includes(agentId) ? current : [...current, agentId])
    setSelectedIndex(agentIds.length)
    setRunState('idle')
    setOutput('')
  }, [agentIds.length])

  const removeAgent = useCallback((index: number) => {
    setAgentIds((current) => current.filter((_, itemIndex) => itemIndex !== index))
    setSelectedIndex((current) => Math.max(0, Math.min(current, agentIds.length - 2)))
    setRunState('idle')
    setOutput('')
  }, [agentIds.length])

  const moveAgent = useCallback((from: number, to: number) => {
    if (from === to) return
    setAgentIds((current) => {
      const next = [...current]
      const [moved] = next.splice(from, 1)
      next.splice(to, 0, moved)
      return next
    })
    setSelectedIndex(to)
    setRunState('idle')
  }, [])

  const saveWorkflow = useCallback(() => {
    const definition: WorkflowDefinition = {
      name: workflowName.trim() || 'Untitled workflow',
      agentIds,
      updatedAt: new Date().toISOString(),
    }
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(definition))
  }, [agentIds, workflowName])

  const resetWorkflow = useCallback(() => {
    setAgentIds(DEFAULT_AGENT_IDS)
    setWorkflowName('Research brief pipeline')
    setSelectedIndex(0)
    setRunState('idle')
    setActiveStage(null)
    setOutput('')
    setError(null)
  }, [])

  const runWorkflow = useCallback(async () => {
    if (chain.length === 0 || !prompt.trim()) return
    setRunState('running')
    setOutput('')
    setError(null)
    setActiveStage(0)
    const controller = new AbortController()
    abortRef.current = controller

    const timer = window.setInterval(() => {
      setActiveStage((current) => current === null ? 0 : Math.min(current + 1, chain.length - 1))
    }, 1200)

    try {
      const googleAccessToken = (session as { accessToken?: string } | null)?.accessToken
      const response = await api.chat.send({
        message: prompt.trim(),
        team_agents: chain.map((agent) => agent.id),
      }, googleAccessToken)
      if (!response.success || !response.data) throw new Error(response.error || 'Workflow execution failed')
      setActiveStage(chain.length - 1)
      setOutput(response.data.output)
      setRunState('complete')
    } catch (runError) {
      if (controller.signal.aborted) {
        setError('Run stopped')
      } else {
        setError(runError instanceof Error ? runError.message : 'Workflow execution failed')
      }
      setRunState('error')
    } finally {
      window.clearInterval(timer)
      abortRef.current = null
    }
  }, [chain, prompt, session])

  const stopWorkflow = useCallback(() => {
    abortRef.current?.abort()
    setRunState('idle')
    setActiveStage(null)
  }, [])

  return (
    <div className="flex min-h-full flex-col bg-[#f7f7f4] text-[#26251e]">
      <header className="flex flex-col gap-4 border-b border-[#dcdcd6] pb-5 md:flex-row md:items-center md:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 font-mono text-[10px] font-semibold uppercase text-[#1877a8]">
            <Workflow className="h-3.5 w-3.5" /> Workflow studio
          </div>
          <Input
            aria-label="Workflow name"
            value={workflowName}
            onChange={(event) => setWorkflowName(event.target.value)}
            className="h-auto max-w-xl border-0 bg-transparent p-0 text-2xl font-medium shadow-none focus-visible:ring-0 sm:text-3xl"
          />
          <p className="mt-1 text-xs text-[#6c6a64]">{chain.length} stages · sequential handoff · saved in this browser</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={resetWorkflow} title="Reset workflow" className="h-9 w-9 p-0">
            <RotateCcw className="h-4 w-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={saveWorkflow} className="gap-2">
            <Save className="h-4 w-4" /> Save
          </Button>
          {runState === 'running' ? (
            <Button size="sm" variant="destructive" onClick={stopWorkflow} className="gap-2">
              <CircleStop className="h-4 w-4" /> Stop
            </Button>
          ) : (
            <Button size="sm" onClick={runWorkflow} disabled={chain.length === 0 || !prompt.trim()} className="gap-2">
              <Play className="h-4 w-4 fill-current" /> Run workflow
            </Button>
          )}
        </div>
      </header>

      {error ? (
        <div className="mt-4 flex items-center justify-between border border-[#e7b4b4] bg-[#fff7f7] px-3 py-2 text-xs text-[#a93636]">
          <span>{error}</span>
          <button type="button" aria-label="Dismiss error" onClick={() => setError(null)}><X className="h-4 w-4" /></button>
        </div>
      ) : null}

      <div className="mt-5 grid min-h-[640px] flex-1 grid-cols-1 border border-[#d8d8d2] bg-white lg:grid-cols-[230px_minmax(0,1fr)_280px]">
        <aside className="border-b border-[#d8d8d2] bg-[#fbfbf8] lg:border-b-0 lg:border-r">
          <div className="border-b border-[#e5e5df] p-3">
            <p className="font-mono text-[10px] font-semibold uppercase text-[#77756e]">Agent library</p>
            <div className="relative mt-3">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-[#898780]" />
              <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find an agent" className="h-8 bg-white pl-8 text-xs" />
            </div>
          </div>
          <div className="grid max-h-52 grid-cols-2 overflow-y-auto p-2 lg:max-h-[570px] lg:grid-cols-1">
            {availableAgents.map((agent) => (
              <button
                key={agent.id}
                type="button"
                onClick={() => addAgent(agent.id)}
                className="group flex min-h-16 items-center gap-2.5 border-b border-[#ecece7] px-2 py-2 text-left hover:bg-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[#f54e00]"
              >
                <span className="flex h-8 w-8 shrink-0 items-center justify-center border border-[#deded8] bg-white text-[#1877a8]">
                  <AgentGlyph agent={agent} />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block truncate text-xs font-semibold">{agent.name.replace(' Agent', '')}</span>
                  <span className="mt-0.5 block truncate text-[10px] text-[#77756e]">{agent.capabilities?.[0]?.replaceAll('_', ' ') || 'Specialist'}</span>
                </span>
                <Plus className="h-3.5 w-3.5 shrink-0 text-[#aaa9a1] group-hover:text-[#f54e00]" />
              </button>
            ))}
            {availableAgents.length === 0 ? <p className="p-3 text-xs text-[#77756e]">No agents match.</p> : null}
          </div>
        </aside>

        <main className="relative min-h-[430px] min-w-0 overflow-hidden bg-[#f8faf9]">
          <div
            className="absolute inset-0 opacity-60"
            aria-hidden="true"
            style={{
              backgroundImage: 'linear-gradient(#dfe5e2 1px, transparent 1px), linear-gradient(90deg, #dfe5e2 1px, transparent 1px)',
              backgroundSize: '24px 24px',
            }}
          />
          <div className="absolute left-3 top-3 z-10 flex items-center gap-2 border border-[#d8d8d2] bg-white px-2.5 py-1.5 font-mono text-[9px] uppercase text-[#77756e] shadow-sm">
            <span className={cn('h-1.5 w-1.5 rounded-full', runState === 'running' ? 'animate-pulse bg-[#1f8a65]' : 'bg-[#aaa9a1]')} />
            {runState === 'running' ? 'Signal active' : 'Canvas ready'}
          </div>
          <div className="relative z-[1] flex h-full min-h-[430px] items-center overflow-x-auto px-10 pb-12 pt-16 scrollbar-thin">
            {chain.length > 0 ? chain.map((agent, index) => (
              <CanvasNode
                key={agent.id}
                agent={agent}
                index={index}
                selected={selectedIndex === index}
                runState={runState === 'complete' || (runState === 'running' && activeStage !== null && index < activeStage) ? 'complete' : runState === 'running' && activeStage === index ? 'running' : 'idle'}
                draggable={runState !== 'running'}
                onSelect={() => setSelectedIndex(index)}
                onDragStart={() => setDragIndex(index)}
                onDragOver={(event) => event.preventDefault()}
                onDrop={() => { if (dragIndex !== null) moveAgent(dragIndex, index); setDragIndex(null) }}
                onRemove={() => removeAgent(index)}
              />
            )) : (
              <button type="button" onClick={() => availableAgents[0] && addAgent(availableAgents[0].id)} className="mx-auto flex h-40 w-64 flex-col items-center justify-center border border-dashed border-[#aeb8b2] bg-white/80 text-[#6c6a64] hover:border-[#f54e00] hover:text-[#26251e]">
                <Plus className="mb-2 h-5 w-5" />
                <span className="text-sm font-medium">Add the first stage</span>
              </button>
            )}
          </div>
          <div className="absolute bottom-3 left-3 z-10 font-mono text-[9px] uppercase text-[#77756e]">Drag stages to change handoff order</div>
        </main>

        <aside className="border-t border-[#d8d8d2] bg-white lg:border-l lg:border-t-0">
          <div className="border-b border-[#e5e5df] px-4 py-3">
            <p className="font-mono text-[10px] font-semibold uppercase text-[#77756e]">Inspector</p>
          </div>
          {selectedAgent ? (
            <div className="p-4">
              <div className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center border border-[#deded8] bg-[#f7f7f4] text-[#f54e00]"><AgentGlyph agent={selectedAgent} /></span>
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold">{selectedAgent.name}</p>
                  <p className="font-mono text-[9px] uppercase text-[#77756e]">Stage {selectedIndex + 1}</p>
                </div>
              </div>
              <p className="mt-4 text-xs leading-5 text-[#65635d]">{selectedAgent.description}</p>
              <div className="mt-4 border-t border-[#ecece7] pt-4">
                <p className="mb-2 font-mono text-[9px] font-semibold uppercase text-[#77756e]">Capabilities</p>
                <div className="flex flex-wrap gap-1.5">
                  {(selectedAgent.capabilities || []).slice(0, 4).map((capability) => (
                    <span key={capability} className="border border-[#deded8] bg-[#f7f7f4] px-2 py-1 text-[9px] text-[#65635d]">{capability.replaceAll('_', ' ')}</span>
                  ))}
                </div>
              </div>
              <Button variant="ghost" size="sm" onClick={() => removeAgent(selectedIndex)} className="mt-5 gap-2 px-0 text-xs text-[#b53d3d] hover:bg-transparent hover:text-[#8e2727]">
                <Trash2 className="h-3.5 w-3.5" /> Remove stage
              </Button>
            </div>
          ) : <p className="p-4 text-xs text-[#77756e]">Select a stage to inspect it.</p>}

          <div className="border-t border-[#e5e5df] p-4">
            <label htmlFor="workflow-input" className="font-mono text-[10px] font-semibold uppercase text-[#77756e]">Run input</label>
            <Textarea id="workflow-input" value={prompt} onChange={(event) => setPrompt(event.target.value)} className="mt-2 min-h-28 resize-y text-xs leading-5" />
            <div className="mt-3 flex items-center justify-between text-[10px] text-[#77756e]">
              <span>Output of each stage feeds the next</span>
              <ChevronRight className="h-3.5 w-3.5" />
            </div>
          </div>
        </aside>
      </div>

      {output ? (
        <section className="mt-5 border border-[#d8d8d2] bg-white">
          <div className="flex items-center justify-between border-b border-[#e5e5df] px-4 py-3">
            <div className="flex items-center gap-2">
              <Check className="h-4 w-4 text-[#1f8a65]" />
              <h2 className="text-sm font-semibold tracking-normal">Run output</h2>
            </div>
            <span className="font-mono text-[9px] uppercase text-[#1f8a65]">Complete</span>
          </div>
          <pre className="max-h-[420px] overflow-auto whitespace-pre-wrap p-4 font-sans text-xs leading-6 text-[#3f3e39] scrollbar-thin">{output}</pre>
        </section>
      ) : null}
    </div>
  )
}
