'use client'

import { X } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { CodeSandbox, type CodeSandboxProps } from '@/components/code-sandbox'

interface CodePreviewPanelProps {
  preview: CodeSandboxProps | null
  onClose: () => void
}

export function CodePreviewPanel({ preview, onClose }: CodePreviewPanelProps) {
  if (!preview) return null

  return (
    <div className="fixed inset-y-0 right-0 z-40 flex h-screen h-[100svh] supports-[height:100dvh]:h-dvh w-full max-w-full flex-col border-l bg-background pb-[env(safe-area-inset-bottom)] shadow-xl animate-in slide-in-from-right sm:w-[min(600px,100vw)] lg:w-[min(720px,100vw)]" role="dialog" aria-modal="true" aria-label="Code preview" onClick={(event) => event.stopPropagation()}>
      <div className="flex min-h-14 items-center justify-between border-b px-3 pb-2 pt-[max(0.5rem,env(safe-area-inset-top))] sm:px-4 sm:py-3">
        <h2 className="text-sm font-semibold">Code Preview</h2>
        <Button variant="ghost" size="icon" className="h-11 w-11" onClick={onClose} aria-label="Close code preview" title="Close code preview">
          <X className="h-4 w-4" />
        </Button>
      </div>
      <div className="min-h-0 min-w-0 flex-1 overflow-auto p-2 sm:p-4">
        <CodeSandbox
          html={preview.html}
          css={preview.css}
          js={preview.js}
          fullHtml={preview.fullHtml}
        />
      </div>
    </div>
  )
}
