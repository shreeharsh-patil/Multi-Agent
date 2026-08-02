'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { FileText, Upload, Trash2, Loader2, HardDrive, FolderOpen, Plus, Share2, ExternalLink } from 'lucide-react'
import { api, mkheaders } from '@/lib/api'
import { cn, formatBytes, formatDate } from '@/lib/utils'
import { downloadSecureFile } from '@/lib/download'

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
  driveWebViewLink?: string
  driveFileId?: string
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
  const [storageUsed, setStorageUsed] = useState<number | null>(null)
  const [highlightedDocumentId, setHighlightedDocumentId] = useState<string | null>(null)

  const fetchDocuments = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.documents.list(selectedWorkspace === 'all' ? undefined : selectedWorkspace)
      if (res.success && res.data) {
        setDocuments(res.data)
      } else {
        setError(res.error || 'Failed to load documents')
      }
    } catch (e) {
      setError('Failed to load documents')
    } finally {
      setLoading(false)
    }
  }, [selectedWorkspace])

  const fetchWorkspaces = useCallback(async () => {
    const res = await api.workspaces.list()
    if (res.success && res.data) {
      setWorkspaces(res.data)
    } else {
      console.warn('Failed to load workspaces:', res.error)
    }
  }, [])

  const fetchStorage = useCallback(async () => {
    try {
      const res = await api.documents.storage()
      if (res.success && res.data) {
        setStorageUsed(res.data.used)
      }
    } catch {
      // Storage info is non-critical; fall back to client-side total
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
    fetchWorkspaces()
    fetchStorage()
  }, [fetchDocuments, fetchWorkspaces, fetchStorage])

  useEffect(() => {
    if (loading || documents.length === 0) return
    const documentId = new URLSearchParams(window.location.search).get('document')
    if (!documentId || !documents.some((document) => document.id === documentId)) return
    setHighlightedDocumentId(documentId)
    const frame = window.requestAnimationFrame(() => {
      document.getElementById(`document-${documentId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
    })
    const timer = window.setTimeout(() => setHighlightedDocumentId(null), 2600)
    return () => {
      window.cancelAnimationFrame(frame)
      window.clearTimeout(timer)
    }
  }, [documents, loading])

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
      const res = await api.documents.upload(file, 'default', setUploadProgress, selectedWorkspace === 'all' ? undefined : selectedWorkspace, accessToken, refreshToken)
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

  const [successAlert, setSuccessAlert] = useState<string | null>(null)

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this document?')) return
    setError(null)
    setSuccessAlert(null)
    try {
      const res = await api.documents.delete(id)
      if (res.success) {
        setDocuments((prev) => prev.filter((d) => d.id !== id))
        setSuccessAlert('Document successfully deleted')
        window.setTimeout(() => setSuccessAlert(null), 4000)
      } else {
        setError(res.error || 'Could not delete document')
      }
    } catch (e) {
      setError('Could not delete document. Ensure the backend is connected.')
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
          'image/png',
          'image/jpeg',
          'image/gif',
          'image/webp',
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
            const uploadRes = await api.documents.upload(
              file,
              'default',
              undefined,
              selectedWorkspace === 'all' ? undefined : selectedWorkspace,
              accessToken,
              refreshToken,
            )
            if (uploadRes.success) imported++
          }
        }
        await fetchDocuments()
        if (imported > 0) {
          alert(`Imported ${imported} file(s) from Google Drive`)
        } else {
          setError('No importable files found in Drive')
        }
      } else {
        setError(res.error || 'Could not read files from Google Drive')
      }
    } catch (e) {
      setError('Import from Drive failed')
    } finally {
      setImportingFromDrive(false)
    }
  }

  const totalSize = documents.reduce((sum, d) => sum + d.fileSize, 0)

  return (
    <div className="space-y-6 animate-fade-in bg-background">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-[#26251e]">Documents</h1>
          <p className="text-sm text-muted-foreground mt-1">
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
              accept=".pdf,.docx,.pptx,.txt,.md,.png,.jpg,.jpeg,.gif,.webp,.svg"
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
        <div className="bg-card border border-border rounded-[8px] p-4 space-y-3 shadow-xs animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex justify-between items-center text-sm">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="font-medium text-foreground">Uploading your document...</span>
            </div>
            <span className="font-semibold text-primary">{uploadProgress}%</span>
          </div>
          <div className="w-full bg-secondary h-2.5 rounded-full overflow-hidden border border-border">
            <div 
              className="bg-primary h-full transition-all duration-300 ease-out" 
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {successAlert && (
        <div className="bg-emerald-500/10 border border-emerald-500/30 text-emerald-700 dark:text-emerald-400 text-sm px-4 py-3 rounded-[8px] flex items-center justify-between animate-in fade-in duration-200">
          <span className="font-medium">{successAlert}</span>
          <Button variant="ghost" size="sm" className="h-6 text-emerald-700 dark:text-emerald-400 hover:bg-emerald-500/20" onClick={() => setSuccessAlert(null)}>
            Dismiss
          </Button>
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

      <Card className="shadow-xs">
        <CardContent className="flex flex-col gap-4 p-5 md:flex-row md:items-center">
          <div className="flex items-center gap-3 md:flex-1">
            <div className="rounded-[8px] bg-secondary p-2 text-primary border border-border shadow-none">
              <FolderOpen className="h-4.5 w-4.5 stroke-[1.5]" />
            </div>
            <div>
              <p className="text-sm font-medium text-foreground">Scope Knowledge</p>
              <p className="text-[11px] text-muted-foreground">Organize documents into dedicated RAG search scopes.</p>
            </div>
          </div>
          <select 
            value={selectedWorkspace} 
            onChange={(e) => setSelectedWorkspace(e.target.value)} 
            className="h-10 rounded-[8px] border border-border bg-card px-3 text-xs md:w-56 focus:outline-none focus:border-primary text-[#26251e] shadow-sm cursor-pointer"
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
              className="h-10 w-36 rounded-[8px] border border-border bg-card px-3 text-xs focus:outline-none focus:border-primary text-[#26251e] placeholder:text-muted-foreground shadow-sm" 
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

      <Card className="shadow-xs">
        <CardHeader>
          <CardTitle className="font-sans font-normal tracking-[-0.02em] text-lg">All Documents</CardTitle>
          <CardDescription className="text-muted-foreground">
            {documents.length === 0
              ? 'No documents uploaded yet'
              : `${documents.filter((d) => d.status === 'ready').length} ready · ${documents.filter((d) => d.status === 'processing').length} processing`}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-12 text-muted-foreground">
              <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-primary" />
              <p>Loading documents...</p>
            </div>
          ) : documents.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <FileText className="h-12 w-12 mx-auto mb-3 opacity-40 text-primary" />
              <p className="font-sans font-normal text-lg text-foreground">No documents uploaded</p>
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
                    id={`document-${doc.id}`}
                    className={cn(
                      'flex items-center gap-4 p-3 rounded-[8px] border bg-secondary hover:bg-secondary/70 transition-colors group shadow-xs',
                      highlightedDocumentId === doc.id ? 'border-primary ring-2 ring-primary/15' : 'border-border',
                    )}
                  >
                    <div className="p-2 rounded-[8px] bg-card text-primary border border-border">
                      <FileText className="h-5 w-5" />
                    </div>
                    <div className="flex-1 min-w-0 cursor-pointer" onClick={() => downloadSecureFile(api.documents.downloadUrl(doc.id), doc.fileName)}>
                      <p className="font-medium text-sm text-foreground truncate">{doc.fileName}</p>
                      <div className="flex items-center gap-3 text-xs text-muted-foreground mt-0.5">
                        <span className="font-mono">{doc.fileType.toUpperCase()}</span>
                        <span>{formatBytes(doc.fileSize)}</span>
                        <span>{formatDate(doc.createdAt)}</span>
                        {doc.chunks > 0 && <span>{doc.chunks} chunks</span>}
                        {doc.ocrPages ? <span className="text-primary font-medium">{doc.ocrPages} OCR page{doc.ocrPages !== 1 ? 's' : ''}</span> : null}
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
                    {doc.driveWebViewLink && (
                      <a
                        href={doc.driveWebViewLink}
                        target="_blank"
                        rel="noopener noreferrer"
                        title="Open in Google Drive"
                        className="inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-[10px] font-medium border border-[#1f8a65]/30 bg-[#1f8a65]/5 text-[#1f8a65] hover:bg-[#1f8a65]/10 hover:border-[#1f8a65]/50 transition-all shrink-0"
                      >
                        <ExternalLink className="h-3 w-3" />
                        Drive
                      </a>
                    )}
                    <select 
                      value={doc.workspaceId || 'unfiled'} 
                      onChange={(e) => moveDocument(doc.id, e.target.value)} 
                      className="hidden h-8 max-w-36 rounded-[8px] border border-border bg-card px-2 text-xs text-foreground sm:block focus:outline-none focus:border-primary cursor-pointer"
                    >
                      <option value="unfiled">Unfiled</option>
                      {workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
                    </select>
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => downloadSecureFile(api.documents.downloadUrl(doc.id), doc.fileName)}
                      className="opacity-0 group-hover:opacity-100 transition-opacity text-muted-foreground hover:text-foreground hover:bg-secondary/70 h-8 w-8 rounded-[8px]"
                      title="Download File"
                    >
                      <FileText className="h-4 w-4" />
                    </Button>
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
        <Card className="shadow-xs">
          <CardHeader>
            <CardTitle className="text-base font-sans font-normal tracking-[-0.02em] text-foreground">Supported Formats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-xs text-muted-foreground leading-relaxed">
              <p className="font-mono text-[#26251e]">PDF · DOCX · PPTX · TXT · MD</p>
              <p>Maximum file size: 50 MB</p>
              <p>All documents are processed and indexed for RAG</p>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow-xs">
          <CardHeader>
            <CardTitle className="text-base font-sans font-normal tracking-[-0.02em] text-foreground">Storage</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Used</span>
                <span className="font-semibold text-foreground">{storageUsed !== null ? formatBytes(storageUsed) : formatBytes(totalSize)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Documents</span>
                <span className="font-semibold text-foreground">{documents.length} file{documents.length !== 1 ? 's' : ''}</span>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card className="shadow-xs">
          <CardHeader>
            <CardTitle className="text-base font-sans font-normal tracking-[-0.02em] text-foreground">Processing Queue</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-xs text-muted-foreground leading-relaxed">
              <p>{documents.filter((d) => d.status === 'processing').length} documents processing</p>
              <p>0 documents in queue</p>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
