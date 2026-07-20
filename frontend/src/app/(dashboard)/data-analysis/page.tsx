'use client'

import React, { useState, useCallback, useRef, useEffect } from 'react'
import {
  Upload, BarChart2, FileSpreadsheet, Send, Trash2, ChevronDown,
  ChevronUp, Sparkles, Table2, TrendingUp, AlertCircle, Plus,
} from 'lucide-react'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

function getToken() {
  try {
    return typeof window !== 'undefined' ? localStorage.getItem('access_token') : null
  } catch {
    return null
  }
}

async function apiFetch(endpoint: string, opts: RequestInit = {}) {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (!(opts.body instanceof FormData)) headers['Content-Type'] = 'application/json'
  const res = await fetch(`${BACKEND_URL}${endpoint}`, { ...opts, headers: { ...headers, ...(opts.headers as Record<string, string> | undefined) } })
  return res.json()
}

interface ColumnStat {
  count: number
  nulls: number
  numeric: boolean
  min?: number
  max?: number
  mean?: number
  sum?: number
}

interface SessionInfo {
  session_id: string
  filename: string
  row_count: number
  column_count: number
  headers: string[]
  preview: string[][]
  stats: Record<string, ColumnStat>
}

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: Date
}

interface ChartData {
  type: 'bar' | 'line' | 'pie' | 'scatter'
  title: string
  labels: string[]
  datasets: Array<{ label: string; data: number[] }>
}

function parseChartBlocks(content: string): { text: string; charts: ChartData[] } {
  const charts: ChartData[] = []
  const text = content.replace(/```chart\n([\s\S]*?)```/g, (_, json) => {
    try { charts.push(JSON.parse(json.trim())) } catch { /* ignore */ }
    return `[[chart-${charts.length}]]`
  })
  return { text, charts }
}

const CHART_COLORS = ['#2dd4bf', '#a78bfa', '#fb923c', '#f472b6', '#34d399', '#60a5fa', '#fbbf24', '#f87171']

function MiniChart({ chart }: { chart: ChartData }) {
  const W = 460, H = 200, PAD = 36

  if (chart.type === 'pie') {
    const data = chart.datasets[0]?.data ?? []
    const total = data.reduce((a, b) => a + b, 0)
    if (!total) return null
    let angle = -Math.PI / 2
    const cx = W / 2, cy = H / 2, r = Math.min(W, H) / 2 - 20
    return (
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
        {data.map((val, i) => {
          const sweep = (val / total) * 2 * Math.PI
          const x1 = cx + r * Math.cos(angle), y1 = cy + r * Math.sin(angle)
          angle += sweep
          const x2 = cx + r * Math.cos(angle), y2 = cy + r * Math.sin(angle)
          const large = sweep > Math.PI ? 1 : 0
          const midA = angle - sweep / 2
          const lx = cx + r * 0.65 * Math.cos(midA), ly = cy + r * 0.65 * Math.sin(midA)
          return (
            <g key={i}>
              <path d={`M${cx},${cy} L${x1},${y1} A${r},${r} 0 ${large},1 ${x2},${y2} Z`}
                fill={CHART_COLORS[i % CHART_COLORS.length]} stroke="#0d0d1a" strokeWidth="2" />
              {val / total > 0.05 && <text x={lx} y={ly} textAnchor="middle" dominantBaseline="middle" fontSize="9" fill="#fff">{chart.labels?.[i]?.slice(0, 8)}</text>}
            </g>
          )
        })}
      </svg>
    )
  }

  const dataset = chart.datasets[0]
  if (!dataset) return null
  const vals = dataset.data
  const maxV = Math.max(...vals, 0.001), minV = Math.min(...vals, 0)
  const range = maxV - minV || 1
  const colW = (W - PAD * 2) / (vals.length || 1)
  const toY = (v: number) => PAD + ((maxV - v) / range) * (H - PAD * 2)

  if (chart.type === 'line' || chart.type === 'scatter') {
    const pts = vals.map((v, i) => `${PAD + i * colW + colW / 2},${toY(v)}`).join(' ')
    return (
      <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
        <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#334155" strokeWidth="1" />
        <polyline points={pts} fill="none" stroke={CHART_COLORS[0]} strokeWidth="2.5" strokeLinejoin="round" />
        {vals.map((v, i) => (
          <circle key={i} cx={PAD + i * colW + colW / 2} cy={toY(v)} r="4" fill={CHART_COLORS[0]} />
        ))}
        {chart.labels?.map((l, i) => (
          <text key={i} x={PAD + i * colW + colW / 2} y={H - PAD + 14} textAnchor="middle" fontSize="9" fill="#64748b">{l.slice(0, 8)}</text>
        ))}
      </svg>
    )
  }

  // Bar chart (default)
  const bw = colW * 0.72
  return (
    <svg width={W} height={H} viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
      <line x1={PAD} y1={H - PAD} x2={W - PAD} y2={H - PAD} stroke="#334155" strokeWidth="1" />
      {vals.map((v, i) => {
        const bh = Math.abs(toY(v) - toY(0))
        const by = Math.min(toY(v), toY(0))
        return (
          <g key={i}>
            <rect x={PAD + i * colW + (colW - bw) / 2} y={by} width={bw} height={bh}
              fill={CHART_COLORS[i % CHART_COLORS.length]} rx="3" opacity="0.88" />
            <text x={PAD + i * colW + colW / 2} y={by - 3} textAnchor="middle" fontSize="9" fill="#e2e8f0">{v}</text>
          </g>
        )
      })}
      {chart.labels?.map((l, i) => (
        <text key={i} x={PAD + i * colW + colW / 2} y={H - PAD + 14} textAnchor="middle" fontSize="9" fill="#64748b">{l.slice(0, 10)}</text>
      ))}
    </svg>
  )
}

