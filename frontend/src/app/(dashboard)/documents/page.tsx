'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { FileText, Upload, Download, Trash2, File, FileSpreadsheet, FileImage } from 'lucide-react'

const documents = [
  { id: '1', name: 'AI_Introduction.pdf', type: 'PDF', size: '2.4 MB', status: 'ready', date: '2026-07-10' },
  { id: '2', name: 'ML_Fundamentals.docx', type: 'DOCX', size: '1.8 MB', status: 'ready', date: '2026-07-09' },
  { id: '3', name: 'Neural_Networks.txt', type: 'TXT', size: '156 KB', status: 'ready', date: '2026-07-08' },
  { id: '4', name: 'Research_Paper.pdf', type: 'PDF', size: '3.2 MB', status: 'processing', date: '2026-07-07' },
  { id: '5', name: 'Study_Notes.md', type: 'MD', size: '45 KB', status: 'ready', date: '2026-07-06' },
  { id: '6', name: 'Presentation.pptx', type: 'PPTX', size: '5.1 MB', status: 'error', date: '2026-07-05' },
]

function getFileIcon(type: string) {
  switch (type) {
    case 'PDF': return <FileText className="h-8 w-8 text-red-500" />
    case 'DOCX': return <FileText className="h-8 w-8 text-blue-500" />
    case 'PPTX': return <FileSpreadsheet className="h-8 w-8 text-orange-500" />
    default: return <File className="h-8 w-8 text-muted-foreground" />
  }
}

export default function DocumentsPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Documents</h1>
          <p className="text-muted-foreground mt-1">
            Upload and manage your documents
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="gap-2">
            <Download className="h-4 w-4" />
            Import from Drive
          </Button>
          <Button className="gap-2">
            <Upload className="h-4 w-4" />
            Upload
          </Button>
        </div>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>All Documents</CardTitle>
          <CardDescription>6 documents · 12.7 MB total</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {documents.map((doc) => (
              <div key={doc.id} className="flex items-center gap-4 p-4 rounded-lg border hover:bg-secondary/50 transition-colors">
                {getFileIcon(doc.type)}
                <div className="flex-1 min-w-0">
                  <p className="font-medium truncate">{doc.name}</p>
                  <div className="flex items-center gap-3 text-sm text-muted-foreground">
                    <span>{doc.type}</span>
                    <span>{doc.size}</span>
                    <span>{doc.date}</span>
                  </div>
                </div>
                <Badge variant={doc.status === 'ready' ? 'success' : doc.status === 'processing' ? 'warning' : 'destructive'}>
                  {doc.status}
                </Badge>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon">
                    <Download className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon">
                    <Trash2 className="h-4 w-4 text-destructive" />
                  </Button>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Supported Formats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>PDF · DOCX · PPTX · TXT · MD</p>
              <p>Maximum file size: 50 MB</p>
              <p>All documents are processed and indexed for RAG</p>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Storage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Used</span>
                <span className="font-medium">12.7 MB</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Limit</span>
                <span className="font-medium">1 GB</span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2 mt-2">
                <div className="bg-primary h-2 rounded-full" style={{ width: '1.3%' }} />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Processing Queue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-sm text-muted-foreground">
              <p>1 document processing</p>
              <p>0 documents in queue</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
