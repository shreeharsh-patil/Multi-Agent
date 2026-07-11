'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Search, Upload, BookOpen } from 'lucide-react'

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
                <BookOpen className="h-5 w-5" />
                Indexed Documents
              </CardTitle>
              <CardDescription>No documents indexed yet</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="text-center py-12 text-muted-foreground">
                <BookOpen className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p>No documents in your knowledge base</p>
                <p className="text-sm mt-1">Upload documents to build your knowledge base</p>
                <Button variant="outline" className="mt-4 gap-2">
                  <Upload className="h-4 w-4" />
                  Upload your first document
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <Search className="h-5 w-5" />
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
                  { label: 'Total Documents', value: '0' },
                  { label: 'Total Chunks', value: '0' },
                  { label: 'Vector Index Size', value: '0 B' },
                  { label: 'Last Updated', value: '—' },
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
