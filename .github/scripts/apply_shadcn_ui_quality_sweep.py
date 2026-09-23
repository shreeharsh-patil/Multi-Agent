from pathlib import Path
import re


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def write(path: str, text: str) -> None:
    Path(path).write_text(text, encoding="utf-8")


def replace_once(path: str, old: str, new: str, label: str) -> None:
    text = read(path)
    if new in text:
        print(f"already applied: {label}")
        return
    if old not in text:
        raise RuntimeError(f"missing expected block for {label}: {path}")
    write(path, text.replace(old, new, 1))
    print(f"applied: {label}")


def regex_once(path: str, pattern: str, repl: str, label: str, flags: int = 0) -> None:
    text = read(path)
    new_text, count = re.subn(pattern, repl, text, count=1, flags=flags)
    if count != 1:
        raise RuntimeError(f"expected one match for {label}, got {count}: {path}")
    write(path, new_text)
    print(f"applied: {label}")


# 1) Accessibility: never disable user zoom on mobile.
replace_once(
    "frontend/src/app/layout.tsx",
    "  initialScale: 1,\n  maximumScale: 1,\n  userScalable: false,\n",
    "  initialScale: 1,\n",
    "allow browser zoom",
)
replace_once(
    "frontend/src/app/layout.tsx",
    '<Toaster richColors position="top-right" />',
    '<Toaster richColors closeButton position="top-right" />',
    "make toasts dismissible",
)

# 2) Shared dashboard shell: width/overscroll safety + skip-link target.
replace_once(
    "frontend/src/components/dashboard-content.tsx",
    "        'min-h-0 min-w-0 flex-1 bg-background',",
    "        'min-h-0 min-w-0 w-full flex-1 bg-background overscroll-contain',",
    "dashboard content containment",
)
replace_once(
    "frontend/src/components/dashboard-content.tsx",
    "    <main\n      className={cn(",
    "    <main\n      id=\"dashboard-main\"\n      tabIndex={-1}\n      className={cn(",
    "dashboard main landmark",
)
replace_once(
    "frontend/src/app/(dashboard)/layout.tsx",
    '      <div className="flex h-screen h-[100svh] supports-[height:100dvh]:h-dvh min-h-0 min-w-0 overflow-hidden bg-background text-foreground font-sans">\n        <Sidebar />',
    '      <div className="flex h-screen h-[100svh] supports-[height:100dvh]:h-dvh min-h-0 min-w-0 overflow-hidden bg-background text-foreground font-sans">\n        <a href="#dashboard-main" className="sr-only fixed left-3 top-3 z-[100] rounded-md bg-card px-3 py-2 text-sm font-medium text-foreground shadow-lg ring-1 ring-border focus:not-sr-only">Skip to content</a>\n        <Sidebar />',
    "keyboard skip link",
)

