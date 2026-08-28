'use client'

import React, { useState, useEffect, useRef, useMemo } from 'react'
import { Download, Maximize2, X, RefreshCw, AlertCircle } from 'lucide-react'
import { downloadSecureFile } from '@/lib/download'
import { getAccessToken } from '@/lib/auth-store'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

interface ImagePreviewCardProps {
  src: string
  alt?: string
}

export const ImagePreviewCard = React.memo(function ImagePreviewCard({ src, alt = 'Generated Image' }: ImagePreviewCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [blobUrl, setBlobUrl] = useState<string | null>(null)
  const [retryCount, setRetryCount] = useState(0)
  const imgRef = useRef<HTMLImageElement>(null)

  // Compute canonical image source with backend host resolution
  const resolvedSrc = useMemo(() => {
    let s = src?.trim() || ''
    if (!s) return ''

    // Convert relative API paths to absolute backend URLs
    if (s.startsWith('/api/')) {
      s = `${BACKEND_URL}${s}`
    }

    // Map legacy /download endpoint to inline /file endpoint
    if (s.includes('/api/documents/') && s.includes('/download')) {
      s = s.replace('/download', '/file')
    }

    // Strip attachment query parameters
    s = s.replace(/[?&]download=true/g, '')

    return s
  }, [src])

  // Final image URL prioritizing local Blob URL over raw resolved URL
  const activeImageSrc = useMemo(() => {
    if (blobUrl) return blobUrl
    if (retryCount > 0 && resolvedSrc) {
      return `${resolvedSrc}${resolvedSrc.includes('?') ? '&' : '?'}retry=${retryCount}`
    }
    return resolvedSrc
  }, [blobUrl, resolvedSrc, retryCount])

  // Clean up Blob URLs to prevent memory leaks
  useEffect(() => {
    return () => {
      if (blobUrl && blobUrl.startsWith('blob:')) {
        URL.revokeObjectURL(blobUrl)
      }
    }
  }, [blobUrl])

  // Reset states when source changes or user triggers a manual retry
  useEffect(() => {
    setIsLoading(true)
    setHasError(false)
    setErrorMessage('')
    setBlobUrl(null)

    // Check if the image element was already cached by the browser
    if (imgRef.current?.complete && imgRef.current.naturalWidth > 0) {
      setIsLoading(false)
    }
  }, [resolvedSrc, retryCount])

  // Fallback handler to fetch the image via secure fetch and create a Blob URL
  const tryBlobFallback = async () => {
    if (!resolvedSrc) return false
    try {
      const headers: Record<string, string> = {}
      const token = getAccessToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }

      const response = await fetch(resolvedSrc, { headers })
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const blob = await response.blob()

      if (!blob || blob.size === 0) {
        throw new Error('Received 0-byte image file')
      }

      const newBlobUrl = URL.createObjectURL(blob)
      setBlobUrl(newBlobUrl)
      setHasError(false)
      setIsLoading(false)
      return true
    } catch (err: any) {
      console.warn('Blob fallback failed for image:', resolvedSrc, err)
      setErrorMessage(err.message || 'Unable to load image')
      return false
    }
  }

  const handleImageError = async () => {
    // If direct <img src> failed, attempt secure fetch Blob fallback
    if (!blobUrl) {
      const blobSuccess = await tryBlobFallback()
      if (blobSuccess) return
    }

    setIsLoading(false)
    setHasError(true)
  }

  const handleDownload = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    downloadSecureFile(activeImageSrc || resolvedSrc, 'generated-image.png')
  }

  const handleRetry = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setHasError(false)
    setIsLoading(true)
    setBlobUrl(null)
    setRetryCount((prev) => prev + 1)
  }

  return (
    <>
      {/* ChatGPT Style Inline Image Card */}
      <div className="group relative my-4 min-h-[180px] w-full min-w-0 max-w-md overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm transition-all hover:shadow-md sm:min-h-[220px]">
        {/* Loading Skeleton Spinner */}
        {isLoading && !hasError && (
          <div className="absolute inset-0 z-10 flex items-center justify-center bg-muted/30 backdrop-blur-[2px] animate-pulse min-h-[220px]">
            <div className="flex flex-col items-center gap-2">
              <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
              <span className="text-[11px] text-muted-foreground font-medium">Loading image preview...</span>
            </div>
          </div>
        )}

        {/* Error Fallback Card */}
        {hasError ? (
          <div className="flex flex-col items-center justify-center p-6 bg-muted/20 text-center min-h-[220px] gap-2">
            <AlertCircle className="h-8 w-8 text-amber-500/80 mb-1" />
            <p className="text-xs text-foreground font-medium">Image preview loading issue</p>
            {errorMessage && (
              <p className="text-[11px] text-muted-foreground max-w-xs">{errorMessage}</p>
            )}
            <div className="flex items-center gap-2 mt-2">
              <button
                type="button"
                onClick={handleRetry}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary text-secondary-foreground text-xs font-medium hover:bg-secondary/80 transition-colors cursor-pointer"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Retry Loading</span>
              </button>
              <button
                type="button"
                onClick={handleDownload}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors cursor-pointer"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Download File</span>
              </button>
            </div>
          </div>
        ) : (
          <img
            ref={imgRef}
            src={activeImageSrc}
            alt={alt}
            onLoad={() => {
              setIsLoading(false)
              setHasError(false)
            }}
            onError={handleImageError}
            onClick={() => setIsOpen(true)}
            className="w-full h-auto max-h-[420px] object-cover cursor-pointer transition-transform duration-300 group-hover:scale-[1.01] rounded-xl block"
          />
        )}

        {/* Hover Overlay Actions */}
        {!hasError && !isLoading && (
          <div className="absolute inset-0 hidden items-center justify-center gap-3 bg-black/40 opacity-0 transition-opacity duration-200 pointer-events-none group-hover:opacity-100 group-hover:pointer-events-auto md:flex">
            <button
              type="button"
              onClick={() => setIsOpen(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-background/90 text-foreground text-xs font-medium backdrop-blur-md shadow-sm hover:bg-background transition-colors cursor-pointer"
              title="Expand Preview"
            >
              <Maximize2 className="h-3.5 w-3.5" />
              <span>Expand</span>
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium shadow-sm hover:bg-primary/90 transition-colors cursor-pointer"
              title="Download Image"
            >
              <Download className="h-3.5 w-3.5" />
              <span>Download</span>
            </button>
          </div>
        )}
        {!hasError && !isLoading && (
          <div className="flex items-center justify-end gap-2 border-t border-border bg-card p-2 md:hidden">
            <button
              type="button"
              onClick={() => setIsOpen(true)}
              className="flex min-h-11 items-center gap-1.5 rounded-lg px-3 text-xs font-medium text-foreground hover:bg-secondary"
            >
              <Maximize2 className="h-4 w-4" /> Expand
            </button>
            <button
              type="button"
              onClick={handleDownload}
              className="flex min-h-11 items-center gap-1.5 rounded-lg bg-primary px-3 text-xs font-medium text-primary-foreground"
            >
              <Download className="h-4 w-4" /> Download
            </button>
          </div>
        )}
      </div>

      {/* ChatGPT Style Fullscreen Lightbox Modal */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex h-screen h-[100svh] supports-[height:100dvh]:h-dvh items-center justify-center bg-black/85 p-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-[max(3.5rem,env(safe-area-inset-top))] backdrop-blur-md animate-fade-in sm:p-4"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="relative flex h-full max-h-full w-full max-w-4xl min-w-0 flex-col items-center justify-center"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Top Modal Toolbar */}
            <div className="absolute right-0 top-0 z-10 flex items-center gap-2">
              <button
                type="button"
                onClick={handleDownload}
                className="flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20 cursor-pointer"
                title="Download"
                aria-label="Download image"
              >
                <Download className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-white transition-colors hover:bg-white/20 cursor-pointer"
                title="Close"
                aria-label="Close image preview"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* High Res Image */}
            <img
              src={activeImageSrc}
              alt={alt}
              className="max-h-full w-auto max-w-full rounded-xl border border-white/10 object-contain shadow-2xl"
            />
          </div>
        </div>
      )}
    </>
  )
})
