'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { BookOpen, Search, Upload, FileText, Plus, Brain } from 'lucide-react'

const knowledgeItems = [
  { id: '1', title: 'Introduction to AI', type: 'PDF', pages: 24, date: '2026-07-10', chunks: 48 },
  { id: '2', title: 'Machine Learning Fundamentals', type: 'DOCX', pages: 56, date: '2026-07-09', chunks: 112 },
  { id: '3', title: 'Neural Networks Notes', type: 'TXT', pages: 12, date: '2026-07-08', chunks: 36 },
]

export default function KnowledgeBasePage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Knowledge Base</h1>
          <p className="text-muted-foreground mt-1">
            Search and manage your document knowledge
          </p>
        </div>
        <Button className="gap-2">
          <Upload className="h-4 w-4" />
          Upload Document
        </Button>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input placeholder="Search your knowledge base..." className="pl-10" />
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText className="h-5 w-5" />
                Indexed Documents
              </CardTitle>
              <CardDescription>3 documents indexed · 196 total chunks</CardDescription>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[400px]">
                <div className="space-y-3">
                  {knowledgeItems.map((item) => (
                    <Card key={item.id} className="border-0 bg-secondary/50">
                      <CardContent className="p-4">
                        <div className="flex items-start justify-between">
                          <div className="flex items-start gap-3">
                            <div className="p-2 rounded-lg bg-primary/10 text-primary">
                              <BookOpen className="h-5 w-5" />
                            </div>
                            <div>
                              <h3 className="font-medium">{item.title}</h3>
                              <div className="flex items-center gap-3 mt-1 text-sm text-muted-foreground">
                                <Badge variant="secondary" className="text-xs">{item.type}</Badge>
                                <span>{item.pages} pages</span>
                                <span>{item.chunks} chunks</span>
                              </div>
                            </div>
                          </div>
                          <Button variant="ghost" size="sm">
                            <Brain className="h-4 w-4" />
                          </Button>
                        </div>
                        <p className="text-xs text-muted-foreground mt-2">Added {item.date}</p>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Brain className="h-5 w-5" />
                Ask Knowledge Base
              </CardTitle>
              <CardDescription>Query your documents using RAG</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <Input placeholder="Ask a question about your documents..." />
                <Button className="w-full gap-2">
                  <Search className="h-4 w-4" />
                  Search
                </Button>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-lg">Quick Stats</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { label: 'Total Documents', value: '3' },
                  { label: 'Total Chunks', value: '196' },
                  { label: 'Vector Index Size', value: '2.4 MB' },
                  { label: 'Last Updated', value: '2026-07-10' },
                ].map((stat) => (
                  <div key={stat.label} className="flex items-center justify-between text-sm">
                    <span className="text-muted-foreground">{stat.label}</span>
                    <span className="font-medium">{stat.value}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