# 3) Sidebar: use shadcn Sheet/Dialog/Skeleton for resilient mobile navigation,
# accessible deletion confirmation, and non-jumpy loading placeholders.
replace_once(
    "frontend/src/components/sidebar.tsx",
    "import React, { useState, useEffect, useCallback, useMemo, useRef } from 'react'",
    "import React, { useState, useEffect, useCallback, useMemo } from 'react'",
    "remove manual drawer ref",
)
replace_once(
    "frontend/src/components/sidebar.tsx",
    "import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'\nimport { openCommandPalette } from '@/components/command-palette'",
    "import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'\nimport { Button } from '@/components/ui/button'\nimport { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'\nimport { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'\nimport { Skeleton } from '@/components/ui/skeleton'\nimport { openCommandPalette } from '@/components/command-palette'\nimport { toast } from 'sonner'",
    "shadcn sidebar imports",
)
replace_once(
    "frontend/src/components/sidebar.tsx",
    "  const collapsed = isCollapsed && !mobileMenuOpen\n  const mobileDrawerRef = useRef<HTMLElement>(null)\n  \n  const [conversations, setConversations] = useState<SidebarConversation[]>([])",
    "  const collapsed = isCollapsed && !mobileMenuOpen\n  \n  const [conversations, setConversations] = useState<SidebarConversation[]>([])",
    "drop manual focus ref",
)
replace_once(
    "frontend/src/components/sidebar.tsx",
    "  const [activeWorkspace, setActiveWorkspace] = useState('all')\n\n  const isChatRoute",
    "  const [activeWorkspace, setActiveWorkspace] = useState('all')\n  const [deleteTarget, setDeleteTarget] = useState<SidebarConversation | null>(null)\n\n  const isChatRoute",
    "delete dialog state",
)
regex_once(
    "frontend/src/components/sidebar.tsx",
    r"\n  useEffect\(\(\) => \{\n    if \(!mobileMenuOpen\) return\n.*?\n  \}, \[mobileMenuOpen, setMobileMenuOpen\]\)\n",
    "\n",
    "remove manual drawer focus/escape management",
    flags=re.S,
)
regex_once(
    "frontend/src/components/sidebar.tsx",
    r"  const handleDeleteConversation = async \(id: string, e: React\.MouseEvent\) => \{.*?\n  \}\n\n  const startRename",
    '''  const handleDeleteConversation = async () => {\n    if (!deleteTarget) return\n    const id = deleteTarget.id\n    const res = await api.chat.deleteConversation(id)\n    if (res.success) {\n      setConversations(prev => prev.filter(c => c.id !== id))\n      setDeleteTarget(null)\n      if (pathname === `/chat` || pathname.startsWith(`/chat/`)) {\n        router.push('/chat')\n      }\n      toast.success('Conversation deleted')\n    } else {\n      toast.error(res.error || 'Failed to delete conversation')\n    }\n  }\n\n  const startRename''',
    "replace browser confirm with controlled dialog",
    flags=re.S,
)
replace_once(
    "frontend/src/components/sidebar.tsx",
    "                        onClick={(e) => handleDeleteConversation(conv.id, e)}",
    "                        onClick={(e) => { e.stopPropagation(); e.preventDefault(); setDeleteTarget(conv) }}",
    "open delete dialog",
)
replace_once(
    "frontend/src/components/sidebar.tsx",
    '''              {loadingDocuments ? (\n                <div className="flex items-center justify-center py-4">\n                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />\n                </div>\n              ) : documents.length === 0 ? (''',
    '''              {loadingDocuments ? (\n                <div className="space-y-2 px-1 py-2" aria-label="Loading documents">\n                  <Skeleton className="h-8 w-full rounded-md" />\n                  <Skeleton className="h-8 w-11/12 rounded-md" />\n                  <Skeleton className="h-8 w-4/5 rounded-md" />\n                </div>\n              ) : documents.length === 0 ? (''',
    "document loading skeletons",
)
replace_once(
    "frontend/src/components/sidebar.tsx",
    "                  onClick={() => setMobileMenuOpen(false)}\n                  className={cn(",
    "                  onClick={() => setMobileMenuOpen(false)}\n                  aria-current={isActive ? 'page' : undefined}\n                  className={cn(",
    "active navigation semantics",
)
regex_once(
    "frontend/src/components/sidebar.tsx",
    r'''      \{\/\* Mobile Drawer \(Fixed Overlay — Never affects or shrinks background layout\) \*\/\}\n      \{mobileMenuOpen && \(\n        <>.*?\n        </>\n      \)\}\n''',
    '''      {/* Mobile navigation uses the shadcn Sheet primitive for focus trapping,\n          Escape handling, scroll locking, and accessible dialog semantics. */}\n      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>\n        <SheetContent\n          side="left"\n          className="w-[min(88vw,20rem)] max-w-[20rem] gap-0 overflow-hidden border-r border-border bg-secondary p-0 pb-[env(safe-area-inset-bottom)] pt-[env(safe-area-inset-top)] [&>button]:hidden"\n        >\n          <SheetHeader className="sr-only">\n            <SheetTitle>Navigation menu</SheetTitle>\n          </SheetHeader>\n          <div className="flex h-full min-h-0 flex-col">\n            {renderSidebarContent(true)}\n          </div>\n        </SheetContent>\n      </Sheet>\n\n      <Dialog open={Boolean(deleteTarget)} onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}>\n        <DialogContent className="w-[calc(100vw-2rem)] max-w-md">\n          <DialogHeader>\n            <DialogTitle>Delete conversation?</DialogTitle>\n            <DialogDescription>\n              {deleteTarget ? `“${deleteTarget.title}” will be permanently removed. This action cannot be undone.` : 'This conversation will be permanently removed.'}\n            </DialogDescription>\n          </DialogHeader>\n          <DialogFooter className="gap-2 sm:gap-0">\n            <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>\n            <Button type="button" variant="destructive" onClick={handleDeleteConversation}>Delete</Button>\n          </DialogFooter>\n        </DialogContent>\n      </Dialog>\n''',
    "replace manual mobile drawer with shadcn Sheet",
    flags=re.S,
)

