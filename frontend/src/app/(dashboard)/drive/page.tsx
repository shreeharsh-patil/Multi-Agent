'use client'

import { useState, useEffect, useCallback } from 'react'
import { useSession, signIn } from 'next-auth/react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  Folder,
  File,
  FileText,
  Image as ImageIcon,
  FileSpreadsheet,
  RefreshCw,
  Upload,
  Trash2,
  Download,
  ExternalLink,
  Loader2,
  LogIn,
  HardDrive,
} from 'lucide-react'
import { api, mkheaders } from '@/lib/api'
import { formatBytes, formatDate } from '@/lib/utils'

interface DriveFile {
  id: string
  name: string
  mimeType: string
  size: number
  modifiedTime: string
  webViewLink: string
  iconLink?: string
  isFolder: boolean
}

interface DriveStorage {
  limit: number
  usage: number
  usageInDrive: number
  usageInDriveTrash: number
}

export default function DrivePage() {
  const { data: session } = useSession()
  const sessionError = (session as any)?.error
  const accessToken = !sessionError ? (session as any)?.accessToken || '' : ''
  const refreshToken = (session as any)?.refreshToken || ''
  const [files, setFiles] = useState<DriveFile[]>([])
  const [storage, setStorage] = useState<DriveStorage | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadProgress, setUploadProgress] = useState<number>(0)

  const fetchFiles = useCallback(async () => {
    if (!accessToken) return
    setLoading(true)
    setError(null)
    try {
      const [filesRes, storageRes] = await Promise.all([
        api.drive.listFiles(accessToken, refreshToken),
        api.drive.getStorage(accessToken, refreshToken),
      ])
      if (filesRes.success && filesRes.data) {
        setFiles(filesRes.data.files)
      } else {
        setError(filesRes.error || 'Failed to load files')
      }
      if (storageRes.success && storageRes.data) {
        setStorage(storageRes.data)
      }
    } catch (e) {
      setError('Failed to connect to Drive. Ensure you are signed in.')
    } finally {
      setLoading(false)
    }
  }, [accessToken, refreshToken])

  useEffect(() => {
    if (accessToken) {
      fetchFiles()
    }
  }, [accessToken, fetchFiles])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    const target = e.target
    if (!file || !accessToken) return
    setUploading(true)
    setUploadProgress(0)
    try {
      const res = await api.drive.uploadToDrive(file, accessToken, refreshToken, undefined, setUploadProgress)
      if (res.success) {
        await fetchFiles()
      } else {
        setError(res.error || 'Upload failed')
      }
    } catch {
      setError('Upload failed')
    } finally {
      setUploading(false)
      if (target) target.value = ''
    }
  }

  const handleDelete = async (fileId: string) => {
    if (!confirm('Delete this file from Google Drive?')) return
    try {
      const res = await api.drive.deleteFile(fileId, accessToken, refreshToken)
      if (res.success) {
        setFiles((prev) => prev.filter((f) => f.id !== fileId))
      } else {
        setError(res.error || 'Delete failed')
      }
    } catch (e) {
      setError('Delete failed')
    }
  }

  const handleDownload = async (file: DriveFile) => {
    if (!accessToken) return
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/drive/download/${file.id}/content`,
        { headers: mkheaders(accessToken, refreshToken) },
      )
      if (res.ok) {
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = file.name
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        setTimeout(() => URL.revokeObjectURL(url), 1000)
      } else {
        setError(`Download failed (${res.status})`)
      }
    } catch (e) {
      setError('Download failed due to network error')
    }
  }

  if (!accessToken) {
    return (
    <div className="mx-auto w-full min-w-0 max-w-7xl space-y-6 bg-background animate-fade-in">
      <div>
        <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-[#26251e]">Google Drive</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your Google Drive files
        </p>
      </div>
      <Card className="shadow-xs">
        <CardContent className="py-16">
          <div className="text-center text-muted-foreground">
            <HardDrive className="h-16 w-16 mx-auto mb-4 opacity-40 text-primary" />
            <h2 className="text-xl font-sans font-normal tracking-[-0.02em] text-foreground mb-2">
              {sessionError ? 'Session expired' : 'Connect Google Drive'}
            </h2>
            <p className="mb-6 max-w-md mx-auto text-sm">
              {sessionError
                ? 'Your Google session expired and could not be refreshed. Sign in again to continue managing your Drive files.'
                : 'Sign in with Google to access, upload, and manage your Drive files directly from this platform.'}
            </p>
            <Button size="lg" className="gap-3 shadow-sm" onClick={() => signIn('google', { callbackUrl: '/drive' })}>
              <LogIn className="h-5 w-5" />
              Sign in with Google
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
    )
  }

  return (
    <div className="mx-auto w-full min-w-0 max-w-7xl space-y-6 bg-background animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="font-sans text-2xl font-normal tracking-[-0.03em] text-[#26251e] sm:text-3xl">Google Drive</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {files.length} file{files.length !== 1 ? 's' : ''} · Connected as {session?.user?.email}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2 sm:gap-3">
          {storage && (
            <div className="text-xs text-muted-foreground self-center">
              {formatBytes(storage.usageInDrive)} / {formatBytes(storage.limit)}
            </div>
          )}
          <Button variant="outline" size="icon" onClick={fetchFiles} disabled={loading} className="h-11 w-11 rounded-[8px] sm:h-10 sm:w-10" aria-label="Refresh Drive files">
            <RefreshCw className={`h-4 w-4 text-muted-foreground ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <label>
            <input
              type="file"
              className="hidden"
              onChange={handleUpload}
              disabled={uploading}
            />
            <Button variant="outline" className="gap-2 h-10 rounded-[8px] cursor-pointer shadow-sm animate-fade-in" disabled={uploading} asChild>
              <span>
                {uploading ? (
                  <Loader2 className="h-4 w-4 animate-spin text-primary" />
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
              <span className="font-medium text-foreground">Uploading to Google Drive...</span>
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

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-[8px]">
          {error}
          <Button variant="link" size="sm" className="ml-2 text-red-700 underline" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {loading && files.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-primary" />
            <p>Loading files from Google Drive...</p>
          </CardContent>
        </Card>
      ) : files.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            <HardDrive className="h-12 w-12 mx-auto mb-3 opacity-40 text-primary" />
            <p className="text-lg font-sans font-normal tracking-[-0.02em] text-foreground">Drive is empty</p>
            <p className="text-sm mt-1">Upload a file to get started</p>
          </CardContent>
        </Card>
      ) : (
        <Card className="shadow-xs overflow-hidden">
          <ScrollArea className="h-[min(600px,65dvh)] min-h-[320px]">
            <div className="divide-y divide-border">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="group flex flex-col items-stretch gap-3 bg-secondary p-3 transition-colors hover:bg-secondary/70 sm:flex-row sm:items-center sm:gap-4 sm:p-4"
                >
                  <div className="hidden shrink-0 rounded-[8px] border border-border bg-card p-2 text-primary sm:block">
                    {file.isFolder ? (
                      <Folder className="h-5 w-5" />
                    ) : file.mimeType.startsWith('image/') ? (
                      <ImageIcon className="h-5 w-5" />
                    ) : file.mimeType.includes('spreadsheet') || file.mimeType.includes('csv') ? (
                      <FileSpreadsheet className="h-5 w-5" />
                    ) : file.mimeType.includes('document') || file.mimeType.includes('pdf') ? (
                      <FileText className="h-5 w-5" />
                    ) : (
                      <File className="h-5 w-5" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm text-foreground truncate">{file.name}</p>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted-foreground">
                      <span>{file.isFolder ? 'Folder' : formatBytes(file.size)}</span>
                      <span>{formatDate(file.modifiedTime)}</span>
                    </div>
                  </div>
                  <div className="flex justify-end gap-1 opacity-100 transition-opacity md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDownload(file)}
                      title="Download"
                      className="h-10 w-10 rounded-[8px] text-muted-foreground hover:bg-card hover:text-foreground cursor-pointer"
                      aria-label={`Download ${file.name}`}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    {file.webViewLink && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => window.open(file.webViewLink, '_blank')}
                        title="Open in Drive"
                        className="h-10 w-10 rounded-[8px] text-muted-foreground hover:bg-card hover:text-foreground cursor-pointer"
                        aria-label={`Open ${file.name} in Drive`}
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(file.id)}
                      title="Delete"
                      className="h-10 w-10 cursor-pointer rounded-[8px] text-[#c64545] hover:bg-[#c64545]/10"
                      aria-label={`Delete ${file.name}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </Card>
      )}

      {storage && (
        <Card className="shadow-xs">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-sans font-normal tracking-[-0.02em] text-foreground flex items-center gap-2">
              <HardDrive className="h-4.5 w-4.5 text-primary" />
              Storage Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Used</span>
                <span className="font-semibold text-foreground">{formatBytes(storage.usageInDrive)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Limit</span>
                <span className="font-semibold text-foreground">{formatBytes(storage.limit)}</span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2 mt-2 border border-border overflow-hidden">
                <div
                  className="bg-primary h-full rounded-full transition-all"
                  style={{ width: `${Math.min((storage.usageInDrive / storage.limit) * 100, 100)}%` }}
                />
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
