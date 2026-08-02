'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Search, Globe, FileText, Loader2, Sparkles, Trash2, CheckCircle2, Download } from 'lucide-react'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { MarkdownRenderer } from '@/components/markdown-renderer'

interface Report {
  id: string
  query: string
  content: string
  createdAt: string
}

export default function ResearchPage() {
  const [query, setQuery] = useState('')
  const [researching, setResearching] = useState(false)
  const [exportingPdf, setExportingPdf] = useState(false)
  const [reports, setReports] = useState<Report[]>([])
  const [currentReport, setCurrentReport] = useState<Report | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [activeStage, setActiveStage] = useState(0)
  const stages = [
    { label: 'Research plan', detail: 'Framing questions and source strategy' },
    { label: 'Sub-question decomposition', detail: 'Splitting the topic into focused angles' },
    { label: 'Parallel evidence gathering', detail: 'Running concurrent searches across sub-questions' },
    { label: 'Source review', detail: 'Reading and comparing strong pages' },
    { label: 'Draft synthesis', detail: 'Identifying findings and gaps' },
    { label: 'Gap search', detail: 'Running targeted follow-up research' },
    { label: 'Final report', detail: 'Editing the publication-grade report' },
  ]
  const resultsRef = useRef<HTMLDivElement>(null)

  // Fetch existing reports from backend on mount
  const fetchReports = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.research.list()
      if (res.success && res.data) {
        setReports(res.data)
      } else {
        setError(res.error || 'Failed to load reports')
      }
    } catch {
      setError('Failed to load reports. Ensure the backend is running.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchReports()
  }, [fetchReports])

  useEffect(() => {
    if (resultsRef.current) {
      resultsRef.current.scrollTop = 0
    }
  }, [currentReport?.content])

  const handleResearch = async () => {
    if (!query.trim() || researching) return
    setResearching(true)
    setActiveStage(0)
    setCurrentReport(null)
    setError(null)

    try {
      const res = await api.research.deep(query)
      if (res.success && res.data) {
        const report = { id: res.data.id, query: res.data.query, content: res.data.content, createdAt: res.data.createdAt }
        setCurrentReport(report)
        setReports((prev) => [report, ...prev])
      } else {
        setError(res.error || 'Deep research failed')
      }
    } catch {
      setError('Failed to complete deep research. Ensure the backend is running.')
    } finally {
      setResearching(false)
      setQuery('')
    }
  }

  useEffect(() => {
    if (!researching) return
    const timer = window.setInterval(() => setActiveStage((stage) => Math.min(stage + 1, stages.length - 1)), 3500)
    return () => window.clearInterval(timer)
  }, [researching, stages.length])

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm('Delete this report?')) return

    try {
      const res = await api.research.delete(id)
      if (!res.success) {
        setError(res.error || 'Failed to delete report')
        return
      }
      setReports((prev) => prev.filter((r) => r.id !== id))
      if (currentReport?.id === id) {
        setCurrentReport(null)
      }
    } catch {
      setError('Failed to delete report')
    }
  }

  const handleDownloadPdf = async () => {
    if (!currentReport) return
    setExportingPdf(true)
    try {
      const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
      const response = await fetch(`${BACKEND_URL}/api/reports`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: currentReport.query,
          content: currentReport.content,
          polish: false,
        }),
      })
      if (response.ok) {
        const data = await response.json()
        const downloadUrl = data.data?.downloadUrl || data.downloadUrl
        if (downloadUrl) {
          const fullUrl = downloadUrl.startsWith('http') ? downloadUrl : `${BACKEND_URL}${downloadUrl}`
          window.open(fullUrl, '_blank')
          setExportingPdf(false)
          return
        }
      }
    } catch (err) {
      console.warn('Backend PDF generation failed, using print PDF fallback:', err)
    } finally {
      setExportingPdf(false)
    }

    const printWin = window.open('', '_blank')
    if (printWin) {
      printWin.document.write(`
        <!DOCTYPE html>
        <html>
          <head>
            <title>${currentReport.query} — Research Report</title>
            <style>
              body { font-family: system-ui, -apple-system, sans-serif; padding: 40px; color: #26251e; line-height: 1.6; }
              h1 { font-size: 24px; border-bottom: 2px solid #e5e5e0; padding-bottom: 8px; margin-bottom: 24px; }
              h2 { font-size: 18px; margin-top: 24px; border-bottom: 1px solid #eee; padding-bottom: 4px; }
              h3 { font-size: 15px; margin-top: 18px; }
              pre { background: #f4f4f0; padding: 12px; border-radius: 6px; overflow-x: auto; font-family: monospace; }
              table { border-collapse: collapse; width: 100%; margin: 16px 0; }
              th, td { border: 1px solid #ddd; padding: 8px 12px; text-align: left; }
              th { background-color: #f8f8f6; }
              code { background: #f4f4f0; padding: 2px 4px; border-radius: 4px; font-family: monospace; font-size: 13px; }
            </style>
          </head>
          <body>
            <h1>Research Report: ${currentReport.query}</h1>
            <div>${resultsRef.current?.innerHTML || currentReport.content}</div>
            <script>
              window.onload = function() { window.print(); }
            </script>
          </body>
        </html>
      `)
      printWin.document.close()
    }
  }

  return (
    <div className="space-y-6 animate-fade-in bg-[#faf9f5]">
      <div className="space-y-1">
        <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-[#26251e]">Research</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Internet research, source comparison, and report generation
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-[8px]">
          {error}
          <Button variant="link" size="sm" className="ml-2 text-red-700 underline" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      <Card className="shadow-xs">
        <CardContent className="p-4">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Research a topic..."
                className="pl-10 shadow-sm"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleResearch()}
                disabled={researching}
              />
            </div>
            <Button onClick={handleResearch} disabled={researching || !query.trim()} className="gap-2 shadow-sm">
              {researching ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Globe className="h-4 w-4" />
              )}
              Research
            </Button>
          </div>
        </CardContent>
      </Card>

      {researching && (
        <Card className="shadow-xs">
          <CardContent className="space-y-4 py-6">
            <div className="flex items-center gap-3">
              <Loader2 className="h-5 w-5 animate-spin text-primary" />
              <div>
                <p className="font-semibold text-sm text-foreground">Deep Research is running</p>
                <p className="text-xs text-muted-foreground mt-0.5">A bounded multi-step investigation is in progress.</p>
              </div>
            </div>
            <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
              {stages.map((stage, index) => (
                <div 
                  key={stage.label} 
                  className={`rounded-[8px] border p-3 transition-colors ${
                    index === activeStage 
                      ? 'border-primary/40 bg-primary/5' 
                      : index < activeStage 
                        ? 'border-[#1f8a65]/30 bg-[#1f8a65]/5' 
                        : 'opacity-50 border-border bg-secondary'
                  }`}
                >
                  <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                    {index < activeStage ? (
                      <CheckCircle2 className="h-4 w-4 text-[#1f8a65]" />
                    ) : index === activeStage ? (
                      <Loader2 className="h-4 w-4 animate-spin text-primary" />
                    ) : (
                      <span className="h-4 w-4 rounded-full border border-border bg-secondary" />
                    )}
                    {stage.label}
                  </div>
                  <p className="mt-1 text-[10px] text-muted-foreground leading-normal">{stage.detail}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {currentReport && !researching && (
        <Card className="shadow-xs">
          <CardHeader className="p-5 pb-3 flex flex-row items-center justify-between">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-lg text-foreground">
              <Sparkles className="h-4.5 w-4.5 text-primary" />
              Research Report: {currentReport.query}
            </CardTitle>
            <Button
              onClick={handleDownloadPdf}
              disabled={exportingPdf}
              variant="outline"
              size="sm"
              className="gap-2 cursor-pointer shadow-2xs text-xs"
            >
              {exportingPdf ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Download className="h-3.5 w-3.5 text-primary" />}
              Download PDF
            </Button>
          </CardHeader>
          <CardContent className="p-5 pt-0">
            <div ref={resultsRef} className="max-h-[650px] overflow-y-auto pr-3 scrollbar-thin space-y-4">
              <MarkdownRenderer content={currentReport.content} />
            </div>
          </CardContent>
        </Card>
      )}

      {!currentReport && !researching && (
        <>
          {loading ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-primary" />
                <p>Loading reports...</p>
              </CardContent>
            </Card>
          ) : reports.length > 0 ? (
            <Card className="shadow-xs">
              <CardHeader className="p-5">
                <CardTitle className="flex items-center gap-2 text-base font-sans font-normal tracking-[-0.02em] text-foreground">
                  <FileText className="h-4.5 w-4.5 text-primary" />
                  Previous Reports
                </CardTitle>
              </CardHeader>
              <CardContent className="p-5 pt-0">
                <div className="space-y-2">
                  {reports.map((report) => (
                    <div
                      key={report.id}
                      className="group flex items-center justify-between p-3 rounded-[8px] border border-border bg-secondary hover:bg-secondary/70 transition-colors cursor-pointer shadow-xs"
                      onClick={() => setCurrentReport(report)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-foreground truncate">{report.query}</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5">
                          {formatDate(report.createdAt)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant="secondary" className="bg-card text-muted-foreground border border-border text-[10px] px-2 py-0.5 shadow-none">Report</Badge>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity rounded-[8px] text-[#c64545] hover:bg-[#c64545]/10"
                          onClick={(e) => handleDelete(report.id, e)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <FileText className="h-12 w-12 mx-auto mb-3 opacity-40 text-primary" />
                <p className="font-sans font-normal tracking-[-0.02em] text-lg text-foreground">No research reports yet</p>
                <p className="text-sm mt-1">Enter a topic above and click Research to generate a report</p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
