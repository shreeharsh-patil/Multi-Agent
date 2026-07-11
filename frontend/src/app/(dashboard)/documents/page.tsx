'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FileText, Upload, Download } from 'lucide-react'

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
          <CardDescription>No documents uploaded yet</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12 text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No documents uploaded</p>
            <p className="text-sm mt-1">Upload PDF, DOCX, PPTX, TXT, or Markdown files</p>
            <Button variant="outline" className="mt-4 gap-2">
              <Upload className="h-4 w-4" />
              Upload your first document
            </Button>
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
                <span className="font-medium">0 B</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Limit</span>
                <span className="font-medium">1 GB</span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2 mt-2">
                <div className="bg-primary h-2 rounded-full" style={{ width: '0%' }} />
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
              <p>0 documents processing</p>
              <p>0 documents in queue</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
