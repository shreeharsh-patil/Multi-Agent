'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Search, Globe, FileText, Loader2, Sparkles, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'

interface Report {
  id: string
  query: string
  content: string
  createdAt: string
}

export default function ResearchPage() {
  const [query, setQuery] = useState('')
  const [researching, setResearching] = useState(false)
  const [reports, setReports] = useState<Report[]>([])
  const [currentReport, setCurrentReport] = useState<Report | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const resultsRef = useRef<HTMLDivElement>(null)

  // Fetch existing reports from backend on mount
  const fetchReports = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.research.list()
      if (res.success && res.data) {
        setReports(res.data)
      }
    } catch {
      // Silently fail — user sees empty state
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchReports()
  }, [fetchReports])

  useEffect(() => {
    if (resultsRef.current) {
      resultsRef.current.scrollTop = resultsRef.current.scrollHeight
    }
  }, [currentReport?.content])

  const handleResearch = async () => {
    if (!query.trim() || researching) return
    setResearching(true)
    setCurrentReport(null)
    setError(null)

    try {
      const res = await api.chat.send({
        message: `Conduct thorough research on: ${query}
        
Please structure your response with:
1. **Abstract** — Brief overview of the topic
2. **Key Findings** — Main points discovered
3. **Analysis** — Deeper dive into the topic
4. **Sources** — Any sources or references

Make this comprehensive and well-structured.`,
        agent_id: 'research',
      })

      if (res.success && res.data) {
        const content = res.data.output

        // Persist to backend
        const createRes = await api.research.create({ query, content })
        if (createRes.success && createRes.data) {
          setCurrentReport(createRes.data)
          setReports((prev) => [createRes.data!, ...prev])
        } else {
          // Save locally even if persistence fails
          const localReport: Report = {
            id: crypto.randomUUID(),
            query,
            content,
            createdAt: new Date().toISOString(),
          }
          setCurrentReport(localReport)
          setReports((prev) => [localReport, ...prev])
        }
      } else {
        setError(res.error || 'Research failed')
      }
    } catch (e) {
      setError('Failed to complete research. Ensure the backend is running.')
    } finally {
      setResearching(false)
      setQuery('')
    }
  }

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm('Delete this report?')) return

    try {
      await api.research.delete(id)
      setReports((prev) => prev.filter((r) => r.id !== id))
      if (currentReport?.id === id) {
        setCurrentReport(null)
      }
    } catch {
      setError('Failed to delete report')
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Research</h1>
        <p className="text-muted-foreground mt-1">
          Internet research, source comparison, and report generation
        </p>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-lg">
          {error}
          <Button variant="link" size="sm" className="ml-2" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      <Card>
        <CardContent className="p-6">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Research a topic..."
                className="pl-10"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleResearch()}
                disabled={researching}
              />
            </div>
            <Button onClick={handleResearch} disabled={researching || !query.trim()} className="gap-2">
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
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3" />
            <p className="font-medium">Researching...</p>
            <p className="text-sm mt-1">Gathering and analyzing information</p>
          </CardContent>
        </Card>
      )}

      {currentReport && !researching && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Research Report: {currentReport.query}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea ref={resultsRef} className="max-h-[600px]">
              <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                {currentReport.content}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {!currentReport && !researching && (
        <>
          {loading ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3" />
                <p className="font-medium">Loading reports...</p>
              </CardContent>
            </Card>
          ) : reports.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <FileText className="h-5 w-5" />
                  Previous Reports
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {reports.map((report) => (
                    <div
                      key={report.id}
                      className="group flex items-center justify-between p-3 rounded-lg border hover:bg-secondary/50 transition-colors cursor-pointer"
                      onClick={() => setCurrentReport(report)}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{report.query}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatDate(report.createdAt)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant="secondary">Report</Badge>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={(e) => handleDelete(report.id, e)}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
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
                <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p className="text-lg font-medium">No research reports yet</p>
                <p className="text-sm mt-1">Enter a topic above and click Research to generate a report</p>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
