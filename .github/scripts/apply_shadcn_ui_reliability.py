from pathlib import Path
import re


def read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding='utf-8')


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if old not in text:
        raise RuntimeError(f'missing expected block: {label}')
    return text.replace(old, new, 1)


# Sidebar: replace hand-rolled mobile dialog behavior with shadcn Sheet,
# use shared inputs/skeletons, and replace browser confirm() with an accessible dialog.
path = 'frontend/src/components/sidebar.tsx'
text = read(path)
text = replace_once(
    text,
    "import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'",
    "import React, { useState, useEffect, useCallback, useMemo } from 'react'",
    'sidebar react imports',
)
text = replace_once(
    text,
    "import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'\nimport { openCommandPalette } from '@/components/command-palette'",
    "import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'\nimport { Button } from '@/components/ui/button'\nimport { Input } from '@/components/ui/input'\nimport { Skeleton } from '@/components/ui/skeleton'\nimport { Sheet, SheetContent, SheetDescription, SheetTitle } from '@/components/ui/sheet'\nimport { ConfirmDialog } from '@/components/confirm-dialog'\nimport { toast } from 'sonner'\nimport { openCommandPalette } from '@/components/command-palette'",
    'sidebar shadcn imports',
)
text = text.replace("  const mobileDrawerRef = useRef<HTMLElement>(null)\n", '')
text = replace_once(
    text,
    "  const [renameText, setRenameText] = useState('')\n  const [activeWorkspace, setActiveWorkspace] = useState('all')",
    "  const [renameText, setRenameText] = useState('')\n  const [pendingDelete, setPendingDelete] = useState<SidebarConversation | null>(null)\n  const [deletingConversation, setDeletingConversation] = useState(false)\n  const [activeWorkspace, setActiveWorkspace] = useState('all')",
    'sidebar delete state',
)
text = re.sub(
    r"\n  useEffect\(\(\) => \{\n    if \(!mobileMenuOpen\) return\n.*?\n  \}, \[mobileMenuOpen, setMobileMenuOpen\]\)\n",
    "\n",
    text,
    count=1,
    flags=re.S,
)
old_delete = '''  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    if (confirm('Delete this conversation?')) {
      const res = await api.chat.deleteConversation(id)
      if (res.success) {
        setConversations(prev => prev.filter(c => c.id !== id))
        if (pathname === `/chat` || pathname.startsWith(`/chat/`)) {
          router.push('/chat')
        }
      } else {
        console.error('Failed to delete conversation:', res.error)
      }
    }
  }
'''
new_delete = '''  const handleDeleteConversation = (conversation: SidebarConversation, e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    setPendingDelete(conversation)
  }

  const confirmDeleteConversation = async () => {
    if (!pendingDelete || deletingConversation) return
    setDeletingConversation(true)
    const id = pendingDelete.id
    try {
      const res = await api.chat.deleteConversation(id)
      if (!res.success) {
        throw new Error(res.error || 'Failed to delete conversation')
      }
      setConversations(prev => prev.filter(c => c.id !== id))
      setPendingDelete(null)
      if (pathname === '/chat' || pathname.startsWith('/chat/')) {
        router.push('/chat')
      }
      toast.success('Conversation deleted')
    } catch (error) {
      console.error('Failed to delete conversation:', error)
      toast.error(error instanceof Error ? error.message : 'Failed to delete conversation')
    } finally {
      setDeletingConversation(false)
    }
  }
'''
text = replace_once(text, old_delete, new_delete, 'sidebar delete handler')
text = text.replace("onClick={(e) => handleDeleteConversation(conv.id, e)}", "onClick={(e) => handleDeleteConversation(conv, e)}")
text = replace_once(
    text,
    '''                  <input
                    type="text"
                    value={renameText}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => setRenameText(e.target.value)}
                    onBlur={() => saveRename(conv.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') { e.preventDefault(); saveRename(conv.id) }
                      else if (e.key === 'Escape') { e.preventDefault(); cancelRename() }
                    }}
                    className="w-full bg-background border border-border rounded px-1.5 py-0.5 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                  />''',
    '''                  <Input
                    value={renameText}
                    autoFocus
                    onClick={(e) => e.stopPropagation()}
                    onChange={(e) => setRenameText(e.target.value)}
                    onBlur={() => saveRename(conv.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') { e.preventDefault(); saveRename(conv.id) }
                      else if (e.key === 'Escape') { e.preventDefault(); cancelRename() }
                    }}
                    className="h-8 w-full text-xs"
                    aria-label={`Rename ${conv.title}`}
                  />''',
    'sidebar rename input',
)
text = replace_once(
    text,
    '''                <input
                  type="text"
                  value={conversationSearch}
                  onChange={(e) => setConversationSearch(e.target.value)}
                  placeholder="Search chats..."
                  className="w-full h-8 pl-8 pr-2 rounded-[8px] bg-card border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                />''',
    '''                <Input
                  value={conversationSearch}
                  onChange={(e) => setConversationSearch(e.target.value)}
                  placeholder="Search chats..."
                  className="h-8 bg-card pl-8 text-xs"
                  aria-label="Search conversations"
                />''',
    'sidebar history search input',
)
text = text.replace('text-[#26251e]', 'text-foreground')
text = replace_once(
    text,
    '''              {loadingDocuments ? (
                <div className="flex items-center justify-center py-4">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
                </div>
              ) : documents.length === 0 ? (''',
    '''              {loadingDocuments ? (
                <div className="space-y-2 px-2 py-2" aria-label="Loading documents">
                  <Skeleton className="h-8 w-full" />
                  <Skeleton className="h-8 w-4/5" />
                  <Skeleton className="h-8 w-11/12" />
                </div>
              ) : documents.length === 0 ? (''',
    'sidebar document skeleton',
)
old_mobile = '''      {/* Mobile Drawer (Fixed Overlay — Never affects or shrinks background layout) */}
      {mobileMenuOpen && (
        <>
          <div 
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
            aria-hidden="true"
          />
          <aside
            ref={mobileDrawerRef}
            role="dialog"
            aria-modal="true"
            aria-label="Navigation menu"
            tabIndex={-1}
            className="fixed inset-y-0 left-0 z-50 flex h-screen h-[100svh] supports-[height:100dvh]:h-dvh w-[min(85vw,280px)] flex-col overflow-hidden border-r border-border bg-secondary pb-[env(safe-area-inset-bottom)] pt-[env(safe-area-inset-top)] shadow-2xl outline-none animate-in slide-in-from-left duration-200 lg:hidden"
          >
            {renderSidebarContent(true)}
          </aside>
        </>
      )}
'''
new_mobile = '''      {/* Accessible mobile navigation powered by the shadcn Sheet pattern. */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent
          side="left"
          showCloseButton={false}
          className="flex h-[100dvh] w-[min(88vw,300px)] max-w-[300px] flex-col overflow-hidden border-r border-border bg-secondary p-0 pb-[env(safe-area-inset-bottom)] pt-[env(safe-area-inset-top)] lg:hidden"
        >
          <SheetTitle className="sr-only">Navigation menu</SheetTitle>
          <SheetDescription className="sr-only">Navigate Agentic, search conversations, and open workspace tools.</SheetDescription>
          {renderSidebarContent(true)}
        </SheetContent>
      </Sheet>
'''
text = replace_once(text, old_mobile, new_mobile, 'sidebar mobile sheet')
text = replace_once(
    text,
    '''      </aside>
    </>
  )
}''',
    '''      </aside>

      <ConfirmDialog
        open={Boolean(pendingDelete)}
        onOpenChange={(open) => { if (!open && !deletingConversation) setPendingDelete(null) }}
        title="Delete conversation?"
        description={pendingDelete ? `This will permanently delete “${pendingDelete.title}”. This action cannot be undone.` : 'This action cannot be undone.'}
        confirmLabel="Delete"
        destructive
        loading={deletingConversation}
        onConfirm={confirmDeleteConversation}
      />
    </>
  )
}''',
    'sidebar confirmation dialog',
)
write(path, text)


