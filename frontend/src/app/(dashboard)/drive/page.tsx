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
  Image,
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
  }, [accessToken])

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
        a.click()
        URL.revokeObjectURL(url)
      }
    } catch (e) {
      setError('Download failed')
    }
  }

  if (!accessToken) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Google Drive</h1>
          <p className="text-muted-foreground mt-1">
            Manage your Google Drive files
          </p>
        </div>
        <Card>
          <CardContent className="py-16">
            <div className="text-center text-muted-foreground">
              <HardDrive className="h-16 w-16 mx-auto mb-4 opacity-30" />
              <h2 className="text-xl font-semibold mb-2">
                {sessionError ? 'Session expired' : 'Connect Google Drive'}
              </h2>
              <p className="mb-6 max-w-md mx-auto">
                {sessionError
                  ? 'Your Google session expired and could not be refreshed. Sign in again to continue managing your Drive files.'
                  : 'Sign in with Google to access, upload, and manage your Drive files directly from this platform.'}
              </p>
              <Button size="lg" className="gap-3" onClick={() => signIn('google', { callbackUrl: '/drive' })}>
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
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Google Drive</h1>
          <p className="text-muted-foreground mt-1">
            {files.length} file{files.length !== 1 ? 's' : ''} · Connected as {session?.user?.email}
          </p>
        </div>
        <div className="flex gap-3">
          {storage && (
            <div className="text-sm text-muted-foreground self-center">
              {formatBytes(storage.usageInDrive)} / {formatBytes(storage.limit)}
            </div>
          )}
          <Button variant="outline" size="icon" onClick={fetchFiles} disabled={loading}>
            <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
          </Button>
          <label>
            <input
              type="file"
              className="hidden"
              onChange={handleUpload}
              disabled={uploading}
            />
           <Button variant="outline" className="gap-2" disabled={uploading} asChild>
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
        <div className="bg-secondary/40 border rounded-xl p-4 space-y-3 shadow-sm animate-in fade-in slide-in-from-top-2 duration-300">
          <div className="flex justify-between items-center text-sm">
            <div className="flex items-center gap-2">
              <Loader2 className="h-4 w-4 animate-spin text-primary" />
              <span className="font-medium">Uploading to Google Drive...</span>
            </div>
            <span className="font-semibold text-primary">{uploadProgress}%</span>
          </div>
          <div className="w-full bg-secondary h-2.5 rounded-full overflow-hidden">
            <div 
              className="bg-gradient-to-r from-primary/80 to-primary h-full transition-all duration-300 ease-out" 
              style={{ width: `${uploadProgress}%` }}
            />
          </div>
        </div>
      )}

      {error && (
        <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-lg">
          {error}
          <Button variant="link" size="sm" className="ml-2" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      {loading && files.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3" />
            <p>Loading files from Google Drive...</p>
          </CardContent>
        </Card>
      ) : files.length === 0 ? (
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            <HardDrive className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-lg font-medium">Drive is empty</p>
            <p className="text-sm mt-1">Upload a file to get started</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <ScrollArea className="h-[600px]">
            <div className="divide-y">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-4 p-4 hover:bg-secondary/50 transition-colors group"
                >
                  <div className="p-2 rounded-lg bg-secondary shrink-0">
                    {file.isFolder ? (
                      <Folder className="h-5 w-5 text-amber-500" />
                    ) : file.mimeType.startsWith('image/') ? (
                      <Image className="h-5 w-5 text-purple-500" />
                    ) : file.mimeType.includes('spreadsheet') || file.mimeType.includes('csv') ? (
                      <FileSpreadsheet className="h-5 w-5 text-green-500" />
                    ) : file.mimeType.includes('document') || file.mimeType.includes('pdf') ? (
                      <FileText className="h-5 w-5 text-blue-500" />
                    ) : (
                      <File className="h-5 w-5 text-muted-foreground" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium truncate">{file.name}</p>
                    <div className="flex items-center gap-3 text-sm text-muted-foreground">
                      <span>{file.isFolder ? 'Folder' : formatBytes(file.size)}</span>
                      <span>{formatDate(file.modifiedTime)}</span>
                    </div>
                  </div>
                  <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDownload(file)}
                      title="Download"
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    {file.webViewLink && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => window.open(file.webViewLink, '_blank')}
                        title="Open in Drive"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(file.id)}
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </Card>
      )}

      {storage && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center gap-2">
              <HardDrive className="h-4 w-4" />
              Storage
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Used</span>
                <span className="font-medium">{formatBytes(storage.usageInDrive)}</span>
              </div>
              <div className="flex justify-between text-sm">
                <span className="text-muted-foreground">Limit</span>
                <span className="font-medium">{formatBytes(storage.limit)}</span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2 mt-2">
                <div
                  className="bg-primary h-2 rounded-full transition-all"
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
