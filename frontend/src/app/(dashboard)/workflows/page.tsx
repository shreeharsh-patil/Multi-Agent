'use client'

/**
 * Visual Multi-Agent Workflow DAG Builder
 *
 * Canvas: pan by dragging the background, zoom by scrolling.
 * Nodes: drag to reposition, click output port then input port to connect.
 * Edges: cubic bezier SVG paths. Click an edge to delete it.
 * Toolbar: new workflow, save, run with SSE streaming per-node status.
 */

import React, {
  useCallback, useEffect, useMemo, useRef, useState, type PointerEvent,
} from 'react'
import { useSession } from 'next-auth/react'
import {
  AlertCircle, BarChart2, Bot, BookOpen, Brain, BrainCircuit,
  Calendar, CalendarDays, Check, ChevronRight, CircleStop,
  FileCode, FilePlus2, GraduationCap, HardDrive, Image as ImageIcon,
  Loader2, Play, Plus, Puzzle, RotateCcw, Save, Search,
  StickyNote, Trash2, Workflow, X, ZoomIn, ZoomOut,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { api } from '@/lib/api'
import { getAccessToken } from '@/lib/auth-store'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

// ── Types ──────────────────────────────────────────────────────────────────

interface AgentInfo {
  id: string
  name: string
  description: string
  icon: string
  capabilities?: string[]
}

interface WFNode {
  id: string
  agentId: string
  label: string
  x: number
  y: number
}

interface WFEdge {
  id: string
  source: string   // node id
  target: string   // node id
}

interface Workflow {
  id?: string
  name: string
  description: string
  prompt: string
  nodes: WFNode[]
  edges: WFEdge[]
}

type RunStatus = 'idle' | 'running' | 'complete' | 'error'
type NodeRunStatus = 'idle' | 'running' | 'complete' | 'error'

// ── Icon map ───────────────────────────────────────────────────────────────

const ICON_MAP: Record<string, LucideIcon> = {
  Bot, BookOpen, Brain, BrainCircuit, Calendar, CalendarDays,
  FileCode, GraduationCap, HardDrive, Image: ImageIcon,
  Puzzle, Search, StickyNote, Workflow, BarChart2,
}

const ACCENT_COLORS = [
  '#f54e00', '#1877a8', '#1f8a65', '#8755a5',
  '#b06c19', '#2dd4bf', '#f472b6', '#60a5fa',
]

function AgentIcon({ iconName, className }: { iconName: string; className?: string }) {
  const Icon = ICON_MAP[iconName] || Bot
  return <Icon className={className ?? 'w-4 h-4'} strokeWidth={1.8} />
}

// ── Constants ──────────────────────────────────────────────────────────────

const NODE_W = 180
const NODE_H = 110
const PORT_R = 6
const GRID_SIZE = 24

// ── Canvas helpers ─────────────────────────────────────────────────────────

function snapToGrid(v: number) {
  return Math.round(v / GRID_SIZE) * GRID_SIZE
}

function outPortXY(node: WFNode) {
  return { x: node.x + NODE_W, y: node.y + NODE_H / 2 }
}

function inPortXY(node: WFNode) {
  return { x: node.x, y: node.y + NODE_H / 2 }
}

function edgePath(src: WFNode, tgt: WFNode): string {
  const s = outPortXY(src)
  const t = inPortXY(tgt)
  const dx = Math.abs(t.x - s.x) * 0.55
  return `M${s.x},${s.y} C${s.x + dx},${s.y} ${t.x - dx},${t.y} ${t.x},${t.y}`
}

function pendingEdgePath(sx: number, sy: number, mx: number, my: number): string {
  const dx = Math.abs(mx - sx) * 0.55
  return `M${sx},${sy} C${sx + dx},${sy} ${mx - dx},${my} ${mx},${my}`
}

function wouldCreateCycle(nodes: WFNode[], edges: WFEdge[], source: string, target: string): boolean {
  const adjacency = new Map(nodes.map(node => [node.id, [] as string[]]))
  for (const edge of edges) adjacency.get(edge.source)?.push(edge.target)
  adjacency.get(source)?.push(target)

  const stack = [target]
  const visited = new Set<string>()
  while (stack.length > 0) {
    const current = stack.pop()!
    if (current === source) return true
    if (visited.has(current)) continue
    visited.add(current)
    stack.push(...(adjacency.get(current) || []))
  }
  return false
}

// ── API helpers ────────────────────────────────────────────────────────────

function getToken() {
  return getAccessToken()
}

async function wfFetch<T>(endpoint: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers.Authorization = `Bearer ${token}`
  const res = await fetch(`${BACKEND_URL}${endpoint}`, { ...opts, headers: { ...headers, ...(opts.headers as Record<string, string> | undefined) } })
  const payload = await res.json()
  if (!res.ok || payload.success === false) {
    throw new Error(payload.error || payload.detail || `Workflow request failed (${res.status})`)
  }
  return (payload.data ?? payload) as T
}

// ── Workflow node component ────────────────────────────────────────────────

interface NodeProps {
  node: WFNode
  agentInfo?: AgentInfo
  accentIndex: number
  selected: boolean
  runStatus: NodeRunStatus
  pendingSource: boolean
  onPointerDown: (e: PointerEvent<HTMLDivElement>) => void
  onClick: () => void
  onOutputPortClick: (e: React.MouseEvent) => void
  onInputPortClick: (e: React.MouseEvent) => void
  onDelete: (e: React.MouseEvent) => void
}

function DAGNode({
  node, agentInfo, accentIndex, selected, runStatus, pendingSource,
  onPointerDown, onClick, onOutputPortClick, onInputPortClick, onDelete,
}: NodeProps) {
  const accent = ACCENT_COLORS[accentIndex % ACCENT_COLORS.length]


  return (
    <g>
      {/* Input port */}
      <circle
        cx={node.x} cy={node.y + NODE_H / 2} r={PORT_R}
        fill="#fff" stroke="#aaa9a1" strokeWidth="1.5"
        className="cursor-crosshair"
        onClick={onInputPortClick}
      />

      {/* Card body — rendered as foreignObject */}
      <foreignObject x={node.x} y={node.y} width={NODE_W} height={NODE_H}>
        <div
          className={`
            absolute inset-0 select-none bg-white border
            shadow-[0_4px_16px_rgba(38,37,30,0.08)]
            transition-[border-color,box-shadow] duration-150
            ${selected ? 'border-[#26251e] shadow-[0_8px_28px_rgba(38,37,30,0.14)]' : 'border-[#d8d8d2] hover:border-[#aaa9a1]'}
            ${pendingSource ? 'ring-2 ring-[#f54e00]' : ''}
          `}
          style={{ borderTop: `3px solid ${accent}`, cursor: 'grab' }}
          onPointerDown={onPointerDown}
          onClick={onClick}
        >
          {/* Status bar */}
          <div className="flex items-center justify-between px-2.5 pt-1.5 pb-1 border-b border-[#f0f0ea]">
            <span className="font-mono text-[9px] font-bold uppercase text-[#78766f] tracking-wider">
              {agentInfo?.id?.toUpperCase().slice(0, 8) ?? 'AGENT'}
            </span>
            <div className="flex items-center gap-1">
              {runStatus === 'running' && <Loader2 className="w-3 h-3 animate-spin text-[#1877a8]" />}
              {runStatus === 'complete' && <Check className="w-3 h-3 text-[#1f8a65]" />}
              {runStatus === 'error' && <AlertCircle className="w-3 h-3 text-[#cf2d56]" />}
              <button
                className="w-4 h-4 flex items-center justify-center text-[#aaa9a1] hover:text-[#cf2d56] transition-colors"
                onClick={onDelete}
              >
                <X className="w-3 h-3" />
              </button>
            </div>
          </div>

          {/* Content */}
          <div className="px-2.5 py-2">
            <div className="w-7 h-7 flex items-center justify-center border border-[#deded8] bg-[#f7f7f4] mb-2" style={{ color: accent }}>
              <AgentIcon iconName={agentInfo?.icon ?? 'Bot'} className="w-3.5 h-3.5" />
            </div>
            <p className="text-xs font-semibold text-[#26251e] truncate leading-tight">
              {agentInfo?.name?.replace(' Agent', '') ?? node.label}
            </p>
            <p className="text-[10px] text-[#78766f] truncate mt-0.5">
              {agentInfo?.capabilities?.[0]?.replaceAll('_', ' ') ?? ''}
            </p>
          </div>
        </div>
      </foreignObject>

      {/* Output port */}
      <circle
        cx={node.x + NODE_W} cy={node.y + NODE_H / 2} r={PORT_R}
        fill={pendingSource ? '#f54e00' : '#fff'}
        stroke={pendingSource ? '#f54e00' : '#aaa9a1'} strokeWidth="1.5"
        className="cursor-crosshair hover:fill-[#f54e00] hover:stroke-[#f54e00] transition-colors"
        onClick={onOutputPortClick}
      />
    </g>
  )
}

// ── Main component ─────────────────────────────────────────────────────────

const EMPTY_WF: Workflow = {
  name: 'My Workflow',
  description: '',
  prompt: 'Research the latest AI trends, summarise the key findings, and produce structured notes.',
  nodes: [],
  edges: [],
}

export default function WorkflowsPage() {
  const { data: session } = useSession()

  // workflow state
  const [workflow, setWorkflow] = useState<Workflow>(EMPTY_WF)
  const [savedId, setSavedId] = useState<string | null>(null)
  const [savedWorkflows, setSavedWorkflows] = useState<Workflow[]>([])
  const [showList, setShowList] = useState(false)

  // agent catalogue
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [agentSearch, setAgentSearch] = useState('')

  // canvas view
  const [pan, setPan] = useState({ x: 60, y: 60 })
  const [zoom, setZoom] = useState(1)
  const svgRef = useRef<SVGSVGElement>(null)

  // interaction
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [pendingSourceId, setPendingSourceId] = useState<string | null>(null)  // drawing edge from output port
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 })

  // drag
  const dragRef = useRef<{ nodeId: string; startX: number; startY: number; origX: number; origY: number } | null>(null)
  const panRef = useRef<{ startX: number; startY: number; origPanX: number; origPanY: number } | null>(null)

  // run
  const [runStatus, setRunStatus] = useState<RunStatus>('idle')
  const [nodeStatuses, setNodeStatuses] = useState<Record<string, NodeRunStatus>>({})
  const [runOutput, setRunOutput] = useState('')
  const [runError, setRunError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)
  const [saveMsg, setSaveMsg] = useState('')
  const abortRef = useRef<AbortController | null>(null)

  // selected agent info for inspector
  const selectedNode = workflow.nodes.find(n => n.id === selectedNodeId)
  const agentById = useMemo(() => new Map(agents.map(a => [a.id, a])), [agents])

  // Load agents
  useEffect(() => {
    api.agents.list().then(r => { if (r.success && r.data) setAgents(r.data.filter(a => !a.custom)) })
  }, [])

  // Load saved workflows list
  const loadList = useCallback(() => {
    wfFetch<Workflow[]>('/api/workflows').then(setSavedWorkflows).catch(() => setSavedWorkflows([]))
  }, [])
  useEffect(() => { loadList() }, [loadList])

  // ── Canvas coordinate conversion ──────────────────────────────────────

  const svgPoint = useCallback((clientX: number, clientY: number) => {
    const svg = svgRef.current
    if (!svg) return { x: 0, y: 0 }
    const rect = svg.getBoundingClientRect()
    return {
      x: (clientX - rect.left - pan.x) / zoom,
      y: (clientY - rect.top - pan.y) / zoom,
    }
  }, [pan.x, pan.y, zoom])

  // ── SVG mouse tracking ─────────────────────────────────────────────────

  const onSvgMouseMove = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    const pt = svgPoint(e.clientX, e.clientY)
    setMousePos(pt)

    if (dragRef.current) {
      const { nodeId, startX, startY, origX, origY } = dragRef.current
      const dx = (e.clientX - startX) / zoom
      const dy = (e.clientY - startY) / zoom
      setWorkflow(prev => ({
        ...prev,
        nodes: prev.nodes.map(n => n.id === nodeId
          ? { ...n, x: snapToGrid(origX + dx), y: snapToGrid(origY + dy) }
          : n),
      }))
    }

    if (panRef.current) {
      const dx = e.clientX - panRef.current.startX
      const dy = e.clientY - panRef.current.startY
      setPan({ x: panRef.current.origPanX + dx, y: panRef.current.origPanY + dy })
    }
  }, [svgPoint, zoom])

  const onSvgMouseUp = useCallback(() => {
    dragRef.current = null
    panRef.current = null
  }, [])

  const onSvgClick = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if ((e.target as SVGElement).tagName === 'svg' || (e.target as SVGElement).classList.contains('canvas-bg')) {
      setSelectedNodeId(null)
      setPendingSourceId(null)
    }
  }, [])

  const onSvgMouseDown = useCallback((e: React.MouseEvent<SVGSVGElement>) => {
    if ((e.target as SVGElement).tagName === 'svg' || (e.target as SVGElement).classList.contains('canvas-bg')) {
      panRef.current = { startX: e.clientX, startY: e.clientY, origPanX: pan.x, origPanY: pan.y }
    }
  }, [pan])

  const onWheel = useCallback((e: React.WheelEvent<SVGSVGElement>) => {
    e.preventDefault()
    setZoom(z => Math.min(2, Math.max(0.35, z - e.deltaY * 0.001)))
  }, [])

  // ── Node drag ─────────────────────────────────────────────────────────

  function startNodeDrag(nodeId: string, e: PointerEvent<HTMLDivElement>) {
    e.stopPropagation()
    const node = workflow.nodes.find(n => n.id === nodeId)
    if (!node) return
    dragRef.current = { nodeId, startX: e.clientX, startY: e.clientY, origX: node.x, origY: node.y }
  }

  // ── Edge drawing ───────────────────────────────────────────────────────

  function onOutputPortClick(nodeId: string, e: React.MouseEvent) {
    e.stopPropagation()
    setPendingSourceId(nodeId)
  }

  function onInputPortClick(nodeId: string, e: React.MouseEvent) {
    e.stopPropagation()
    if (!pendingSourceId || pendingSourceId === nodeId) { setPendingSourceId(null); return }
    // Avoid duplicates
    const exists = workflow.edges.some(edge => edge.source === pendingSourceId && edge.target === nodeId)
    if (wouldCreateCycle(workflow.nodes, workflow.edges, pendingSourceId, nodeId)) {
      setRunError('That connection would create a cycle. Workflows must remain acyclic.')
    } else if (!exists) {
      const newEdge: WFEdge = { id: `e_${Date.now()}`, source: pendingSourceId, target: nodeId }
      setWorkflow(prev => ({ ...prev, edges: [...prev.edges, newEdge] }))
    }
    setPendingSourceId(null)
  }

  function deleteEdge(edgeId: string) {
    setWorkflow(prev => ({ ...prev, edges: prev.edges.filter(e => e.id !== edgeId) }))
  }

  // ── Node add / delete ──────────────────────────────────────────────────

  function addNode(agent: AgentInfo) {
    const id = `n_${Date.now()}`
    // Stagger new nodes so they don't overlap
    const count = workflow.nodes.length
    const newNode: WFNode = {
      id,
      agentId: agent.id,
      label: agent.name,
      x: snapToGrid(100 + (count % 4) * 220),
      y: snapToGrid(80 + Math.floor(count / 4) * 160),
    }
    setWorkflow(prev => ({ ...prev, nodes: [...prev.nodes, newNode] }))
    setSelectedNodeId(id)
  }

  function deleteNode(nodeId: string, e?: { stopPropagation: () => void }) {
    e?.stopPropagation()
    setWorkflow(prev => ({
      ...prev,
      nodes: prev.nodes.filter(n => n.id !== nodeId),
      edges: prev.edges.filter(e => e.source !== nodeId && e.target !== nodeId),
    }))
    if (selectedNodeId === nodeId) setSelectedNodeId(null)
  }

  // ── Save ───────────────────────────────────────────────────────────────

  const persistWorkflow = useCallback(async (): Promise<string | null> => {
    setSaving(true)
    setSaveMsg('')
    try {
      const payload = {
        name: workflow.name,
        description: workflow.description,
        prompt: workflow.prompt,
        nodes: workflow.nodes,
        edges: workflow.edges,
      }
      let result: Workflow & { id?: string }
      if (savedId) {
        result = await wfFetch<Workflow & { id?: string }>(`/api/workflows/${savedId}`, { method: 'PUT', body: JSON.stringify(payload) })
      } else {
        result = await wfFetch<Workflow & { id?: string }>('/api/workflows', { method: 'POST', body: JSON.stringify(payload) })
      }
      const nextId = result.id || savedId || null
      if (nextId && nextId !== savedId) setSavedId(nextId)
      setSaveMsg('Saved ✓')
      loadList()
      return nextId
    } catch (error) {
      setSaveMsg('Save failed')
      setRunError(error instanceof Error ? error.message : 'Save failed')
      return null
    } finally {
      setSaving(false)
      setTimeout(() => setSaveMsg(''), 2000)
    }
  }, [workflow, savedId, loadList])

  const saveWorkflow = useCallback(async () => {
    await persistWorkflow()
  }, [persistWorkflow])

  // ── Run ────────────────────────────────────────────────────────────────

  const runWorkflow = useCallback(async () => {
    if (workflow.nodes.length === 0) return
    const workflowId = await persistWorkflow()
    if (!workflowId) return
    setRunStatus('running')
    setRunOutput('')
    setRunError(null)
    setNodeStatuses({})
    const controller = new AbortController()
    abortRef.current = controller

    const token = getToken()
    const headers: Record<string, string> = { 'Content-Type': 'application/json' }
    if (token) headers.Authorization = `Bearer ${token}`
    const googleAccessToken = (session as { accessToken?: string } | null)?.accessToken
    if (googleAccessToken) headers['X-Google-Access-Token'] = googleAccessToken

    try {
      const res = await fetch(`${BACKEND_URL}/api/workflows/${workflowId}/run`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ prompt: workflow.prompt }),
        signal: controller.signal,
      })
      if (!res.ok) {
        const payload = await res.json().catch(() => null)
        throw new Error(payload?.error || payload?.detail || `Execution failed (${res.status})`)
      }
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      if (!reader) throw new Error('No response body')

      let buffer = ''
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        buffer += decoder.decode(value, { stream: true })
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        for (const line of lines) {
          if (!line.startsWith('data: ')) continue
          try {
            const evt = JSON.parse(line.slice(6))
            if (evt.event === 'node_start') {
              setNodeStatuses(prev => ({ ...prev, [evt.nodeId]: 'running' }))
            } else if (evt.event === 'node_complete') {
              setNodeStatuses(prev => ({ ...prev, [evt.nodeId]: 'complete' }))
              setRunOutput(evt.output ?? '')
            } else if (evt.event === 'node_error') {
              setNodeStatuses(prev => ({ ...prev, [evt.nodeId]: 'error' }))
              setRunError(evt.error || 'A workflow stage failed')
            } else if (evt.event === 'complete') {
              setRunOutput(evt.output ?? '')
              setRunStatus(evt.status === 'error' ? 'error' : 'complete')
            }
          } catch { /* ignore partial JSON */ }
        }
      }
    } catch (err) {
      if (controller.signal.aborted) {
        setRunStatus('idle')
      } else {
        setRunError(err instanceof Error ? err.message : 'Execution failed')
        setRunStatus('error')
      }
    } finally {
      if (abortRef.current === controller) abortRef.current = null
    }
  }, [persistWorkflow, session, workflow])

  const stopRun = useCallback(() => {
    abortRef.current?.abort()
    setRunStatus('idle')
  }, [])

  // ── Load saved workflow ────────────────────────────────────────────────

  function loadWorkflow(wf: Workflow & { id?: string }) {
    setWorkflow({ name: wf.name, description: wf.description, prompt: wf.prompt, nodes: wf.nodes, edges: wf.edges })
    setSavedId(wf.id ?? null)
    setShowList(false)
    setRunStatus('idle')
    setRunOutput('')
    setNodeStatuses({})
    setSelectedNodeId(null)
  }

  function newWorkflow() {
    setWorkflow(EMPTY_WF)
    setSavedId(null)
    setRunStatus('idle')
    setRunOutput('')
    setNodeStatuses({})
    setSelectedNodeId(null)
  }

  // ── Filtered agent list ─────────────────────────────────────────────────

  const filteredAgents = useMemo(() => {
    const q = agentSearch.trim().toLowerCase()
    return agents.filter(a => !q || `${a.name} ${a.description}`.toLowerCase().includes(q))
  }, [agents, agentSearch])

  // ── Render ─────────────────────────────────────────────────────────────

  const selectedAgent = selectedNode ? agentById.get(selectedNode.agentId) : undefined

  return (
    <div className="flex h-full min-h-[680px] flex-col overflow-hidden bg-[#f7f7f4] text-[#26251e]">
      {/* ── Top Toolbar ──────────────────────────────────────────────── */}
      <header className="z-20 flex shrink-0 items-center gap-3 overflow-x-auto border-b border-[#dcdcd6] bg-white px-3 py-2.5 sm:px-5 scrollbar-thin">
        <div className="flex items-center gap-2 mr-2">
          <Workflow className="w-4 h-4 text-[#1877a8]" />
          <span className="font-mono text-[10px] font-bold uppercase text-[#1877a8] tracking-widest">Workflow Studio</span>
        </div>

        <input
          value={workflow.name}
          onChange={e => setWorkflow(prev => ({ ...prev, name: e.target.value }))}
          className="h-8 bg-transparent text-sm font-semibold border-0 outline-none focus:bg-[#f7f7f4] px-2 rounded w-52"
          placeholder="Workflow name"
        />

        <div className="h-5 w-px bg-[#e5e5df]" />

        <button
          onClick={() => { setShowList(v => !v); loadList() }}
          className="flex items-center gap-1.5 h-8 px-3 text-xs text-[#6c6a64] border border-[#d8d8d2] rounded hover:border-[#aaa9a1] hover:bg-[#f7f7f4] transition-colors"
        >
          <FilePlus2 className="w-3.5 h-3.5" /> Saved
        </button>

        <button
          onClick={newWorkflow}
          className="flex items-center gap-1.5 h-8 px-3 text-xs text-[#6c6a64] border border-[#d8d8d2] rounded hover:border-[#aaa9a1] hover:bg-[#f7f7f4] transition-colors"
        >
          <RotateCcw className="w-3.5 h-3.5" /> New
        </button>

        <button
          onClick={saveWorkflow}
          disabled={saving}
          className="flex items-center gap-1.5 h-8 px-3 text-xs border border-[#d8d8d2] rounded hover:border-[#aaa9a1] hover:bg-[#f7f7f4] transition-colors disabled:opacity-50"
        >
          {saving ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Save className="w-3.5 h-3.5" />}
          {saveMsg || 'Save'}
        </button>

        <div className="ml-auto flex items-center gap-2">
          {/* Zoom */}
          <button onClick={() => setZoom(z => Math.min(2, z + 0.1))} className="w-7 h-7 flex items-center justify-center border border-[#d8d8d2] rounded hover:bg-[#f7f7f4] transition-colors">
            <ZoomIn className="w-3.5 h-3.5" />
          </button>
          <span className="font-mono text-[10px] text-[#77756e] w-10 text-center">{Math.round(zoom * 100)}%</span>
          <button onClick={() => setZoom(z => Math.max(0.35, z - 0.1))} className="w-7 h-7 flex items-center justify-center border border-[#d8d8d2] rounded hover:bg-[#f7f7f4] transition-colors">
            <ZoomOut className="w-3.5 h-3.5" />
          </button>

          <div className="h-5 w-px bg-[#e5e5df]" />

          {runStatus === 'running' ? (
            <button onClick={stopRun} className="flex items-center gap-1.5 h-8 px-4 text-xs bg-red-100 text-red-700 border border-red-200 rounded font-medium hover:bg-red-200 transition-colors">
              <CircleStop className="w-3.5 h-3.5" /> Stop
            </button>
          ) : (
            <button
              onClick={runWorkflow}
              disabled={workflow.nodes.length === 0}
              className="flex items-center gap-1.5 h-8 px-4 text-xs bg-[#f54e00] text-white rounded font-medium hover:bg-[#d94300] transition-colors disabled:opacity-40"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              {savedId ? 'Run' : 'Save & Run'}
            </button>
          )}
        </div>
      </header>

      {/* ── Main layout ───────────────────────────────────────────────── */}
      <div className="flex flex-1 min-h-0 overflow-hidden">
        {/* ── Agent Palette ──────────────────────────────────────────── */}
        <aside className="z-10 flex w-40 shrink-0 flex-col overflow-hidden border-r border-[#d8d8d2] bg-[#fbfbf8] sm:w-52">
          <div className="p-3 border-b border-[#e5e5df]">
            <p className="font-mono text-[9px] font-bold uppercase tracking-widest text-[#77756e] mb-2">Agent Library</p>
            <div className="relative">
              <Search className="absolute left-2 top-2 w-3 h-3 text-[#898780]" />
              <input
                value={agentSearch}
                onChange={e => setAgentSearch(e.target.value)}
                placeholder="Search…"
                className="w-full h-7 bg-white border border-[#d8d8d2] rounded pl-6 pr-2 text-xs outline-none focus:border-[#1877a8] transition-colors"
              />
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            {filteredAgents.map((agent, i) => (
              <button
                key={agent.id}
                onClick={() => addNode(agent)}
                className="group w-full flex items-center gap-2 px-3 py-2 border-b border-[#ecece7] text-left hover:bg-white transition-colors"
              >
                <span className="w-7 h-7 shrink-0 flex items-center justify-center border border-[#deded8] bg-white" style={{ color: ACCENT_COLORS[i % ACCENT_COLORS.length] }}>
                  <AgentIcon iconName={agent.icon} className="w-3.5 h-3.5" />
                </span>
                <span className="min-w-0 flex-1">
                  <span className="block text-[11px] font-semibold truncate">{agent.name.replace(' Agent', '')}</span>
                  <span className="block text-[9px] text-[#77756e] truncate">{agent.capabilities?.[0]?.replaceAll('_', ' ')}</span>
                </span>
                <Plus className="w-3 h-3 shrink-0 text-[#aaa9a1] group-hover:text-[#f54e00] transition-colors" />
              </button>
            ))}
          </div>
          <div className="p-3 border-t border-[#e5e5df]">
            <p className="text-[9px] text-[#aaa9a1] leading-4">Click to add a node. Drag output → input port to connect. Click an edge to delete it.</p>
          </div>
        </aside>

        {/* ── SVG Canvas ─────────────────────────────────────────────── */}
        <main className="flex-1 relative overflow-hidden bg-[#f8faf9]">
          <svg
            ref={svgRef}
            className="absolute inset-0 w-full h-full"
            style={{ cursor: panRef.current ? 'grabbing' : pendingSourceId ? 'crosshair' : 'default' }}
            onMouseMove={onSvgMouseMove}
            onMouseUp={onSvgMouseUp}
            onMouseLeave={onSvgMouseUp}
            onClick={onSvgClick}
            onMouseDown={onSvgMouseDown}
            onWheel={onWheel}
          >
            {/* Grid background */}
            <defs>
              <pattern id="grid" width={GRID_SIZE * zoom} height={GRID_SIZE * zoom} patternUnits="userSpaceOnUse"
                x={pan.x % (GRID_SIZE * zoom)} y={pan.y % (GRID_SIZE * zoom)}>
                <path d={`M ${GRID_SIZE * zoom} 0 L 0 0 0 ${GRID_SIZE * zoom}`}
                  fill="none" stroke="#dfe5e2" strokeWidth="0.8" />
              </pattern>
            </defs>
            <rect className="canvas-bg" width="100%" height="100%" fill="url(#grid)" />

            {/* Status badge */}
            <g>
              <rect x="12" y="12" width="112" height="20" rx="3" fill="white" stroke="#d8d8d2" />
              <circle cx="25" cy="22" r="4" fill={runStatus === 'running' ? '#1f8a65' : '#d8d8d2'}>
                {runStatus === 'running' && <animate attributeName="r" values="3;5;3" dur="1.2s" repeatCount="indefinite" />}
              </circle>
              <text x="35" y="27" fontFamily="monospace" fontSize="8" fill="#77756e" fontWeight="bold">
                {runStatus === 'running' ? 'RUNNING' : runStatus === 'complete' ? 'COMPLETE' : runStatus === 'error' ? 'ERROR' : 'READY'}
              </text>
            </g>

            <g transform={`translate(${pan.x},${pan.y}) scale(${zoom})`}>

              {/* Edges */}
              {workflow.edges.map(edge => {
                const src = workflow.nodes.find(n => n.id === edge.source)
                const tgt = workflow.nodes.find(n => n.id === edge.target)
                if (!src || !tgt) return null
                return (
                  <path
                    key={edge.id}
                    d={edgePath(src, tgt)}
                    fill="none"
                    stroke="#aaa9a1"
                    strokeWidth="1.5"
                    strokeDasharray="none"
                    className="cursor-pointer hover:stroke-[#cf2d56] transition-colors"
                    onClick={(e) => { e.stopPropagation(); deleteEdge(edge.id) }}
                  />
                )
              })}

              {/* Animated edge in progress */}
              {pendingSourceId && (() => {
                const src = workflow.nodes.find(n => n.id === pendingSourceId)
                if (!src) return null
                const sp = outPortXY(src)
                return (
                  <path
                    d={pendingEdgePath(sp.x, sp.y, mousePos.x, mousePos.y)}
                    fill="none"
                    stroke="#f54e00"
                    strokeWidth="1.5"
                    strokeDasharray="6 4"
                    pointerEvents="none"
                  />
                )
              })()}

              {/* Nodes */}
              {workflow.nodes.map((node, idx) => (
                <DAGNode
                  key={node.id}
                  node={node}
                  agentInfo={agentById.get(node.agentId)}
                  accentIndex={idx}
                  selected={selectedNodeId === node.id}
                  runStatus={nodeStatuses[node.id] ?? 'idle'}
                  pendingSource={pendingSourceId === node.id}
                  onPointerDown={e => startNodeDrag(node.id, e)}
                  onClick={() => setSelectedNodeId(node.id)}
                  onOutputPortClick={e => onOutputPortClick(node.id, e)}
                  onInputPortClick={e => onInputPortClick(node.id, e)}
                  onDelete={e => deleteNode(node.id, e)}
                />
              ))}

              {/* Empty state */}
              {workflow.nodes.length === 0 && (
                <foreignObject x="50%" y="50%" width="260" height="120" style={{ transform: 'translate(-130px, -60px)' }}>
                  <div className="w-full h-full flex flex-col items-center justify-center border border-dashed border-[#aeb8b2] bg-white/80 rounded">
                    <Workflow className="w-7 h-7 text-[#aaa9a1] mb-2" />
                    <p className="text-sm font-medium text-[#6c6a64]">Add an agent from the panel</p>
                    <p className="text-[10px] text-[#aaa9a1] mt-1">Connect output → input ports to chain them</p>
                  </div>
                </foreignObject>
              )}
            </g>
          </svg>

          {/* Node count badge */}
          <div className="absolute bottom-3 left-3 font-mono text-[9px] uppercase text-[#77756e] bg-white/80 border border-[#d8d8d2] px-2.5 py-1 rounded">
            {workflow.nodes.length} nodes · {workflow.edges.length} edges
          </div>
        </main>

        {/* ── Inspector + Prompt ─────────────────────────────────────── */}
        <aside className="z-10 hidden w-64 shrink-0 flex-col overflow-hidden border-l border-[#d8d8d2] bg-white xl:flex">
          <div className="px-4 py-3 border-b border-[#e5e5df]">
            <p className="font-mono text-[9px] font-bold uppercase tracking-widest text-[#77756e]">Inspector</p>
          </div>

          {/* Node inspector */}
          {selectedAgent && selectedNode ? (
            <div className="p-4 border-b border-[#e5e5df]">
              <div className="flex items-center gap-2.5 mb-3">
                <span className="w-8 h-8 flex items-center justify-center border border-[#deded8] bg-[#f7f7f4] text-[#f54e00]">
                  <AgentIcon iconName={selectedAgent.icon} className="w-4 h-4" />
                </span>
                <div>
                  <p className="text-xs font-semibold">{selectedAgent.name}</p>
                  <p className="font-mono text-[9px] uppercase text-[#77756e]">Node {selectedNode.id.slice(-4)}</p>
                </div>
              </div>
              <p className="text-[11px] text-[#65635d] leading-4">{selectedAgent.description}</p>
              <div className="mt-3 flex flex-wrap gap-1">
                {(selectedAgent.capabilities ?? []).slice(0, 4).map(cap => (
                  <span key={cap} className="text-[9px] bg-[#f7f7f4] border border-[#deded8] px-1.5 py-0.5 text-[#65635d]">
                    {cap.replaceAll('_', ' ')}
                  </span>
                ))}
              </div>
              <button
                onClick={() => deleteNode(selectedNode.id)}
                className="mt-3 flex items-center gap-1.5 text-[11px] text-[#b53d3d] hover:text-[#8e2727] transition-colors"
              >
                <Trash2 className="w-3 h-3" /> Remove node
              </button>
            </div>
          ) : (
            <p className="px-4 py-3 text-[11px] text-[#77756e] border-b border-[#e5e5df]">Select a node to inspect it.</p>
          )}

          {/* Prompt */}
          <div className="p-4 flex flex-col gap-2 border-b border-[#e5e5df]">
            <label className="font-mono text-[9px] font-bold uppercase tracking-widest text-[#77756e]">Run Prompt</label>
            <textarea
              value={workflow.prompt}
              onChange={e => setWorkflow(prev => ({ ...prev, prompt: e.target.value }))}
              className="w-full text-xs leading-5 border border-[#d8d8d2] rounded resize-none p-2 focus:border-[#1877a8] outline-none min-h-[90px] bg-[#fbfbf8]"
              placeholder="The initial prompt fed into the first agent…"
            />
            <p className="text-[9px] text-[#aaa9a1] flex items-center gap-1">
              <ChevronRight className="w-3 h-3" /> Output of each node feeds the next
            </p>
          </div>

          {/* Description */}
          <div className="p-4 flex-1">
            <label className="font-mono text-[9px] font-bold uppercase tracking-widest text-[#77756e] block mb-1.5">Description</label>
            <input
              value={workflow.description}
              onChange={e => setWorkflow(prev => ({ ...prev, description: e.target.value }))}
              className="w-full text-xs border border-[#d8d8d2] rounded px-2 py-1.5 focus:border-[#1877a8] outline-none bg-[#fbfbf8]"
              placeholder="Optional notes…"
            />
          </div>
        </aside>
      </div>

      {/* ── Output panel ───────────────────────────────────────────────── */}
      {(runOutput || runError) && (
        <div className="shrink-0 border-t border-[#d8d8d2] bg-white" style={{ maxHeight: '240px' }}>
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-[#e5e5df]">
            <div className="flex items-center gap-2">
              {runStatus === 'complete' && <Check className="w-4 h-4 text-[#1f8a65]" />}
              {runStatus === 'error' && <AlertCircle className="w-4 h-4 text-[#cf2d56]" />}
              <h2 className="text-sm font-semibold">{runStatus === 'error' ? 'Run Error' : 'Run Output'}</h2>
            </div>
            <button onClick={() => { setRunOutput(''); setRunError(null) }} className="text-[#aaa9a1] hover:text-[#26251e] transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>
          <pre className="overflow-auto p-4 text-xs leading-5 text-[#3f3e39] font-sans whitespace-pre-wrap scrollbar-thin" style={{ maxHeight: '180px' }}>
            {runError || runOutput}
          </pre>
        </div>
      )}

      {/* ── Saved workflows list modal ──────────────────────────────────── */}
      {showList && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30 backdrop-blur-sm" onClick={() => setShowList(false)}>
          <div className="bg-white border border-[#d8d8d2] rounded-lg shadow-2xl w-[480px] max-h-[60vh] flex flex-col" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#e5e5df]">
              <h3 className="font-semibold text-sm">Saved Workflows</h3>
              <button onClick={() => setShowList(false)} className="text-[#aaa9a1] hover:text-[#26251e]"><X className="w-4 h-4" /></button>
            </div>
            <div className="flex-1 overflow-y-auto divide-y divide-[#f0f0ea]">
              {savedWorkflows.length === 0 && <p className="p-5 text-sm text-[#77756e]">No saved workflows yet.</p>}
              {savedWorkflows.map((wf) => (
                <div key={(wf as Workflow & { id?: string }).id} className="flex items-center gap-3 px-5 py-3 hover:bg-[#fbfbf8] transition-colors">
                  <Workflow className="w-4 h-4 text-[#1877a8] shrink-0" />
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{wf.name}</p>
                    <p className="text-[10px] text-[#77756e]">{(wf as Workflow & { nodes?: WFNode[] }).nodes?.length ?? 0} nodes · {wf.description?.slice(0, 40) || 'No description'}</p>
                  </div>
                  <button
                    onClick={() => loadWorkflow(wf as Workflow & { id?: string })}
                    className="text-xs text-[#1877a8] hover:text-[#0f4d6e] font-medium transition-colors"
                  >
                    Open
                  </button>
                  <button
                    onClick={async () => {
                      const id = (wf as Workflow & { id?: string }).id
                      if (id) { await wfFetch(`/api/workflows/${id}`, { method: 'DELETE' }); loadList() }
                    }}
                    className="text-[#aaa9a1] hover:text-[#cf2d56] transition-colors"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
