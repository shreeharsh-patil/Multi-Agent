'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Textarea } from '@/components/ui/textarea'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import { Download, GitBranch, Loader2, Maximize2, Minus, Plus, Sparkles, Wand2 } from 'lucide-react'

const DEFAULT_FLOWCHART = `flowchart TD
  A[Start with a question] --> B[Gather evidence]
  B --> C{Evaluate sources}
  C -->|Strong evidence| D[Synthesize findings]
  C -->|Gaps remain| B
  D --> E[Review and revise]
  E --> F[Share what you learned]`

const DEFAULT_MINDMAP = `mindmap
  root((Study topic))
    Key ideas
      Definitions
      Principles
      Examples
    Evidence
      Sources
      Data
      Counterpoints
    Apply it
      Practice
      Explain
      Review`

function normalizeMermaidSource(input: string) {
  let source = input.replace(/```mermaid\s*/gi, '').replace(/```/g, '').trim()
  source = source.replace(/^raph\b/i, 'graph')
  source = source.replace(/\s+(?=(?:where\b|\*\s+\*\*))/i, '\n')
  source = source.split(/\n\s*(?:where\b|\*\s+\*\*)/i)[0] || ''
  // Mermaid accepts semicolons, but removing terminal ones avoids parser issues
  // when a model concatenates a diagram statement with following prose.
  return source.split('\n').map((line) => line.trimEnd().replace(/;\s*$/, '')).join('\n').trim()
}

function extractMermaid(content?: string) {
  const match = content?.match(/```mermaid\s*([\s\S]*?)```/i)
  return normalizeMermaidSource(match?.[1] || '')
}

/** Repairs chat responses where prose was accidentally left inside a Mermaid fence. */
export function repairMermaidMarkdown(content: string) {
  return content.replace(/```mermaid\s*([\s\S]*?)(```|$)/gi, (full, body: string, closing: string) => {
    const marker = body.search(/\s+(?:where\b|\*\s+\*\*)/i)
    if (marker < 0) return closing ? full : `${full}\n\`\`\``

    const diagram = body.slice(0, marker).trim().replace(/^raph\b/i, 'graph')
    const trailing = `${body.slice(marker).trim()}${closing ? '' : ''}`.trim()
    return `\`\`\`mermaid\n${diagram}\n\`\`\`\n\n${trailing}`
  })
}