function MarkdownRenderer({ text }: { text: string }) {
  const lines = text.split('\n')
  const elements: React.ReactNode[] = []
  let i = 0
  while (i < lines.length) {
    const line = lines[i]
    // Markdown table
    if (line.trim().startsWith('|') && lines[i + 1]?.trim().startsWith('|---')) {
      const headers = line.split('|').filter(Boolean).map(h => h.trim())
      const rows: string[][] = []
      i += 2
      while (i < lines.length && lines[i].trim().startsWith('|')) {
        rows.push(lines[i].split('|').filter(Boolean).map(c => c.trim()))
        i++
      }
      elements.push(
        <div key={`t${i}`} className="overflow-auto my-3 rounded-lg border border-slate-700">
          <table className="min-w-full text-xs">
            <thead><tr className="bg-slate-800">{headers.map((h, j) => <th key={j} className="px-3 py-2 text-left text-teal-400 font-semibold whitespace-nowrap">{h}</th>)}</tr></thead>
            <tbody>{rows.map((row, ri) => (
              <tr key={ri} className={ri % 2 === 0 ? 'bg-slate-900' : 'bg-slate-800/40'}>
                {row.map((c, ci) => <td key={ci} className="px-3 py-1.5 text-slate-300 whitespace-nowrap">{c}</td>)}
              </tr>
            ))}</tbody>
          </table>
        </div>
      )
    } else {
      const inline = line
        .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>')
        .replace(/`(.+?)`/g, '<code class="bg-slate-800 px-1 rounded text-teal-300 text-xs font-mono">$1</code>')
        .replace(/^### (.+)/, '<h3 class="text-sm font-bold text-white mt-3 mb-0.5">$1</h3>')
        .replace(/^## (.+)/, '<h2 class="text-base font-bold text-white mt-4 mb-1">$1</h2>')
        .replace(/^# (.+)/, '<h1 class="text-lg font-bold text-white mt-4 mb-2">$1</h1>')
        .replace(/^[-*] (.+)/, '<li class="ml-4 list-disc text-slate-300 text-sm">$1</li>')
      elements.push(
        <p key={`l${i}`} className="text-slate-300 text-sm leading-relaxed"
          dangerouslySetInnerHTML={{ __html: inline || '\u00a0' }} />
      )
      i++
    }
  }
  return <>{elements}</>
}

const QUICK_QUESTIONS = [
  '📊 Show a statistical summary of all columns',
  '📈 What are the top 5 highest values?',
  '🔗 Show correlations between numeric columns',
  '📉 Identify any outliers in the data',
  '🧁 Create a pie chart of the first categorical column',
  '📊 Generate a bar chart of the top 10 rows',
]

export default function DataAnalysisPage() {
  const [session, setSession] = useState<SessionInfo | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [question, setQuestion] = useState('')
  const [uploading, setUploading] = useState(false)
  const [analysing, setAnalysing] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [showPreview, setShowPreview] = useState(true)
  const [showStats, setShowStats] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const chatEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, analysing])

  const handleFile = useCallback(async (file: File) => {
    setError(null)
    setUploading(true)
    try {
      const fd = new FormData()
      fd.append('file', file)
      fd.append('user_id', 'default')
      const token = getToken()
      const res = await fetch(`${BACKEND_URL}/api/data-analysis/upload`, {
        method: 'POST',
        body: fd,
        headers: token ? { Authorization: `Bearer ${token}` } : {},
      })
      const data = await res.json()
      if (!data.success) throw new Error(data.detail || data.error || 'Upload failed')
      setSession(data)
      setMessages([{
        id: 'welcome',
        role: 'assistant',
        content: `✅ **${data.filename}** loaded successfully!\n\n📊 **${data.row_count.toLocaleString()} rows** × **${data.column_count} columns**\n\nColumns: ${data.headers.slice(0, 6).map((h: string) => `\`${h}\``).join(', ')}${data.headers.length > 6 ? `, +${data.headers.length - 6} more` : ''}\n\nAsk me anything — statistical summaries, trends, correlations, outliers, or ask for a chart!`,
        timestamp: new Date(),
      }])
    } catch (e: unknown) {
      setError((e as Error).message || 'Failed to upload file')
    } finally {
      setUploading(false)
    }
  }, [])

  const onDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file) handleFile(file)
  }, [handleFile])

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) handleFile(file)
    e.target.value = ''
  }

  const sendQuestion = async () => {
    if (!question.trim() || !session || analysing) return
    const userMsg: Message = { id: Date.now().toString(), role: 'user', content: question.trim(), timestamp: new Date() }
    setMessages(prev => [...prev, userMsg])
    const q = question.trim()
    setQuestion('')
    setAnalysing(true)
    try {
      const res = await apiFetch('/api/data-analysis/analyse', {
        method: 'POST',
        body: JSON.stringify({ session_id: session.session_id, question: q, user_id: 'default' }),
      })
      if (!res.success) throw new Error(res.detail || res.error || 'Analysis failed')
      setMessages(prev => [...prev, { id: Date.now().toString() + 'a', role: 'assistant', content: res.answer, timestamp: new Date() }])
    } catch (e: unknown) {
      setMessages(prev => [...prev, { id: Date.now().toString() + 'e', role: 'assistant', content: `❌ Error: ${(e as Error).message}`, timestamp: new Date() }])
    } finally {
      setAnalysing(false)
    }
  }

  const clearSession = () => {
    if (session) apiFetch(`/api/data-analysis/session/${session.session_id}`, { method: 'DELETE' }).catch(() => {})
    setSession(null)
    setMessages([])
    setQuestion('')
    setError(null)
  }

  return (
    <div className="min-h-screen bg-[#0d0d1a] text-white flex flex-col">
      {/* ── Header ─────────────────────────────────────────── */}
      <div className="border-b border-slate-800 bg-[#0d0d1a]/90 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center shadow-lg shadow-teal-500/25">
              <BarChart2 className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Data Analysis Agent</h1>
              <p className="text-xs text-slate-400">Upload CSV / Excel · AI-powered charts & insights</p>
            </div>
          </div>
          {session && (
            <div className="ml-auto flex items-center gap-3">
              <div className="flex items-center gap-2 bg-slate-800/70 border border-slate-700 rounded-lg px-3 py-1.5">
                <FileSpreadsheet className="w-4 h-4 text-teal-400 shrink-0" />
                <span className="text-sm text-slate-300 truncate max-w-[200px]">{session.filename}</span>
                <span className="text-xs text-slate-500 shrink-0">{session.row_count.toLocaleString()} rows</span>
              </div>
              <button
                onClick={clearSession}
                className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-red-400 px-2.5 py-1.5 rounded-lg hover:bg-red-500/10 transition-colors"
              >
                <Trash2 className="w-4 h-4" /> Clear
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6 w-full flex-1">
        {/* ── Upload Zone ─────────────────────────────────── */}
        {!session && (
          <div className="flex flex-col items-center justify-center gap-8" style={{ minHeight: 'calc(100vh - 160px)' }}>
            <div
              className={`w-full max-w-2xl border-2 border-dashed rounded-2xl p-16 text-center cursor-pointer transition-all duration-200 ${
                dragOver
                  ? 'border-teal-400 bg-teal-500/10 scale-[1.02]'
                  : 'border-slate-700 bg-slate-900/40 hover:border-slate-500 hover:bg-slate-800/30'
              }`}
              onDragOver={e => { e.preventDefault(); setDragOver(true) }}
              onDragLeave={() => setDragOver(false)}
              onDrop={onDrop}
              onClick={() => fileInputRef.current?.click()}
            >
              {uploading ? (
                <div className="flex flex-col items-center gap-4">
                  <div className="w-16 h-16 rounded-full border-4 border-teal-500 border-t-transparent animate-spin" />
                  <p className="text-slate-300 text-lg font-medium">Parsing your file…</p>
                  <p className="text-slate-500 text-sm">Extracting columns, rows and computing statistics</p>
                </div>
              ) : (
                <>
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-teal-500/20 to-emerald-500/20 border border-teal-500/30 flex items-center justify-center mx-auto mb-6">
                    <Upload className="w-10 h-10 text-teal-400" />
                  </div>
                  <h2 className="text-2xl font-bold text-white mb-2">Drop your data file here</h2>
                  <p className="text-slate-400 mb-6">
                    Supports <span className="text-teal-400 font-medium">.csv</span>,{' '}
                    <span className="text-teal-400 font-medium">.xlsx</span> and{' '}
                    <span className="text-teal-400 font-medium">.xls</span> files · up to 20 MB
                  </p>
                  <div className="inline-flex items-center gap-2 bg-teal-500 hover:bg-teal-400 text-white font-semibold px-6 py-2.5 rounded-xl transition-colors">
                    <Plus className="w-4 h-4" /> Choose File
                  </div>
                </>
              )}
              <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={onFileChange} />
            </div>

            {error && (
              <div className="w-full max-w-2xl flex items-start gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-4">
                <AlertCircle className="w-5 h-5 text-red-400 mt-0.5 shrink-0" />
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}

            <div className="w-full max-w-2xl grid grid-cols-3 gap-4">
              {[
                { icon: Table2, title: 'Smart Preview', desc: 'Instant column stats & row preview' },
                { icon: TrendingUp, title: 'AI Insights', desc: 'Trends, correlations, outliers' },
                { icon: BarChart2, title: 'Live Charts', desc: 'Bar, line, pie & scatter plots' },
              ].map(({ icon: Icon, title, desc }) => (
                <div key={title} className="bg-slate-900/50 border border-slate-800 rounded-xl p-5 text-center hover:border-slate-700 transition-colors">
                  <Icon className="w-7 h-7 text-teal-400 mx-auto mb-3" />
                  <p className="text-sm font-semibold text-white mb-1">{title}</p>
                  <p className="text-xs text-slate-500">{desc}</p>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Analysis Layout ──────────────────────────────── */}
        {session && (
          <div className="grid grid-cols-1 xl:grid-cols-5 gap-5">
            {/* Left Panel */}
            <div className="xl:col-span-2 space-y-4">
              {/* Data Preview */}
              <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden">
                <button
                  onClick={() => setShowPreview(v => !v)}
                  className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-slate-800/40 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <Table2 className="w-4 h-4 text-teal-400" />
                    <span className="font-semibold text-sm text-white">Data Preview</span>
                    <span className="text-xs text-slate-500">({session.row_count.toLocaleString()} × {session.column_count})</span>
                  </div>
                  {showPreview ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
                </button>
                {showPreview && (
                  <div className="overflow-auto border-t border-slate-800" style={{ maxHeight: '240px' }}>
                    <table className="min-w-full text-xs">
                      <thead className="sticky top-0 bg-slate-800">
                        <tr>{session.headers.map(h => <th key={h} className="px-3 py-2 text-left text-teal-400 font-semibold whitespace-nowrap">{h}</th>)}</tr>
                      </thead>
                      <tbody>
                        {session.preview.map((row, ri) => (
                          <tr key={ri} className={ri % 2 === 0 ? 'bg-slate-900' : 'bg-slate-800/30'}>
                            {row.map((cell, ci) => (
                              <td key={ci} className="px-3 py-1.5 text-slate-300 whitespace-nowrap max-w-[120px] truncate">{cell}</td>
                            ))}
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>

              {/* Column Stats */}
              <div className="bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden">
                <button
                  onClick={() => setShowStats(v => !v)}
                  className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-slate-800/40 transition-colors"
                >
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-4 h-4 text-violet-400" />
                    <span className="font-semibold text-sm text-white">Column Statistics</span>
                  </div>
                  {showStats ? <ChevronUp className="w-4 h-4 text-slate-500" /> : <ChevronDown className="w-4 h-4 text-slate-500" />}
                </button>
                {showStats && (
                  <div className="border-t border-slate-800 divide-y divide-slate-800/60 overflow-y-auto" style={{ maxHeight: '320px' }}>
                    {Object.entries(session.stats).map(([col, stat]) => (
                      <div key={col} className="px-5 py-3">
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-medium text-white truncate max-w-[150px]">{col}</span>
                          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${stat.numeric ? 'bg-teal-500/20 text-teal-400' : 'bg-violet-500/20 text-violet-400'}`}>
                            {stat.numeric ? 'numeric' : 'text'}
                          </span>
                        </div>
                        <div className="grid grid-cols-2 gap-x-4 gap-y-0.5 text-xs">
                          <span className="text-slate-500">Count: <span className="text-slate-300">{stat.count}</span></span>
                          <span className="text-slate-500">Nulls: <span className="text-slate-300">{stat.nulls}</span></span>
                          {stat.numeric && (
                            <>
                              <span className="text-slate-500">Min: <span className="text-slate-300">{stat.min}</span></span>
                              <span className="text-slate-500">Max: <span className="text-slate-300">{stat.max}</span></span>
                              <span className="text-slate-500">Mean: <span className="text-slate-300">{stat.mean}</span></span>
                              <span className="text-slate-500">Sum: <span className="text-slate-300">{stat.sum}</span></span>
                            </>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Quick Questions */}
              <div className="bg-slate-900/50 border border-slate-800 rounded-2xl p-4">
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-widest mb-3">Quick Questions</p>
                <div className="flex flex-col gap-1">
                  {QUICK_QUESTIONS.map(q => (
                    <button
                      key={q}
                      onClick={() => setQuestion(q)}
                      disabled={analysing}
                      className="text-left text-xs text-slate-400 hover:text-teal-300 hover:bg-slate-800/60 px-3 py-2 rounded-lg transition-colors disabled:opacity-50 truncate"
                    >
                      {q}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Right Panel — Chat */}
            <div className="xl:col-span-3 flex flex-col bg-slate-900/50 border border-slate-800 rounded-2xl overflow-hidden" style={{ minHeight: '620px' }}>
              <div className="flex items-center gap-2 px-5 py-3.5 border-b border-slate-800 shrink-0">
                <Sparkles className="w-4 h-4 text-yellow-400" />
                <span className="font-semibold text-sm text-white">AI Analysis Chat</span>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-5 space-y-5">
                {messages.map(msg => (
                  <div key={msg.id} className={`flex gap-2.5 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    {msg.role === 'assistant' && (
                      <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center shrink-0 mt-0.5">
                        <BarChart2 className="w-3.5 h-3.5 text-white" />
                      </div>
                    )}
                    <div className={`max-w-[88%] ${msg.role === 'user'
                      ? 'bg-teal-500/20 border border-teal-500/30 rounded-2xl rounded-tr-sm px-4 py-2.5'
                      : 'bg-slate-800/60 border border-slate-700/50 rounded-2xl rounded-tl-sm px-4 py-3'}`}
                    >
                      {msg.role === 'assistant' ? (() => {
                        const { text, charts } = parseChartBlocks(msg.content)
                        const parts = text.split(/\[\[chart-(\d+)\]\]/)
                        return (
                          <>
                            {parts.map((part, pi) => {
                              const chartIdx = parseInt(part) - 1
                              if (!isNaN(chartIdx) && charts[chartIdx]) {
                                return (
                                  <div key={pi} className="mt-3 bg-slate-900/80 border border-slate-700 rounded-xl p-4">
                                    <p className="text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-3">{charts[chartIdx].title}</p>
                                    <MiniChart chart={charts[chartIdx]} />
                                  </div>
                                )
                              }
                              return <MarkdownRenderer key={pi} text={part} />
                            })}
                          </>
                        )
                      })() : (
                        <p className="text-sm text-slate-200">{msg.content}</p>
                      )}
                      <p className="text-[10px] text-slate-600 mt-1.5 text-right">
                        {msg.timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </p>
                    </div>
                  </div>
                ))}

                {analysing && (
                  <div className="flex gap-2.5 justify-start">
                    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-teal-500 to-emerald-600 flex items-center justify-center shrink-0">
                      <BarChart2 className="w-3.5 h-3.5 text-white" />
                    </div>
                    <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl rounded-tl-sm px-5 py-4">
                      <div className="flex gap-1.5 items-center">
                        {[0, 1, 2].map(i => (
                          <div key={i} className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                        ))}
                        <span className="text-xs text-slate-500 ml-1">Analysing…</span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={chatEndRef} />
              </div>

              {/* Input */}
              <div className="px-4 py-4 border-t border-slate-800 shrink-0">
                <div className="flex items-end gap-2 bg-slate-800/60 border border-slate-700 rounded-xl p-2 focus-within:border-teal-500/50 transition-colors">
                  <textarea
                    className="flex-1 bg-transparent text-sm text-white placeholder:text-slate-500 resize-none outline-none px-2 py-1.5 min-h-[38px] max-h-[120px]"
                    placeholder="Ask about this dataset… (e.g. 'What is the average revenue?')"
                    value={question}
                    onChange={e => setQuestion(e.target.value)}
                    onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendQuestion() } }}
                    rows={1}
                    disabled={analysing}
                  />
                  <button
                    onClick={sendQuestion}
                    disabled={!question.trim() || analysing}
                    className="w-9 h-9 rounded-lg bg-teal-500 hover:bg-teal-400 disabled:bg-slate-700 disabled:cursor-not-allowed flex items-center justify-center transition-colors shrink-0"
                  >
                    <Send className="w-4 h-4 text-white" />
                  </button>
                </div>
                <p className="text-[10px] text-slate-600 mt-1.5 text-center">Enter to send · Shift+Enter for new line</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
