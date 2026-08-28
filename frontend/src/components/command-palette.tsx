'use client'

import { useCallback, useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  Bot,
  BookOpen,
  Calendar,
  FileText,
  HardDrive,
  LayoutDashboard,
  Loader2,
  MessageSquare,
  Search,
  Settings,
  StickyNote,
} from 'lucide-react'
import type { LucideIcon } from 'lucide-react'
import { api } from '@/lib/api'
import { cn } from '@/lib/utils'

type PaletteItem = {
  id: string
  label: string
  detail: string
  href: string
  group: 'Go to' | 'Recent conversations' | 'Notes' | 'Documents'
  icon: LucideIcon
  keywords?: string
}

const destinations: PaletteItem[] = [
  { id: 'dashboard', label: 'Workspace', detail: 'Overview and quick actions', href: '/dashboard', group: 'Go to', icon: LayoutDashboard, keywords: 'home overview' },
  { id: 'chat', label: 'New chat', detail: 'Start a conversation with an agent', href: '/chat', group: 'Go to', icon: MessageSquare, keywords: 'ask conversation' },
  { id: 'research', label: 'Research', detail: 'Search and investigate a topic', href: '/research', group: 'Go to', icon: Search, keywords: 'web search' },
  { id: 'documents', label: 'Document library', detail: 'Upload and manage knowledge files', href: '/documents', group: 'Go to', icon: BookOpen, keywords: 'files upload library' },
  { id: 'drive', label: 'Google Drive', detail: 'Browse connected cloud files', href: '/drive', group: 'Go to', icon: HardDrive, keywords: 'cloud files' },
  { id: 'agents', label: 'Agents', detail: 'Manage specialist agents', href: '/agents', group: 'Go to', icon: Bot, keywords: 'specialists team' },
  { id: 'notes', label: 'Notes', detail: 'Write and organize notes', href: '/notes', group: 'Go to', icon: StickyNote, keywords: 'write knowledge' },
  { id: 'planner', label: 'Scheduled', detail: 'Review plans and scheduled work', href: '/planner', group: 'Go to', icon: Calendar, keywords: 'calendar plan tasks' },
  { id: 'settings', label: 'Settings', detail: 'Profile and platform preferences', href: '/settings', group: 'Go to', icon: Settings, keywords: 'profile preferences' },
]

const groups: PaletteItem['group'][] = ['Go to', 'Recent conversations', 'Notes', 'Documents']

export function openCommandPalette() {
  window.dispatchEvent(new Event('open-command-palette'))
}