# Top bar: remove the non-functional notification control and provide a useful mobile brand target.
path = 'frontend/src/components/top-bar.tsx'
text = read(path)
text = text.replace('  Bell,\n', '')
text = replace_once(
    text,
    '''      </div>\n\n\n\n      {/* Right Side Header Items */}''',
    '''      </div>\n\n      <Link href="/dashboard" className="min-w-0 flex-1 truncate px-1 text-sm font-semibold tracking-tight text-foreground" aria-label="Go to dashboard">\n        Agentic\n      </Link>\n\n      {/* Right Side Header Items */}''',
    'topbar mobile brand',
)
text = re.sub(
    r'''\n        <Button variant="ghost" size="icon" className="relative hidden h-11 w-11 rounded-lg text-muted-foreground hover:bg-accent min-\[360px\]:inline-flex" aria-label="Notifications" title="Notifications">\n          <Bell.*?</Button>\n''',
    '\n',
    text,
    count=1,
    flags=re.S,
)
write(path, text)


# Image preview: replace the hand-rolled lightbox with shadcn Dialog and standard buttons.
path = 'frontend/src/components/image-preview-card.tsx'
text = read(path)
text = replace_once(
    text,
    "import { Download, Maximize2, X, RefreshCw, AlertCircle } from 'lucide-react'",
    "import { Download, Maximize2, RefreshCw, AlertCircle } from 'lucide-react'\nimport { Button } from '@/components/ui/button'\nimport { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'",
    'image preview shadcn imports',
)
text = text.replace(
'''              <button
                type="button"
                onClick={handleRetry}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-secondary text-secondary-foreground text-xs font-medium hover:bg-secondary/80 transition-colors cursor-pointer"
              >
                <RefreshCw className="h-3.5 w-3.5" />
                <span>Retry Loading</span>
              </button>''',
'''              <Button type="button" variant="secondary" size="sm" onClick={handleRetry}>
                <RefreshCw className="h-3.5 w-3.5" />
                Retry Loading
              </Button>''')