export function MermaidWorkspace({ content, title = 'Visual study map' }: { content?: string; title?: string }) {
  const diagramRef = useRef<HTMLDivElement>(null)
  const [code, setCode] = useState(() => extractMermaid(content) || DEFAULT_FLOWCHART)
  const [topic, setTopic] = useState('')
  const [zoom, setZoom] = useState(1)
  const [activeTab, setActiveTab] = useState<'diagram' | 'code'>('diagram')
  const [renderError, setRenderError] = useState<string | null>(null)
  const [generating, setGenerating] = useState(false)

  useEffect(() => {
    const found = extractMermaid(content)
    if (found) setCode(found)
  }, [content])

  useEffect(() => {
    let cancelled = false
    async function render() {
      if (!diagramRef.current || activeTab !== 'diagram') return
      try {
        const mermaid = (await import('mermaid')).default
        mermaid.initialize({ startOnLoad: false, securityLevel: 'strict', suppressErrorRendering: true, theme: 'base', themeVariables: {
          primaryColor: '#fff1e9', primaryTextColor: '#26251e', primaryBorderColor: '#f54e00',
          lineColor: '#8c877d', secondaryColor: '#f4f3ee', tertiaryColor: '#ffffff', fontFamily: 'system-ui'
        }})
        const id = `mermaid-${Date.now()}`
        const normalizedCode = normalizeMermaidSource(code)
        await mermaid.parse(normalizedCode)
        const { svg } = await mermaid.render(id, normalizedCode)
        if (!cancelled && diagramRef.current) {
          diagramRef.current.innerHTML = svg
          const svgElement = diagramRef.current.querySelector('svg')
          if (svgElement) {
            svgElement.style.maxWidth = 'none'
            svgElement.style.height = 'auto'
            svgElement.style.transformOrigin = 'center center'
            svgElement.style.transform = `scale(${zoom})`
          }
          setRenderError(null)
        }
      } catch (error) {
        if (!cancelled) {
          if (diagramRef.current) diagramRef.current.innerHTML = ''
          setRenderError('This diagram has invalid Mermaid syntax. Open Mermaid code to edit it.')
        }
      }
    }
    render()
    return () => { cancelled = true }
  }, [activeTab, code, zoom])

  const isMindmap = useMemo(() => code.trimStart().toLowerCase().startsWith('mindmap'), [code])

  const generate = async () => {
    if (!topic.trim() || generating) return
    setGenerating(true)
    try {
      const response = await api.study.conceptGraph({ topic: topic.trim() })
      if (response.success && response.data?.mermaid) {
        setCode(normalizeMermaidSource(response.data.mermaid))
        setActiveTab('diagram')
      }
    } finally {
      setGenerating(false)
    }
  }

  const downloadSvg = () => {
    const svg = diagramRef.current?.querySelector('svg')
    if (!svg) return
    const blob = new Blob([svg.outerHTML], { type: 'image/svg+xml;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `${title.toLowerCase().replace(/[^a-z0-9]+/g, '-') || 'study-map'}.svg`
    link.click()
    URL.revokeObjectURL(url)
  }

  return (
    <Card className="w-full min-w-0 max-w-full overflow-hidden shadow-xs">
      <CardHeader className="space-y-3 p-3 pb-3 sm:p-5 sm:pb-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <CardTitle className="flex items-center gap-2 text-base font-sans font-normal tracking-[-0.02em]">
            <GitBranch className="h-4 w-4 text-primary" /> {title}
            <Badge variant="secondary" className="text-[10px] bg-secondary border border-border">{isMindmap ? 'Mind map' : 'Flowchart'}</Badge>
          </CardTitle>
          <div className="flex items-center gap-1">
            <Button variant={activeTab === 'diagram' ? 'secondary' : 'ghost'} size="sm" className="h-8 text-xs" onClick={() => setActiveTab('diagram')}>Preview</Button>
            <Button variant={activeTab === 'code' ? 'secondary' : 'ghost'} size="sm" className="h-8 text-xs" onClick={() => setActiveTab('code')}>Mermaid code</Button>
          </div>
        </div>
        <div className="flex flex-wrap gap-2">
          <div className="relative w-full min-w-0 flex-1 sm:min-w-[220px]">
            <Sparkles className="absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-primary" />
            <Input value={topic} onChange={(e) => setTopic(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && generate()} placeholder="Generate a concept map for…" className="h-9 pl-9 text-xs" />
          </div>
          <Button size="sm" className="h-9 gap-1.5 text-xs" onClick={generate} disabled={!topic.trim() || generating}>
            {generating ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Wand2 className="h-3.5 w-3.5" />} Generate
          </Button>
        </div>
      </CardHeader>
      <CardContent className="min-w-0 p-3 pt-0 sm:p-5 sm:pt-0">
        {activeTab === 'code' ? (
          <div className="space-y-3">
            <Textarea value={code} onChange={(e) => setCode(e.target.value)} className="min-h-[260px] font-mono text-xs leading-relaxed bg-[#26251e] text-[#f7f7f4] border-0" spellCheck={false} />
            <div className="flex flex-col items-start gap-2 sm:flex-row sm:items-center sm:justify-between">
              <p className="text-[11px] text-muted-foreground">Edit Mermaid syntax, then switch to Preview.</p>
              <Button size="sm" variant="outline" onClick={() => setCode(code.trimStart().startsWith('mindmap') ? DEFAULT_FLOWCHART : DEFAULT_MINDMAP)} className="h-8 gap-1.5 text-xs"><Wand2 className="h-3.5 w-3.5" /> Use {isMindmap ? 'flowchart' : 'mind map'} template</Button>
            </div>
          </div>
        ) : (
          <div className="relative min-h-[300px] overflow-auto rounded-lg border border-border bg-[#faf9f5] p-5">
            <div className="absolute right-3 top-3 z-10 flex items-center gap-1 rounded-md border border-border bg-white/90 p-1 shadow-sm">
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((value) => Math.max(.5, value - .1))}><Minus className="h-3 w-3" /></Button>
              <span className="w-10 text-center text-[10px] text-muted-foreground">{Math.round(zoom * 100)}%</span>
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom((value) => Math.min(1.8, value + .1))}><Plus className="h-3 w-3" /></Button>
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={downloadSvg} title="Download SVG"><Download className="h-3 w-3" /></Button>
              <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => setZoom(1)} title="Reset zoom"><Maximize2 className="h-3 w-3" /></Button>
            </div>
            <div ref={diagramRef} className="flex min-h-[260px] min-w-full items-center justify-center pt-6" />
            {renderError && <p className="absolute inset-x-5 bottom-4 rounded-md bg-red-50 p-2 text-xs text-red-700">{renderError}. Open Mermaid code to fix the syntax.</p>}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