export function CommandPalette() {
  const router = useRouter()
  const inputRef = useRef<HTMLInputElement>(null)
  const [open, setOpen] = useState(false)
  const [query, setQuery] = useState('')
  const deferredQuery = useDeferredValue(query)
  const [remoteItems, setRemoteItems] = useState<PaletteItem[]>([])
  const [loading, setLoading] = useState(false)
  const [hasLoaded, setHasLoaded] = useState(false)
  const [activeIndex, setActiveIndex] = useState(0)

  const show = useCallback(() => {
    setOpen(true)
    setQuery('')
    setActiveIndex(0)
  }, [])

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        setOpen((current) => {
          if (current) return false
          setQuery('')
          setActiveIndex(0)
          return true
        })
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    window.addEventListener('open-command-palette', show)
    return () => {
      window.removeEventListener('keydown', handleKeyDown)
      window.removeEventListener('open-command-palette', show)
    }
  }, [show])

  useEffect(() => {
    if (!open) return
    const frame = window.requestAnimationFrame(() => inputRef.current?.focus())
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.cancelAnimationFrame(frame)
      document.body.style.overflow = previousOverflow
    }
  }, [open])

  useEffect(() => {
    if (!open || hasLoaded) return
    let cancelled = false
    setLoading(true)
    Promise.all([api.chat.listConversations(), api.notes.list(), api.documents.list()])
      .then(([conversations, notes, documents]) => {
        if (cancelled) return
        const items: PaletteItem[] = []
        if (conversations.success && conversations.data) {
          items.push(...conversations.data.slice(0, 8).map((conversation) => ({
            id: `conversation-${conversation.id}`,
            label: conversation.title || 'Untitled conversation',
            detail: conversation.lastMessage || `${conversation.messageCount} messages`,
            href: `/chat?id=${encodeURIComponent(conversation.id)}`,
            group: 'Recent conversations' as const,
            icon: MessageSquare,
          })))
        }
        if (notes.success && notes.data) {
          items.push(...notes.data.slice(0, 8).map((note) => ({
            id: `note-${note.id}`,
            label: note.title || 'Untitled note',
            detail: note.preview || note.tags.join(', ') || 'Note',
            href: `/notes?note=${encodeURIComponent(note.id)}`,
            group: 'Notes' as const,
            icon: StickyNote,
            keywords: note.tags.join(' '),
          })))
        }
        if (documents.success && documents.data) {
          items.push(...documents.data.slice(0, 8).map((document) => ({
            id: `document-${document.id}`,
            label: document.fileName,
            detail: `${document.fileType.toUpperCase()} document`,
            href: `/documents?document=${encodeURIComponent(document.id)}`,
            group: 'Documents' as const,
            icon: FileText,
            keywords: document.fileType,
          })))
        }
        setRemoteItems(items)
        setHasLoaded(true)
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [hasLoaded, open])

  const visibleItems = useMemo(() => {
    const value = deferredQuery.trim().toLowerCase()
    const allItems = [...destinations, ...remoteItems]
    if (!value) return allItems
    const terms = value.split(/\s+/)
    return allItems.filter((item) => {
      const haystack = `${item.label} ${item.detail} ${item.keywords ?? ''}`.toLowerCase()
      return terms.every((term) => haystack.includes(term))
    })
  }, [deferredQuery, remoteItems])

  useEffect(() => {
    setActiveIndex(0)
  }, [deferredQuery])

  useEffect(() => {
    document.getElementById(`palette-item-${activeIndex}`)?.scrollIntoView({ block: 'nearest' })
  }, [activeIndex])

  const selectItem = useCallback((item: PaletteItem) => {
    setOpen(false)
    router.push(item.href)
  }, [router])

  if (!open) return null

  return (
    <div className="fixed inset-0 z-[100] flex items-start justify-center px-3 pb-3 pt-[max(0.75rem,env(safe-area-inset-top))] sm:pt-[14vh]" role="presentation">
      <button
        type="button"
        aria-label="Close command palette"
        className="absolute inset-0 bg-[#26251e]/30 backdrop-blur-[2px]"
        onClick={() => setOpen(false)}
      />
      <section
        role="dialog"
        aria-modal="true"
        aria-label="Search workspace"
        className="relative flex max-h-[min(620px,calc(100dvh-1.5rem))] w-full max-w-[640px] min-w-0 flex-col overflow-hidden rounded-[8px] border border-border bg-card shadow-2xl"
        onKeyDown={(event) => {
          if (event.key === 'Escape') setOpen(false)
          if (event.key === 'ArrowDown') {
            event.preventDefault()
            setActiveIndex((index) => visibleItems.length ? (index + 1) % visibleItems.length : 0)
          }
          if (event.key === 'ArrowUp') {
            event.preventDefault()
            setActiveIndex((index) => visibleItems.length ? (index - 1 + visibleItems.length) % visibleItems.length : 0)
          }
          if (event.key === 'Enter' && visibleItems[activeIndex]) {
            event.preventDefault()
            selectItem(visibleItems[activeIndex])
          }
        }}
      >
        <div className="flex h-14 shrink-0 items-center gap-3 border-b border-border px-4">
          <Search className="h-4.5 w-4.5 shrink-0 text-primary" strokeWidth={1.7} />
          <input
            ref={inputRef}
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search tools, chats, notes, and documents"
            aria-label="Search tools, chats, notes, and documents"
            aria-controls="command-palette-results"
            aria-activedescendant={visibleItems[activeIndex] ? `palette-item-${activeIndex}` : undefined}
            className="h-full min-w-0 flex-1 bg-transparent text-base text-foreground outline-none placeholder:text-muted-foreground sm:text-sm"
          />
          <kbd className="hidden rounded-[4px] border border-border bg-secondary px-1.5 py-0.5 text-[10px] text-muted-foreground sm:block">Esc</kbd>
        </div>

        <div id="command-palette-results" role="listbox" className="scrollbar-thin overflow-y-auto p-2">
          {groups.map((group) => {
            const groupItems = visibleItems.filter((item) => item.group === group)
            if (!groupItems.length) return null
            return (
              <div key={group} className="pb-2 last:pb-0">
                <p className="px-2 pb-1.5 pt-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">{group}</p>
                {groupItems.map((item) => {
                  const index = visibleItems.indexOf(item)
                  const Icon = item.icon
                  return (
                    <button
                      key={item.id}
                      id={`palette-item-${index}`}
                      role="option"
                      aria-selected={index === activeIndex}
                      type="button"
                      onMouseEnter={() => setActiveIndex(index)}
                      onClick={() => selectItem(item)}
                      className={cn(
                        'flex h-12 w-full items-center gap-3 rounded-[6px] px-2.5 text-left transition-colors',
                        index === activeIndex ? 'bg-secondary text-foreground' : 'text-muted-foreground hover:bg-secondary/70',
                      )}
                    >
                      <span className={cn(
                        'flex h-8 w-8 shrink-0 items-center justify-center rounded-[6px] border bg-card',
                        index === activeIndex ? 'border-primary/30 text-primary' : 'border-border text-muted-foreground',
                      )}>
                        <Icon className="h-4 w-4" strokeWidth={1.5} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-xs font-semibold text-foreground">{item.label}</span>
                        <span className="mt-0.5 block truncate text-[10px] text-muted-foreground">{item.detail}</span>
                      </span>
                    </button>
                  )
                })}
              </div>
            )
          })}

          {!visibleItems.length && !loading ? (
            <div className="flex h-36 flex-col items-center justify-center text-center">
              <Search className="mb-3 h-5 w-5 text-muted-foreground" strokeWidth={1.5} />
              <p className="text-xs font-semibold text-foreground">No matching items</p>
              <p className="mt-1 text-[10px] text-muted-foreground">Try a tool name, note title, or file name.</p>
            </div>
          ) : null}
          {loading ? (
            <div className="flex items-center justify-center gap-2 py-3 text-[10px] text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin" /> Loading recent work
            </div>
          ) : null}
        </div>

        <footer className="hidden h-9 shrink-0 items-center gap-4 border-t border-border bg-secondary/60 px-4 text-[10px] text-muted-foreground sm:flex">
          <span><kbd className="font-sans">↑↓</kbd> Navigate</span>
          <span><kbd className="font-sans">Enter</kbd> Open</span>
          <span className="ml-auto">Workspace search</span>
        </footer>
      </section>
    </div>
  )
}
