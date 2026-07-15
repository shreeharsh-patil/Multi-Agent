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
      <div className="space-y-6 animate-fade-in bg-[#faf9f5]">
        <div>
          <h1 className="text-3xl font-serif font-normal text-[#141413]">Google Drive</h1>
          <p className="text-sm text-[#6c6a64] mt-1">
            Manage your Google Drive files
          </p>
        </div>
        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardContent className="py-16">
            <div className="text-center text-[#6c6a64]">
              <HardDrive className="h-16 w-16 mx-auto mb-4 opacity-40 text-[#cc785c]" />
              <h2 className="text-xl font-serif font-normal text-[#141413] mb-2">
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
    <div className="space-y-6 animate-fade-in bg-[#faf9f5]">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-serif font-normal text-[#141413]">Google Drive</h1>
          <p className="text-sm text-[#6c6a64] mt-1">
            {files.length} file{files.length !== 1 ? 's' : ''} · Connected as {session?.user?.email}
          </p>
        </div>
        <div className="flex gap-3 items-center">
          {storage && (
            <div className="text-xs text-[#6c6a64] self-center">
              {formatBytes(storage.usageInDrive)} / {formatBytes(storage.limit)}
            </div>
          )}
          <Button variant="outline" size="icon" onClick={fetchFiles} disabled={loading} className="h-10 w-10 rounded-[8px]">
            <RefreshCw className={`h-4 w-4 text-[#6c6a64] ${loading ? 'animate-spin' : ''}`} />
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
                  <Loader2 className="h-4 w-4 animate-spin text-[#cc785c]" />
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
              <span className="font-medium text-[#141413]">Uploading to Google Drive...</span>
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

      {loading && files.length === 0 ? (
        <Card className="border-[#e6dfd8] bg-[#efe9de]">
          <CardContent className="py-16 text-center text-[#6c6a64]">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-[#cc785c]" />
            <p>Loading files from Google Drive...</p>
          </CardContent>
        </Card>
      ) : files.length === 0 ? (
        <Card className="border-[#e6dfd8] bg-[#efe9de]">
          <CardContent className="py-16 text-center text-[#6c6a64]">
            <HardDrive className="h-12 w-12 mx-auto mb-3 opacity-40 text-[#cc785c]" />
            <p className="text-lg font-serif font-normal text-[#141413]">Drive is empty</p>
            <p className="text-sm mt-1">Upload a file to get started</p>
          </CardContent>
        </Card>
      ) : (
        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs overflow-hidden">
          <ScrollArea className="h-[600px]">
            <div className="divide-y divide-[#e6dfd8]">
              {files.map((file) => (
                <div
                  key={file.id}
                  className="flex items-center gap-4 p-4 bg-[#faf9f5] hover:bg-[#efe9de]/50 transition-colors group"
                >
                  <div className="p-2 rounded-[8px] bg-[#efe9de] text-[#cc785c] border border-[#e6dfd8] shrink-0">
                    {file.isFolder ? (
                      <Folder className="h-5 w-5" />
                    ) : file.mimeType.startsWith('image/') ? (
                      <Image className="h-5 w-5" />
                    ) : file.mimeType.includes('spreadsheet') || file.mimeType.includes('csv') ? (
                      <FileSpreadsheet className="h-5 w-5" />
                    ) : file.mimeType.includes('document') || file.mimeType.includes('pdf') ? (
                      <FileText className="h-5 w-5" />
                    ) : (
                      <File className="h-5 w-5" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-sm text-[#141413] truncate">{file.name}</p>
                    <div className="flex items-center gap-3 text-xs text-[#6c6a64] mt-0.5">
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
                      className="rounded-[8px] hover:bg-[#efe9de] text-[#6c6a64] hover:text-[#141413] h-8 w-8"
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    {file.webViewLink && (
                      <Button
                        variant="ghost"
                        size="icon"
                        onClick={() => window.open(file.webViewLink, '_blank')}
                        title="Open in Drive"
                        className="rounded-[8px] hover:bg-[#efe9de] text-[#6c6a64] hover:text-[#141413] h-8 w-8"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="icon"
                      onClick={() => handleDelete(file.id)}
                      title="Delete"
                      className="rounded-[8px] hover:bg-[#efe9de] text-[#c64545] hover:bg-[#c64545]/10 h-8 w-8"
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
        <Card className="border-[#e6dfd8] bg-[#efe9de] shadow-xs">
          <CardHeader className="pb-3">
            <CardTitle className="text-base font-serif font-normal text-[#141413] flex items-center gap-2">
              <HardDrive className="h-4.5 w-4.5 text-[#cc785c]" />
              Storage Status
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2 text-xs">
              <div className="flex justify-between">
                <span className="text-[#6c6a64]">Used</span>
                <span className="font-semibold text-[#141413]">{formatBytes(storage.usageInDrive)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-[#6c6a64]">Limit</span>
                <span className="font-semibold text-[#141413]">{formatBytes(storage.limit)}</span>
              </div>
              <div className="w-full bg-[#faf9f5] rounded-full h-2 mt-2 border border-[#e6dfd8] overflow-hidden">
                <div
                  className="bg-[#cc785c] h-full rounded-full transition-all"
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