text = text.replace(
'''              <button
                type="button"
                onClick={handleDownload}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors cursor-pointer"
              >
                <Download className="h-3.5 w-3.5" />
                <span>Download File</span>
              </button>''',
'''              <Button type="button" size="sm" onClick={handleDownload}>
                <Download className="h-3.5 w-3.5" />
                Download File
              </Button>''')
old_modal = '''      {/* ChatGPT Style Fullscreen Lightbox Modal */}
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
      )}'''
new_modal = '''      <Dialog open={isOpen} onOpenChange={setIsOpen}>
        <DialogContent
          className="flex h-[min(92dvh,900px)] max-w-5xl items-center justify-center border-white/10 bg-black/90 p-3 text-white sm:p-5"
          showCloseButton
        >
          <DialogTitle className="sr-only">{alt}</DialogTitle>
          <DialogDescription className="sr-only">Full-size generated image preview.</DialogDescription>
          <Button
            type="button"
            variant="secondary"
            size="icon"
            onClick={handleDownload}
            className="absolute right-14 top-3 z-10 rounded-full bg-white/10 text-white hover:bg-white/20 hover:text-white"
            aria-label="Download image"
            title="Download image"
          >
            <Download className="h-5 w-5" />
          </Button>
          <img
            src={activeImageSrc}
            alt={alt}
            className="max-h-full w-auto max-w-full rounded-xl border border-white/10 object-contain shadow-2xl"
          />
        </DialogContent>
      </Dialog>'''
text = replace_once(text, old_modal, new_modal, 'image dialog')
write(path, text)

print('shadcn UI reliability patch applied')