# 4) Dashboard: use shadcn Alert/Skeleton for consistent recoverable states.
replace_once(
    "frontend/src/app/(dashboard)/dashboard/page.tsx",
    "import { Textarea } from '@/components/ui/textarea'",
    "import { Textarea } from '@/components/ui/textarea'\nimport { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'\nimport { Skeleton } from '@/components/ui/skeleton'",
    "dashboard shadcn state imports",
)
replace_once(
    "frontend/src/app/(dashboard)/dashboard/page.tsx",
    '''      {error && (\n        <div className="p-4 rounded-[8px] border border-red-200 bg-red-50 text-xs text-red-700">\n          {error}\n          <span className="text-[10px] ml-2 font-mono opacity-80">(Some stats may be incomplete)</span>\n        </div>\n      )}''',
    '''      {error && (\n        <Alert variant="destructive">\n          <AlertTitle>Dashboard data is partially unavailable</AlertTitle>\n          <AlertDescription>{error}. Some workspace totals may be incomplete.</AlertDescription>\n        </Alert>\n      )}''',
    "dashboard error alert",
)
replace_once(
    "frontend/src/app/(dashboard)/dashboard/page.tsx",
    '''                {loading ? (\n                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />\n                ) : (\n                  stats[stat.key]\n                )}''',
    '''                {loading ? (\n                  <Skeleton className="h-9 w-16 rounded-md" />\n                ) : (\n                  stats[stat.key]\n                )}''',
    "dashboard stat skeleton",
)
replace_once(
    "frontend/src/app/(dashboard)/dashboard/page.tsx",
    '''        {loading ? (\n          <div className="flex h-40 items-center justify-center gap-2 text-xs text-muted-foreground">\n            <Loader2 className="h-4 w-4 animate-spin" /> Loading recent work\n          </div>\n        ) : visibleActivity.length > 0 ? (''',
    '''        {loading ? (\n          <div className="space-y-1 p-3" aria-label="Loading recent work">\n            {[0, 1, 2].map((item) => (\n              <div key={item} className="grid min-h-16 grid-cols-[auto_minmax(0,1fr)_auto] items-center gap-3 px-2 py-3">\n                <Skeleton className="h-8 w-8 rounded-md" />\n                <div className="space-y-2">\n                  <Skeleton className="h-3 w-2/5" />\n                  <Skeleton className="h-2.5 w-3/4" />\n                </div>\n                <Skeleton className="h-7 w-7 rounded-md" />\n              </div>\n            ))}\n          </div>\n        ) : visibleActivity.length > 0 ? (''',
    "dashboard activity skeleton",
)

# 5) Add segment-level user-facing error and loading states using the same
# shadcn primitives instead of blank screens or raw framework errors.
Path("frontend/src/app/error.tsx").write_text('''\'use client\'\n\nimport { useEffect } from \'react\'\nimport { AlertCircle, RotateCcw } from \'lucide-react\'\nimport { Alert, AlertDescription, AlertTitle } from \'@/components/ui/alert\'\nimport { Button } from \'@/components/ui/button\'\n\nexport default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {\n  useEffect(() => {\n    console.error(\'Unhandled application error\', error)\n  }, [error])\n\n  return (\n    <main className="flex min-h-[60vh] items-center justify-center px-4 py-10">\n      <div className="w-full max-w-lg space-y-4">\n        <Alert variant="destructive">\n          <AlertCircle className="h-4 w-4" />\n          <AlertTitle>Something went wrong</AlertTitle>\n          <AlertDescription>\n            The page could not finish loading. Your saved data has not been changed. Try the request again.\n          </AlertDescription>\n        </Alert>\n        <Button type="button" onClick={reset} className="gap-2">\n          <RotateCcw className="h-4 w-4" />\n          Try again\n        </Button>\n      </div>\n    </main>\n  )\n}\n''', encoding="utf-8")

Path("frontend/src/app/(dashboard)/loading.tsx").write_text('''import { Skeleton } from \'@/components/ui/skeleton\'\n\nexport default function DashboardLoading() {\n  return (\n    <div className="mx-auto w-full max-w-7xl space-y-6 py-2 sm:py-4" aria-label="Loading workspace">\n      <div className="space-y-3">\n        <Skeleton className="h-6 w-36 rounded-full" />\n        <Skeleton className="h-10 w-56" />\n        <Skeleton className="h-4 w-full max-w-lg" />\n      </div>\n      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">\n        {[0, 1, 2, 3].map((item) => <Skeleton key={item} className="h-36 rounded-xl" />)}\n      </div>\n      <Skeleton className="h-72 w-full rounded-xl" />\n    </div>\n  )\n}\n''', encoding="utf-8")

# 6) Simple source-level regression checks for the shared shell changes.
Path("frontend/tests/ui-shell-quality.test.ts").write_text('''import fs from \'node:fs\'\nimport path from \'node:path\'\nimport { describe, expect, it } from \'vitest\'\n\nconst root = process.cwd()\nconst source = (relative: string) => fs.readFileSync(path.join(root, relative), \'utf8\')\n\ndescribe(\'shared UI shell regressions\', () => {\n  it(\'keeps mobile zoom enabled for accessibility\', () => {\n    const layout = source(\'src/app/layout.tsx\')\n    expect(layout).not.toContain(\'userScalable: false\')\n    expect(layout).not.toContain(\'maximumScale: 1\')\n  })\n\n  it(\'uses shadcn Sheet instead of a hand-rolled mobile dialog\', () => {\n    const sidebar = source(\'src/components/sidebar.tsx\')\n    expect(sidebar).toContain(\'<Sheet open={mobileMenuOpen}\')\n    expect(sidebar).not.toContain(\'mobileDrawerRef\')\n    expect(sidebar).not.toContain(\"if (confirm(\'Delete this conversation?\'))\")\n  })\n\n  it(\'provides segment error and loading UI\', () => {\n    expect(source(\'src/app/error.tsx\')).toContain(\'<Alert variant="destructive">\')\n    expect(source(\'src/app/(dashboard)/loading.tsx\')).toContain(\'<Skeleton\')\n  })\n})\n''', encoding="utf-8")

print("shadcn UI quality sweep applied")
