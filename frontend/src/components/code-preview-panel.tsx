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
    <div className="fixed inset-y-0 right-0 z-40 w-full sm:w-[600px] lg:w-[720px] bg-background border-l shadow-xl flex flex-col animate-in slide-in-from-right">
      <div className="flex items-center justify-between px-4 py-3 border-b">
        <h2 className="text-sm font-semibold">Code Preview</h2>
        <Button variant="ghost" size="icon" className="h-8 w-8" onClick={onClose}>
          <X className="h-4 w-4" />
        </Button>
      </div>
      <div className="flex-1 overflow-auto p-4">
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
