'use client'

import React, { useState } from 'react'
import { Download, Maximize2, X, RefreshCw } from 'lucide-react'
import { downloadSecureFile } from '@/lib/download'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

interface ImagePreviewCardProps {
  src: string
  alt?: string
}

export const ImagePreviewCard = React.memo(function ImagePreviewCard({ src, alt = 'Generated Image' }: ImagePreviewCardProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [hasError, setHasError] = useState(false)
  const [retryCount, setRetryCount] = useState(0)
  const imgRef = React.useRef<HTMLImageElement>(null)

  const imageSrc = React.useMemo(() => {
    let s = src?.trim() || ''
    if (s.startsWith('/api/')) {
      s = `${BACKEND_URL}${s}`
    }
    if (s.includes('/api/documents/') && s.includes('/download')) {
      s = s.replace('/download', '/file')
    }
    s = s.replace(/[?&]download=true/g, '')
    if (retryCount > 0) {
      s += (s.includes('?') ? '&' : '?') + `retry=${retryCount}`
    }
    return s
  }, [src, retryCount])

  React.useEffect(() => {
    setIsLoading(true)
    setHasError(false)
    if (imgRef.current?.complete && imgRef.current.naturalWidth > 0) {
      setIsLoading(false)
    }
  }, [imageSrc])

  const handleDownload = (e: React.MouseEvent) => {
    e.preventDefault()
    e.stopPropagation()
    downloadSecureFile(imageSrc, 'generated-image.png')
  }

  return (
    <>
      {/* ChatGPT Style Inline Image Card */}
      <div className="relative group my-4 max-w-md overflow-hidden rounded-xl border border-border/80 bg-card shadow-sm transition-all hover:shadow-md min-h-[220px]">
        {/* Loading Skeleton */}
        {isLoading && !hasError && (
          <div className="absolute inset-0 flex items-center justify-center bg-muted/30 animate-pulse min-h-[220px]">
            <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
          </div>
        )}

        {hasError ? (
          <div className="flex flex-col items-center justify-center p-6 bg-muted/20 text-center min-h-[220px] gap-2">
            <p className="text-xs text-muted-foreground font-medium">Image preview loading issue</p>
            <div className="flex items-center gap-2 mt-2">
              <button
                type="button"
                onClick={() => {
                  setHasError(false)
                  setIsLoading(true)
                  setRetryCount((prev) => prev + 1)
                }}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary text-secondary-foreground text-xs font-medium hover:bg-secondary/80 transition-colors"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Retry Loading</span>
              </button>
              <button
                type="button"
                onClick={handleDownload}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Download File</span>
              </button>
            </div>
          </div>
        ) : (
          <img
            ref={imgRef}
            src={imageSrc}
            alt={alt}
            onLoad={() => {
              setIsLoading(false)
              setHasError(false)
            }}
            onError={() => {
              setIsLoading(false)
              setHasError(true)
            }}
            onClick={() => setIsOpen(true)}
            className={`w-full h-auto max-h-[420px] object-cover cursor-pointer transition-transform duration-300 group-hover:scale-[1.02] ${
              isLoading ? 'opacity-0' : 'opacity-100'
            }`}
          />
        )}

        {/* Hover Overlay Actions */}
        <div className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex items-center justify-center gap-3 pointer-events-none group-hover:pointer-events-auto">
          <button
            onClick={() => setIsOpen(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-background/90 text-foreground text-xs font-medium backdrop-blur-md shadow-sm hover:bg-background transition-colors cursor-pointer"
            title="Expand Preview"
          >
            <Maximize2 className="h-3.5 w-3.5" />
            <span>Expand</span>
          </button>
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium shadow-sm hover:bg-primary/90 transition-colors cursor-pointer"
            title="Download Image"
          >
            <Download className="h-3.5 w-3.5" />
            <span>Download</span>
          </button>
        </div>
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
                onClick={handleDownload}
                className="p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors cursor-pointer"
                title="Download"
              >
                <Download className="h-5 w-5" />
              </button>
              <button
                onClick={() => setIsOpen(false)}
                className="p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors cursor-pointer"
                title="Close"
              >
                <X className="h-5 w-5" />
              </button>
            </div>

            {/* High Res Image */}
            <img
              src={src}
              alt={alt}
              className="max-h-[82vh] w-auto max-w-full rounded-xl object-contain shadow-2xl border border-white/10"
            />
          </div>
        </div>
      )}
    </>
  )
})
