'use client'

import { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Search, Upload, BookOpen, Loader2, FileText, Sparkles, ExternalLink } from 'lucide-react'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import Link from 'next/link'

interface Document {
  id: string
  fileName: string
  fileType: string
  fileSize: number
  status: string
  chunks: number
  createdAt: string
}

interface QueryResult {
  id: string
  content: string
  metadata: Record<string, unknown>
  score: number
}

export default function KnowledgeBasePage() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Query state
  const [query, setQuery] = useState('')
  const [querying, setQuerying] = useState(false)
  const [answer, setAnswer] = useState('')
  const [results, setResults] = useState<QueryResult[]>([])
  const [citations, setCitations] = useState<Array<{ file_name: string; page_number?: number }>>([])
  const resultsRef = useRef<HTMLDivElement>(null)

  const fetchDocuments = async () => {
    setLoading(true)
    try {
      const res = await api.documents.list()
      if (res.success && res.data) {
        setDocuments(res.data)
      }
    } catch (e) {
      setError('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchDocuments()
  }, [])

  useEffect(() => {
    if (resultsRef.current) {
      resultsRef.current.scrollTop = resultsRef.current.scrollHeight
    }
  }, [answer])

  const handleQuery = async () => {
    if (!query.trim()) return
    setQuerying(true)
    setAnswer('')
    setResults([])
    setCitations([])
    try {
      const res = await api.knowledge.query(query)
      if (res.success && res.data) {
        setAnswer(res.data.answer)
        setResults(res.data.results)
        setCitations(res.data.citations)
      } else {
        setError(res.error || 'Query failed')
      }
    } catch (e) {
      setError('Query failed. Ensure Gemini API key is configured.')
    } finally {
      setQuerying(false)
    }
  }

  const readyDocs = documents.filter((d) => d.status === 'ready')
  const totalChunks = documents.reduce((sum, d) => sum + d.chunks, 0)
  const lastUpdated = documents.length > 0
    ? documents.sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime())[0]?.createdAt
    : null

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
          <p className="text-muted-foreground mt-1">
            Search and query your document knowledge
          </p>
        </div>
        <Link href="/documents">
          <Button className="gap-2">
            <Upload className="h-4 w-4" />
            Upload Document
          </Button>
        </Link>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-lg">
          {error}
          <Button variant="link" size="sm" className="ml-2" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
        <div className="space-y-4">
          {/* Query Input */}
          <Card>
            <CardContent className="p-4">
              <div className="flex gap-3">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  <Input
                    placeholder="Ask a question about your documents..."
                    className="pl-10"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleQuery()}
                    disabled={querying}
                  />
                </div>
                <Button onClick={handleQuery} disabled={querying || !query.trim()} className="gap-2">
                  {querying ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Search className="h-4 w-4" />
                  )}
                  Search
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Results */}
          {querying && (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                <p>Searching knowledge base and generating answer...</p>
              </CardContent>
            </Card>
          )}

          {answer && !querying && (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2 text-lg">
                  <Sparkles className="h-5 w-5 text-primary" />
                  Answer
                </CardTitle>
              </CardHeader>
              <CardContent>
                <ScrollArea ref={resultsRef} className="max-h-[400px]">
                  <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                    {answer}
                  </div>
                </ScrollArea>

                {citations.length > 0 && (
                  <>
                    <Separator className="my-4" />
                    <h4 className="text-sm font-semibold mb-2">Sources</h4>
                    <div className="space-y-2">
                      {citations.map((c, i) => (
                        <div key={i} className="flex items-center gap-2 text-sm text-muted-foreground">
                          <FileText className="h-3 w-3 shrink-0" />
                          <span className="truncate">{c.file_name}</span>
                          {c.page_number && <Badge variant="outline" className="text-xs">p.{c.page_number}</Badge>}
                        </div>
                      ))}
                    </div>
                  </>
                )}
              </CardContent>
            </Card>
          )}

          {/* Indexed Documents */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <BookOpen className="h-5 w-5" />
                Indexed Documents
              </CardTitle>
              <CardDescription>
                {loading ? 'Loading...' : `${readyDocs.length} documents indexed`}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="text-center py-8 text-muted-foreground">
                  <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                  <p className="text-sm">Loading documents...</p>
                </div>
              ) : readyDocs.length === 0 ? (
                <div className="text-center py-8 text-muted-foreground">
                  <BookOpen className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No documents indexed</p>
                  <p className="text-sm mt-1">Upload documents from the Documents page</p>
                  <Link href="/documents">
                    <Button variant="outline" className="mt-4 gap-2">
                      <Upload className="h-4 w-4" />
                      Go to Documents
                    </Button>
                  </Link>
                </div>
              ) : (
                <ScrollArea className="h-[300px]">
                  <div className="space-y-3">
                    {readyDocs.map((doc) => (
                      <div key={doc.id} className="flex items-center gap-3 p-2 rounded-lg hover:bg-secondary/50 transition-colors">
                        <div className="p-2 rounded-lg bg-primary/10 text-primary">
                          <FileText className="h-4 w-4" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium truncate">{doc.fileName}</p>
                          <p className="text-xs text-muted-foreground">
                            {doc.chunks} chunks · {formatDate(doc.createdAt)}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                </ScrollArea>
              )}
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Stats</CardTitle>
            </CardHeader>
            <CardContent>
              {loading ? (
                <div className="flex justify-center py-4">
                  <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
                </div>
              ) : (
                <div className="space-y-3">
                  {[
                    { label: 'Total Documents', value: String(readyDocs.length) },
                    { label: 'Total Chunks', value: String(totalChunks) },
                    { label: 'Indexed', value: readyDocs.length > 0 ? 'Yes' : 'No' },
                    { label: 'Last Updated', value: lastUpdated ? formatDate(lastUpdated) : '—' },
                  ].map((stat) => (
                    <div key={stat.label} className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground">{stat.label}</span>
                      <span className="font-medium">{stat.value}</span>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
