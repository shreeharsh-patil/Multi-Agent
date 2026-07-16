'use client'

import { useMemo, useState } from 'react'
import { Maximize2, Minimize2, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

export interface CodeSandboxProps {
  html?: string
  css?: string
  js?: string
  fullHtml?: string
  className?: string
}

function escapeCloser(str: string): string {
  return str.replace(/<\//g, '<\\/')
}

function buildHtmlDocument(html: string, css: string, js: string): string {
  return `<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: system-ui, sans-serif; padding: 16px; }
${css}
</style>
</head>
<body>
${html}
<script>
try {
  ${escapeCloser(js)}
} catch (e) {
  document.body.innerHTML += '<pre style="color:red;margin-top:16px">Runtime Error: ' + e.message + '<\\/pre>';
}
</script>
</body>
</html>`
}

function parseCodeBlocks(text: string): { html: string; css: string; js: string } {
  const result = { html: '', css: '', js: '' }
  const blockRegex = /```(\w+)?\n([\s\S]*?)```/g
  let match: RegExpExecArray | null

  while ((match = blockRegex.exec(text)) !== null) {
    const lang = (match[1] || '').toLowerCase()
    const code = (match[2] ?? '').trim()

    if (lang === 'html' || lang === 'htm') {
      result.html += code + '\n'
    } else if (lang === 'css') {
      result.css += code + '\n'
    } else if (lang === 'js' || lang === 'javascript' || lang === 'jsx') {
      result.js += code + '\n'
    } else if (lang === 'tsx' || lang === 'react') {
      result.js += code + '\n'
    }
  }

  if (!result.html && !result.css && !result.js) {
    result.html = text
  }

  return result
}

function extractCodeFromMessage(content: string): { blocks: { lang: string; code: string }[]; hasCode: boolean } {
  const blocks: { lang: string; code: string }[] = []
  const blockRegex = /```(\w+)?\n([\s\S]*?)```/g
  let match: RegExpExecArray | null

  while ((match = blockRegex.exec(content)) !== null) {
    const lang = (match[1] || '').toLowerCase()
    blocks.push({ lang, code: (match[2] ?? '').trim() })
  }

  return { blocks, hasCode: blocks.length > 0 }
}

export function extractCodeFromContent(content: string): CodeSandboxProps | null {
  const { hasCode } = extractCodeFromMessage(content)
  if (!hasCode) return null

  const parsed = parseCodeBlocks(content)
  const hasRenderableContent = parsed.html.length > 0 || parsed.css.length > 0 || parsed.js.length > 0
  if (!hasRenderableContent) return null

  return parsed
}

export function CodeSandbox({ html = '', css = '', js = '', fullHtml, className = '' }: CodeSandboxProps) {
  const [fullscreen, setFullscreen] = useState(false)
  const [key, setKey] = useState(0)

  const srcdoc = useMemo(() => {
    if (fullHtml) return fullHtml
    return buildHtmlDocument(html, css, js)
  }, [html, css, js, fullHtml])

  const containerClass = fullscreen
    ? 'fixed inset-0 z-50 bg-background p-4'
    : `rounded-lg border overflow-hidden ${className}`

  const iframeHeight = fullscreen ? 'calc(100vh - 80px)' : '400px'

  return (
    <div className={containerClass}>
      <div className="flex items-center justify-between px-3 py-2 bg-muted/50 border-b rounded-t-lg">
        <span className="text-xs font-medium text-muted-foreground">Live Preview</span>
        <div className="flex gap-1">
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setKey(k => k + 1)} title="Refresh">
            <RefreshCw className="h-3 w-3" />
          </Button>
          <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => setFullscreen(!fullscreen)} title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}>
            {fullscreen ? <Minimize2 className="h-3 w-3" /> : <Maximize2 className="h-3 w-3" />}
          </Button>
        </div>
      </div>
      <iframe
        key={key}
        srcDoc={srcdoc}
        sandbox="allow-scripts allow-modals"
        className="w-full bg-white"
        style={{ height: iframeHeight, border: 'none' }}
        title="Code Preview"
      />
    </div>
  )
}

interface CodePreviewButtonProps {
  content: string
  onPreview: (props: CodeSandboxProps) => void
}

export function CodePreviewButton({ content, onPreview }: CodePreviewButtonProps) {
  const previewProps = useMemo(() => extractCodeFromContent(content), [content])
  if (!previewProps) return null

  return (
    <Button
      variant="outline"
      size="sm"
      className="gap-1.5 text-xs h-7"
      onClick={() => onPreview(previewProps)}
    >
      <Maximize2 className="h-3 w-3" />
      Preview
    </Button>
  )
}
