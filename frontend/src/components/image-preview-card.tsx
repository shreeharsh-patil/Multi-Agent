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
      <div className="relative group my-4 max-w-md overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm transition-all hover:shadow-md min-h-[220px]">
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
          <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-3 pointer-events-none group-hover:pointer-events-auto">
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
      </div>

      {/* ChatGPT Style Fullscreen Lightbox Modal */}
      {isOpen && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/85 backdrop-blur-md p-4 animate-fade-in"
          onClick={() => setIsOpen(false)}
        >
          <div
            className="relative max-w-4xl w-full max-h-[90vh] flex flex-col items-center justify-center"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Top Modal Toolbar */}
            <div className="absolute top-[-44px] right-0 flex items-center gap-2">
              <button
                type="button"
                onClick={handleDownload}
                className="p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors cursor-pointer"
                title="Download"
              >
                <Download className="h-5 w-5" />
              </button>
              <button
                type="button"
                onClick={() => setIsOpen(false)}
                className="p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors cursor-pointer"
                title="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* High Res Image */}
            <img
              src={activeImageSrc}
              alt={alt}
              className="max-h-[82vh] w-auto max-w-full rounded-xl object-contain shadow-2xl border border-white/10"
            />
          </div>
        </div>
      )}
    </>
  )
})
