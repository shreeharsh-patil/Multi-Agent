'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { FileText, Upload, Trash2, Loader2, HardDrive, FolderOpen, Plus, Share2 } from 'lucide-react'
import { api, mkheaders } from '@/lib/api'
import { formatBytes, formatDate } from '@/lib/utils'

interface Document {
  id: string
  fileName: string
  fileType: string
  fileSize: number
  status: string
  chunks: number
  createdAt: string
  workspaceId?: string
  ocrPages?: number
}

interface Workspace {
  id: string
  name: string
  color: string
  documentCount: number
}

export default function DocumentsPage() {
  const { data: session } = useSession()
  const accessToken = (session as any)?.accessToken
  const refreshToken = (session as any)?.refreshToken || ''
  const [documents, setDocuments] = useState<Document[]>([])
  const [loading, setLoading] = useState(false)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<number>(0)
  const [importingFromDrive, setImportingFromDrive] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [workspaces, setWorkspaces] = useState<Workspace[]>([])
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>('all')
  const [newWorkspaceName, setNewWorkspaceName] = useState('')
  const [creatingWorkspace, setCreatingWorkspace] = useState(false)
  const [inviteCopied, setInviteCopied] = useState(false)

  const fetchDocuments = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.documents.list(selectedWorkspace === 'all' ? undefined : selectedWorkspace)
      if (res.success && res.data) {
        setDocuments(res.data)
      }
    } catch (e) {
      setError('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [selectedWorkspace])

  const fetchWorkspaces = useCallback(async () => {
    const res = await api.workspaces.list()
    if (res.success && res.data) setWorkspaces(res.data)
  }, [])

  useEffect(() => {
    fetchDocuments()
    fetchWorkspaces()
  }, [fetchDocuments, fetchWorkspaces])

  const createWorkspace = async () => {
    if (!newWorkspaceName.trim()) return
    setCreatingWorkspace(true)
    const res = await api.workspaces.create({ name: newWorkspaceName.trim() })
    if (res.success && res.data) {
      setNewWorkspaceName('')
      await fetchWorkspaces()
      setSelectedWorkspace(res.data.id)
    } else setError(res.error || 'Could not create workspace')
    setCreatingWorkspace(false)
  }

  const copyWorkspaceInvite = async () => {
    if (selectedWorkspace === 'all' || selectedWorkspace === 'unfiled') return
    await navigator.clipboard?.writeText(`${window.location.origin}/shared/workspace/${selectedWorkspace}`)
    setInviteCopied(true)
    window.setTimeout(() => setInviteCopied(false), 2200)
  }

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadProgress(0)
    setError(null)
    try {
      const res = await api.documents.upload(file, 'default', setUploadProgress, selectedWorkspace === 'all' ? undefined : selectedWorkspace)
      if (res.success) {
        await fetchDocuments()
      } else {
        setError(res.error || 'Upload failed')
      }
    } catch (e) {
      setError('Upload failed')
    } finally {
      setUploading(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document?')) return
    try {
      await api.documents.delete(id)
      setDocuments((prev) => prev.filter((d) => d.id !== id))
    } catch (e) {
      setError('Delete failed')
    }
  }

  const moveDocument = async (id: string, workspaceId: string) => {
    const res = await api.documents.moveToWorkspace(id, workspaceId === 'unfiled' ? undefined : workspaceId)
    if (res.success) {
      await fetchDocuments()
      await fetchWorkspaces()
    } else setError(res.error || 'Could not move document')
  }

  const handleImportFromDrive = async () => {
    if (!accessToken) {
      setError('Please connect Google Drive first from Settings')
      return
    }
    setImportingFromDrive(true)
    setError(null)
    try {
      const res = await api.drive.listFiles(accessToken, refreshToken)
      if (res.success && res.data) {
        const supportedMimes = [
          'application/pdf',
          'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
          'application/vnd.openxmlformats-officedocument.presentationml.presentation',
          'text/plain',
          'text/markdown',
        ]
        const docs = res.data.files.filter(
          (f) => !f.isFolder && supportedMimes.includes(f.mimeType),
        )
        let imported = 0
        for (const doc of docs) {
          const downloadRes = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/drive/download/${doc.id}/content`,
            { headers: mkheaders(accessToken, refreshToken) },
          )
          if (downloadRes.ok) {
            const blob = await downloadRes.blob()
            const file = new File([blob], doc.name, { type: doc.mimeType })
            const uploadRes = await api.documents.upload(file)
            if (uploadRes.success) imported++
          }
        }
        await fetchDocuments()
        if (imported > 0) {
          alert(`Imported ${imported} file(s) from Google Drive`)
        } else {
          setError('No importable files found in Drive')
        }
      }
    } catch (e) {
      setError('Import from Drive failed')
    } finally {
      setImportingFromDrive(false)
    }
  }

  const totalSize = documents.reduce((sum, d) => sum + d.fileSize, 0)

  return (
    <div className="space-y-6 animate-fade-in bg-[#faf9f5]">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-serif font-normal text-[#141413]">Documents</h1>
          <p className="text-sm text-[#6c6a64] mt-1">
            {documents.length} document{documents.length !== 1 ? 's' : ''} · {formatBytes(totalSize)} total
          </p>
        </div>
        <div className="flex gap-3">
          <Button
            variant="outline"
            className="gap-2 shadow-sm"
            onClick={handleImportFromDrive}
            disabled={importingFromDrive || !accessToken}
          >
            {importingFromDrive ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <HardDrive className="h-4 w-4" />
            )}
            Import from Drive
          </Button>
          <label>
            <input
              type="file"
              accept=".pdf,.docx,.pptx,.txt,.md"
              className="hidden"
              onChange={handleUpload}
              disabled={uploading}
            />
            <Button className="gap-2 shadow-sm cursor-pointer" disabled={uploading} asChild>
              <span>
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Upload className="h-4 w-4" />
                )}
                {uploading ? `Uploading ${uploadProgress}%` : 'Upload'}
              </span>
            </Button>
          </label>
        </div>
      </div>

      {uploading && (
        <div className="bg-[#efe9de] border border-[#e6dfd8] rounded-[8px] p-4 space-y-3 shadow-xs animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex justify-between items-center text-sm">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-[#cc785c]" />
              <span className="font-medium text-[#141413]">Uploading your document...</span>
            </div>
            <span className="font-semibold text-[#cc785c]">{uploadProgress}%</span>
          </div>
          <div className="w-full bg-[#faf9f5] h-2.5 rounded-full overflow-hidden border border-[#e6dfd8]">
            <div 
              className="bg-[#cc785c] h-full transition-all duration-300 ease-out" 
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-[8px]">
          {error}
          <Button variant="link" size="sm" className="ml-2 text-red-700 underline" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
        <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center">
          <div className="flex items-center gap-3 md:flex-1">
            <div className="rounded-[8px] bg-[#faf9f5] p-2 text-[#cc785c] border border-[#e6dfd8] shadow-xs">
              <FolderOpen className="h-4.5 w-4.5 stroke-[1.5]" />
            </div>
            <div>
              <p className="text-sm font-medium text-[#141413]">Scope Knowledge</p>
              <p className="text-[11px] text-[#6c6a64]">Organize documents into dedicated RAG search scopes.</p>
            </div>
          </div>
          <select 
            value={selectedWorkspace} 
            onChange={(e) => setSelectedWorkspace(e.target.value)} 
            className="h-10 rounded-[8px] border border-[#e6dfd8] bg-[#faf9f5] px-3 text-xs md:w-56 focus:outline-none focus:border-[#cc785c] text-[#141413] shadow-sm"
          >
            <option value="all">All workspaces</option>
            <option value="unfiled">Unfiled documents</option>
            {workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>
                {workspace.name} ({workspace.documentCount})
              </option>
            ))}
          </select>
          <div className="flex gap-2">
            <input 
              value={newWorkspaceName} 
              onChange={(e) => setNewWorkspaceName(e.target.value)} 
              onKeyDown={(e) => e.key === 'Enter' && createWorkspace()} 
              placeholder="New scope..." 
              className="h-10 w-36 rounded-[8px] border border-[#e6dfd8] bg-[#faf9f5] px-3 text-xs focus:outline-none focus:border-[#cc785c] text-[#141413] placeholder:text-[#6c6a64] shadow-sm" 
            />
            <Button variant="outline" size="sm" onClick={createWorkspace} disabled={creatingWorkspace || !newWorkspaceName.trim()} className="gap-1 h-10 px-3 text-xs rounded-[8px]">
              <Plus className="h-3.5 w-3.5" /> Create
            </Button>
            <Button variant="outline" size="sm" onClick={copyWorkspaceInvite} disabled={selectedWorkspace === 'all' || selectedWorkspace === 'unfiled'} className="gap-1 h-10 px-3 text-xs rounded-[8px]">
              <Share2 className="h-3.5 w-3.5" /> {inviteCopied ? 'Copied' : 'Invite'}
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
        <CardHeader>
          <CardTitle className="font-serif font-normal text-lg">All Documents</CardTitle>
          <CardDescription className="text-[#6c6a64]">
            {documents.length === 0
              ? 'No documents uploaded yet'
              : `${documents.filter((d) => d.status === 'ready').length} ready · ${documents.filter((d) => d.status === 'processing').length} processing`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-12 text-[#6c6a64]">
              <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-[#cc785c]" />
              <p>Loading documents...</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12 text-[#6c6a64]">
              <FileText className="h-12 w-12 mx-auto mb-3 opacity-40 text-[#cc785c]" />
              <p className="font-serif font-normal text-lg">No documents uploaded</p>
              <p className="text-sm mt-1">Upload PDF, DOCX, PPTX, TXT, or Markdown files</p>
              <label>
                <input
                  type="file"
                  accept=".pdf,.docx,.pptx,.txt,.md"
                  className="hidden"
                  onChange={handleUpload}
                  disabled={uploading}
                />
                <Button variant="outline" className="mt-4 gap-2 cursor-pointer shadow-sm" disabled={uploading} asChild>
                  <span>
                    {uploading ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <Upload className="h-4 w-4" />
                    )}
                    {uploading ? `Uploading ${uploadProgress}%` : 'Upload your first document'}
                  </span>
                </Button>
              </label>
            </div>
          ) : (
            <ScrollArea className="h-[400px]">
              <div className="space-y-2">
                {documents.map((doc) => (
                  <div
                    key={doc.id}
                    className="flex items-center gap-4 p-3 rounded-[8px] border border-[#e6dfd8] bg-[#faf9f5] hover:bg-[#e8e0d2]/40 transition-colors group shadow-xs"
                  >
                    <div className="p-2 rounded-[8px] bg-[#efe9de] text-[#cc785c] border border-[#e6dfd8]">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium text-sm text-[#141413] truncate">{doc.fileName}</p>
                      <div className="flex items-center gap-3 text-xs text-[#6c6a64] mt-0.5">
                        <span className="font-mono">{doc.fileType.toUpperCase()}</span>
                        <span>{formatBytes(doc.fileSize)}</span>
                        <span>{formatDate(doc.createdAt)}</span>
                        {doc.chunks > 0 && <span>{doc.chunks} chunks</span>}
                        {doc.ocrPages ? <span className="text-[#cc785c] font-medium">{doc.ocrPages} OCR page{doc.ocrPages !== 1 ? 's' : ''}</span> : null}
                      </div>
                    </div>
                    <Badge
                      className="rounded-full px-2.5 py-0.5 border"
                      variant={
                        doc.status === 'ready'
                          ? 'success'
                          : doc.status === 'processing'
                            ? 'secondary'
                            : 'destructive'
                      }
                    >
                      {doc.status === 'processing' && <Loader2 className="h-3 w-3 animate-spin mr-1" />}
                      {doc.status}
                    </Badge>
                    <select 
                      value={doc.workspaceId || 'unfiled'} 
                      onChange={(e) => moveDocument(doc.id, e.target.value)} 
                      className="hidden h-8 max-w-36 rounded-[8px] border border-[#e6dfd8] bg-[#faf9f5] px-2 text-xs text-[#141413] sm:block focus:outline-none focus:border-[#cc785c]"
                    >
                      <option value="unfiled">Unfiled</option>
                      {workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
                    </select>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(doc.id)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-[#c64545] hover:bg-[#c64545]/10 h-8 w-8 rounded-[8px]"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader>
            <CardTitle className="text-base font-serif font-normal text-[#141413]">Supported Formats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-xs text-[#6c6a64] leading-relaxed">
              <p className="font-mono">PDF · DOCX · PPTX · TXT · MD</p>
              <p>Maximum file size: 50 MB</p>
              <p>All documents are processed and indexed for RAG</p>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader>
            <CardTitle className="text-base font-serif font-normal text-[#141413]">Storage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#6c6a64]">Used</span>
                <span className="font-semibold text-[#141413]">{formatBytes(totalSize)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6c6a64]">Limit</span>
                <span className="font-semibold text-[#141413]">1 GB</span>
              </div>
              <div className="w-full bg-[#faf9f5] rounded-full h-2 mt-2 border border-[#e6dfd8] overflow-hidden">
                <div
                  className="bg-[#cc785c] h-full rounded-full transition-all"
                  style={{ width: `${Math.min((totalSize / (1024 * 1024 * 1024)) * 100, 100)}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader>
            <CardTitle className="text-base font-serif font-normal text-[#141413]">Processing Queue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-xs text-[#6c6a64] leading-relaxed">
              <p>{documents.filter((d) => d.status === 'processing').length} documents processing</p>
              <p>0 documents in queue</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
