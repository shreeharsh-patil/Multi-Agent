'use client'

import React, { useState, useEffect, useCallback, useMemo } from 'react'
import Link from 'next/link'
import Image from 'next/image'
import { usePathname, useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { cn } from '@/lib/utils'
import { useSidebar } from '@/context/sidebar-context'
import { api } from '@/lib/api'
import {
  LayoutDashboard,
  Bot,
  BookOpen,
  StickyNote,
  Search,
  Calendar,
  HardDrive,
  Settings,
  PanelLeftClose,
  PanelLeft,
  Plus,
  Trash2,
  FolderOpen,
  FileText,
  ImageIcon,
  Pencil,
  BrainCircuit,
  Workflow,
  ListChecks,
  FileCode,
  GalleryVerticalEnd,
  LibraryBig,
  BarChart2,
  CloudSun,
  Users,
  X,
} from 'lucide-react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Skeleton } from '@/components/ui/skeleton'
import { openCommandPalette } from '@/components/command-palette'
import { toast } from 'sonner'

// Map existing functional routes to standard names from prompt style
const navigation = [
  { name: 'Workspace', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Agent Swarm', href: '/swarm', icon: Users },
  { name: 'Task Runner', href: '/task-runner', icon: ListChecks },
  { name: 'Code Agent', href: '/code-agent', icon: FileCode },
  { name: 'Search', href: '/research', icon: Search },
  { name: 'Library', href: '/documents', icon: BookOpen },
  { name: 'Drive', href: '/drive', icon: HardDrive },
  { name: 'Agentic', href: '/agents', icon: Bot },
  { name: 'Workflows', href: '/workflows', icon: Workflow },
  { name: 'Data Analysis', href: '/data-analysis', icon: BarChart2 },
  { name: 'Weather & News', href: '/weather-news', icon: CloudSun },
  { name: 'Notes', href: '/notes', icon: StickyNote },
  { name: 'Scheduled', href: '/planner', icon: Calendar },
  { name: 'Memory', href: '/memory', icon: BrainCircuit },
  { name: 'Flashcards', href: '/flashcards', icon: GalleryVerticalEnd },
  { name: 'Templates', href: '/templates', icon: LibraryBig },
  { name: 'Settings', href: '/settings', icon: Settings },
]

interface SidebarConversation {
  id: string
  title: string
  createdAt: string
}

export function Sidebar() {
  const pathname = usePathname()
  const router = useRouter()
  const { data: session } = useSession()
  const { isCollapsed, toggle, mobileMenuOpen, setMobileMenuOpen } = useSidebar()
  const collapsed = isCollapsed && !mobileMenuOpen
  
  const [conversations, setConversations] = useState<SidebarConversation[]>([])
  const [conversationSearch, setConversationSearch] = useState('')
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameText, setRenameText] = useState('')
  const [activeWorkspace, setActiveWorkspace] = useState('all')
  const [deleteTarget, setDeleteTarget] = useState<SidebarConversation | null>(null)

  const isChatRoute = pathname === '/chat' || pathname.startsWith('/chat/')
  const [documents, setDocuments] = useState<any[]>([])
  const [loadingDocuments, setLoadingDocuments] = useState(false)

  const fetchDocuments = useCallback(async () => {
    if (!isChatRoute) return
    setLoadingDocuments(true)
    try {
      const res = await api.documents.list(activeWorkspace === 'all' ? undefined : activeWorkspace === 'unfiled' ? '__unfiled__' : activeWorkspace)
      if (res.success && res.data) {
        setDocuments(res.data)
      } else {
        console.warn("Failed to load sidebar documents:", res.error)
      }
    } catch (err) {
      console.error("Error loading sidebar documents", err)
    } finally {
      setLoadingDocuments(false)
    }
  }, [isChatRoute, activeWorkspace])

  useEffect(() => {
    if (isChatRoute && session) {
      fetchDocuments()
    }
  }, [isChatRoute, session, fetchDocuments])

  useEffect(() => {
    const handleRefresh = () => {
      fetchDocuments()
    }
    window.addEventListener('refresh-documents-list', handleRefresh)
    return () => window.removeEventListener('refresh-documents-list', handleRefresh)
  }, [fetchDocuments])

  useEffect(() => {
    const handleWorkspaceChange = (e: Event) => {
      const workspaceId = (e as CustomEvent).detail
      setActiveWorkspace(workspaceId)
    }
    window.addEventListener('workspace-changed', handleWorkspaceChange)
    return () => window.removeEventListener('workspace-changed', handleWorkspaceChange)
  }, [])

  // Fetch recent conversations for history section
  const loadSidebarHistory = useCallback(() => {
    api.chat.listConversations()
      .then((res) => {
        if (res.success && res.data) {
          setConversations(res.data.map(c => ({
            id: c.id,
            title: c.title,
            createdAt: c.createdAt
          })))
        }
      })
      .catch(err => console.error("Error loading sidebar history", err))
  }, [])

  useEffect(() => {
    loadSidebarHistory()
    window.addEventListener('refresh-conversations-list', loadSidebarHistory)
    return () => window.removeEventListener('refresh-conversations-list', loadSidebarHistory)
  }, [pathname, loadSidebarHistory])


  // Ctrl+B shortcut to toggle sidebar collapse
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'b') {
        e.preventDefault()
        toggle()
      }
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [toggle])


  useEffect(() => {
    setMobileMenuOpen(false)
  }, [pathname, setMobileMenuOpen])

  // Group conversations by date
  const { today, yesterday, previous7Days, older } = useMemo(() => {
    const todayList: SidebarConversation[] = []
    const yesterdayList: SidebarConversation[] = []
    const previous7DaysList: SidebarConversation[] = []
    const olderList: SidebarConversation[] = []

    const now = new Date()
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterdayStart = new Date(todayStart)
    yesterdayStart.setDate(yesterdayStart.getDate() - 1)
    const sevenDaysAgo = new Date(todayStart)
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

    const q = conversationSearch.trim().toLowerCase()
    const visible = q
      ? conversations.filter((c) => c.title.toLowerCase().includes(q))
      : conversations

    visible.forEach((conv) => {
      const date = new Date(conv.createdAt)
      if (date >= todayStart) {
        todayList.push(conv)
      } else if (date >= yesterdayStart) {
        yesterdayList.push(conv)
      } else if (date >= sevenDaysAgo) {
        previous7DaysList.push(conv)
      } else {
        olderList.push(conv)
      }
    })

    return {
      today: todayList,
      yesterday: yesterdayList,
      previous7Days: previous7DaysList,
      older: olderList,
    }
  }, [conversations, conversationSearch])

  const handleNewChat = () => {
    if (isChatRoute) {
      window.dispatchEvent(new Event('start-new-chat'))
      router.replace('/chat')
      setMobileMenuOpen(false)
      return
    }
    router.push('/chat')
    setMobileMenuOpen(false)
  }

  const handleDeleteConversation = async () => {
    if (!deleteTarget) return
    const id = deleteTarget.id
    const res = await api.chat.deleteConversation(id)
    if (res.success) {
      setConversations(prev => prev.filter(c => c.id !== id))
      setDeleteTarget(null)
      if (pathname === `/chat` || pathname.startsWith(`/chat/`)) {
        router.push('/chat')
      }
      toast.success('Conversation deleted')
    } else {
      toast.error(res.error || 'Failed to delete conversation')
    }
  }

  const startRename = (id: string, currentTitle: string, e: React.MouseEvent) => {
    e.stopPropagation()
    e.preventDefault()
    setRenamingId(id)
    setRenameText(currentTitle)
  }

  const cancelRename = () => {
    setRenamingId(null)
    setRenameText('')
  }

  const saveRename = async (id: string) => {
    const title = renameText.trim()
    if (!title) {
      cancelRename()
      return
    }
    const res = await api.chat.renameConversation(id, title)
    if (res.success && res.data) {
      setConversations(prev => prev.map(c => (c.id === id ? { ...c, title: res.data!.title } : c)))
    } else {
      console.error('Failed to rename conversation:', res.error)
    }
    cancelRename()
  }

  const renderHistorySection = (title: string, list: SidebarConversation[]) => {
    if (list.length === 0) return null
    return (
      <div className="space-y-1 mb-4">
        <h4 className="px-3 text-[10px] font-semibold text-muted-foreground uppercase tracking-wider select-none">
          {title}
        </h4>
        <div className="space-y-0.5">
          {list.map((conv) => {
            const isActive = pathname.includes(conv.id)
            const isRenaming = renamingId === conv.id
            return (
              <div
                key={conv.id}
                onClick={() => { if (!isRenaming) { router.push(`/chat?id=${conv.id}`); setMobileMenuOpen(false); } }}
                className={cn(
                  "group relative flex min-w-0 items-center justify-between px-3 py-2 rounded-[8px] text-sm cursor-pointer transition-all duration-150",
                  isActive
                    ? "bg-background text-foreground border border-border font-semibold shadow-xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-background/50"
                )}
              >
                {isRenaming ? (
                  <input
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
                  />
                ) : (
                  <>
                    <span className="truncate w-full pr-10 text-xs">
                      {conv.title}
                    </span>

                    {/* Hover actions */}
                    <div className="absolute right-1 top-1/2 flex -translate-y-1/2 items-center gap-1 opacity-100 transition-opacity lg:right-2 lg:opacity-0 lg:group-hover:opacity-100 lg:group-focus-within:opacity-100">
                      <button
                        onClick={(e) => startRename(conv.id, conv.title, e)}
                        className="flex h-8 w-8 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground cursor-pointer"
                        title="Rename"
                        aria-label={`Rename ${conv.title}`}
                      >
                        <Pencil className="h-3 w-3 stroke-[1.5]" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); e.preventDefault(); setDeleteTarget(conv) }}
                        className="flex h-8 w-8 items-center justify-center rounded text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground cursor-pointer"
                        title="Delete"
                        aria-label={`Delete ${conv.title}`}
                      >
                        <Trash2 className="h-3 w-3 stroke-[1.5]" />
                      </button>
                    </div>
                  </>
                )}
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  const renderSidebarContent = (isMobile: boolean) => (
    <>
      {/* Top Header Section */}
      <div className="p-4 flex flex-col gap-4 border-b border-border shrink-0">
        <div className="flex items-center justify-between h-9">
          {collapsed && !isMobile ? (
            <button
              onClick={toggle}
              className="h-9 w-9 rounded-[8px] border border-border bg-card flex items-center justify-center transition-all hover:bg-secondary/40 duration-200 shadow-xs shrink-0 mx-auto cursor-pointer"
              title="Expand sidebar (Ctrl+B)"
            >
              <PanelLeft className="h-4.5 w-4.5 text-muted-foreground" />
            </button>
          ) : (
            <>
              <Link href="/dashboard" className="flex items-center gap-2.5 group">
                <div className="h-9 w-9 rounded-[8px] border border-border bg-card flex items-center justify-center transition-all group-hover:scale-105 duration-200 shadow-xs shrink-0">
                  <Image src="/logo.png" alt="Agentic Logo" width={24} height={24} className="h-6 w-6 object-contain" />
                </div>
                <span className="font-sans font-normal text-lg tracking-[-0.03em] text-[#26251e]">
                  Agentic
                </span>
              </Link>
              <button
                onClick={isMobile ? () => setMobileMenuOpen(false) : toggle}
                className="flex h-11 w-11 items-center justify-center rounded-[8px] text-muted-foreground transition-colors hover:bg-card hover:text-foreground cursor-pointer"
                title={isMobile ? "Close menu" : "Collapse sidebar (Ctrl+B)"}
                aria-label={isMobile ? "Close navigation menu" : "Collapse sidebar"}
              >
                {isMobile ? (
                  <X className="h-4.5 w-4.5 stroke-[1.5]" />
                ) : (
                  <PanelLeftClose className="h-4.5 w-4.5 stroke-[1.5]" />
                )}
              </button>
            </>
          )}
        </div>

        <button
          type="button"
          onClick={openCommandPalette}
          className={cn(
            'flex h-9 items-center rounded-[8px] border border-border bg-card text-muted-foreground shadow-xs transition-colors hover:bg-secondary/40 hover:text-foreground',
            (collapsed && !isMobile) ? 'w-9 justify-center self-center' : 'w-full gap-2.5 px-3',
          )}
          title="Search workspace (Ctrl+K)"
          aria-label="Search workspace"
        >
          <Search className="h-4 w-4 shrink-0" strokeWidth={1.5} />
          {(!collapsed || isMobile) ? (
            <>
              <span className="flex-1 text-left text-xs">Search workspace</span>
              <kbd className="rounded-[4px] border border-border bg-secondary px-1.5 py-0.5 text-[9px] text-muted-foreground">Ctrl K</kbd>
            </>
          ) : null}
        </button>

        {/* New Chat Button */}
        <button
          onClick={() => { handleNewChat(); if (isMobile) setMobileMenuOpen(false); }}
          className={cn(
            "flex items-center justify-center rounded-[8px] border border-border text-[13px] font-semibold text-foreground transition-all active:scale-[0.98] shadow-xs bg-card cursor-pointer",
            (isCollapsed && !isMobile)
              ? "h-9 w-9 hover:bg-secondary/40 mx-auto gap-0" 
              : "w-full py-2 hover:bg-secondary/40 gap-2"
          )}
          title="New Chat"
        >
          <Plus className="h-4 w-4 stroke-[1.5]" />
          <span className={cn(
            "transition-all duration-300 ease-in-out whitespace-nowrap overflow-hidden",
            (collapsed && !isMobile) ? "opacity-0 w-0" : "opacity-100 w-auto"
          )}>
            New Chat
          </span>
        </button>
      </div>

      {/* Main Navigation Links */}
      <div className="flex-1 px-3 py-4 space-y-6 overflow-y-auto overflow-x-hidden scrollbar-thin">
        <div className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
            return (
              <div key={item.name} className="relative group/tooltip">
                <Link
                  href={item.href}
                  prefetch={true}
                  onClick={() => setMobileMenuOpen(false)}
                  aria-current={isActive ? 'page' : undefined}
                  className={cn(
                    "flex items-center rounded-[8px] font-semibold text-sm transition-all duration-200 relative h-10",
                    (collapsed && !isMobile)
                      ? "justify-center h-10 w-10 mx-auto gap-0 px-0" 
                      : "w-full px-3 py-2 gap-3",
                    isActive 
                      ? "bg-card text-foreground border border-border shadow-xs" 
                      : "text-muted-foreground hover:text-foreground hover:bg-card/50"
                  )}
                >
                  <item.icon className={cn("h-4.5 w-4.5 stroke-[1.5] shrink-0", isActive ? "text-primary" : "text-muted-foreground")} />
                  <span className={cn(
                    "transition-all duration-300 ease-in-out whitespace-nowrap overflow-hidden truncate",
                    (collapsed && !isMobile) ? "opacity-0 w-0" : "opacity-100 w-auto"
                  )}>
                    {item.name}
                  </span>
                </Link>

                {/* Collapsed Tooltip */}
                {collapsed && !isMobile && (
                  <div className="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-2.5 py-1.5 rounded-[6px] bg-card border border-border text-xs font-semibold text-foreground whitespace-nowrap opacity-0 pointer-events-none group-hover/tooltip:opacity-100 transition-opacity duration-150 z-50 shadow-xs">
                    {item.name}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Documents Explorer Section */}
        {isChatRoute && (!collapsed || isMobile) && (
          <div className="space-y-2 pt-4 border-t border-border">
            <div className="px-3 flex items-center justify-between">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider select-none">
                Documents Explorer
              </span>
              <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
            
            <div className="px-1 max-h-[220px] overflow-y-auto scrollbar-thin">
              {loadingDocuments ? (
                <div className="space-y-2 px-1 py-2" aria-label="Loading documents">
                  <Skeleton className="h-8 w-full rounded-md" />
                  <Skeleton className="h-8 w-11/12 rounded-md" />
                  <Skeleton className="h-8 w-4/5 rounded-md" />
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center py-6 text-[10px] text-muted-foreground px-2">
                  No documents index. Drag & drop files in chat to upload.
                </div>
              ) : (
                <div className="space-y-0.5">
                  {documents.map((doc) => {
                    const fileType = doc.fileType.toLowerCase()
                    const isImg = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'].includes(fileType)
                    const Icon = isImg ? ImageIcon : FileText
                    return (
                      <button
                        key={doc.id}
                        onClick={() => {
                          const event = new CustomEvent('open-document-tab', { detail: doc })
                          window.dispatchEvent(event)
                          if (isMobile) setMobileMenuOpen(false)
                        }}
                        className="w-full flex items-center gap-2.5 rounded-[8px] px-2.5 py-1.5 text-left text-xs transition-all hover:bg-background text-muted-foreground hover:text-foreground cursor-pointer"
                      >
                        <Icon className="h-3.5 w-3.5 shrink-0 text-muted-foreground" />
                        <span className="truncate flex-1 text-[11px] font-sans">{doc.fileName}</span>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        )}

        {/* History / Conversations Section */}
        <div className={cn(
          "transition-all duration-300 ease-in-out overflow-hidden",
          (collapsed && !isMobile) ? "opacity-0 h-0 pointer-events-none" : "opacity-100 h-auto pt-4 border-t border-border"
        )}>
          {conversations.length > 0 && (
            <>
              <div className="relative mb-2">
                <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
                <input
                  type="text"
                  value={conversationSearch}
                  onChange={(e) => setConversationSearch(e.target.value)}
                  placeholder="Search chats..."
                  className="w-full h-8 pl-8 pr-2 rounded-[8px] bg-card border border-border text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-ring"
                />
              </div>
              {renderHistorySection("Today", today)}
              {renderHistorySection("Yesterday", yesterday)}
              {renderHistorySection("Previous 7 Days", previous7Days)}
              {renderHistorySection("Older", older)}
            </>
          )}
        </div>
      </div>

      {/* Footer Profile Section */}
      <div className={cn("p-4 border-t border-border bg-secondary/85 shrink-0", (collapsed && !isMobile) ? "px-2" : "px-4")}>
        <div className={cn("flex items-center", (collapsed && !isMobile) ? "justify-center" : "gap-3")}>
          <div className="relative group/tooltip">
            <Avatar className="h-9 w-9 border border-border cursor-pointer shrink-0" onClick={() => { router.push('/settings'); if (isMobile) setMobileMenuOpen(false); }}>
              <AvatarImage src={session?.user?.image ?? ''} alt={session?.user?.name ?? ''} />
              <AvatarFallback className="bg-card text-xs text-muted-foreground font-semibold uppercase">
                {session?.user?.name?.charAt(0) ?? 'U'}
              </AvatarFallback>
            </Avatar>
          </div>

          {(!collapsed || isMobile) && (
            <div className="flex-1 flex items-center justify-between transition-all duration-300 ease-in-out min-w-0">
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-[13px] font-semibold text-[#26251e] truncate leading-tight">
                    {session?.user?.name}
                  </span>
                  <span className="px-1.5 py-0.5 rounded-[4px] bg-primary text-primary-foreground text-[9px] font-bold tracking-wider uppercase select-none shrink-0">
                    Pro
                  </span>
                </div>
                <span className="text-[11px] text-muted-foreground truncate">
                  {session?.user?.email}
                </span>
              </div>
              
              <Link 
                href="/settings"
                onClick={() => setMobileMenuOpen(false)}
                className="p-1.5 hover:bg-card rounded-[8px] text-muted-foreground hover:text-foreground transition-colors shrink-0 ml-2"
                title="Settings"
              >
                <Settings className="h-4 w-4 stroke-[1.5]" />
              </Link>
            </div>
          )}
        </div>
      </div>
    </>
  )

  return (
    <>
      {/* Mobile navigation uses the shadcn Sheet primitive for focus trapping,
          Escape handling, scroll locking, and accessible dialog semantics. */}
      <Sheet open={mobileMenuOpen} onOpenChange={setMobileMenuOpen}>
        <SheetContent
          side="left"
          className="w-[min(88vw,20rem)] max-w-[20rem] gap-0 overflow-hidden border-r border-border bg-secondary p-0 pb-[env(safe-area-inset-bottom)] pt-[env(safe-area-inset-top)] [&>button]:hidden"
        >
          <SheetHeader className="sr-only">
            <SheetTitle>Navigation menu</SheetTitle>
          </SheetHeader>
          <div className="flex h-full min-h-0 flex-col">
            {renderSidebarContent(true)}
          </div>
        </SheetContent>
      </Sheet>

      <Dialog open={Boolean(deleteTarget)} onOpenChange={(open) => { if (!open) setDeleteTarget(null) }}>
        <DialogContent className="w-[calc(100vw-2rem)] max-w-md">
          <DialogHeader>
            <DialogTitle>Delete conversation?</DialogTitle>
            <DialogDescription>
              {deleteTarget ? `“${deleteTarget.title}” will be permanently removed. This action cannot be undone.` : 'This conversation will be permanently removed.'}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter className="gap-2 sm:gap-0">
            <Button type="button" variant="outline" onClick={() => setDeleteTarget(null)}>Cancel</Button>
            <Button type="button" variant="destructive" onClick={handleDeleteConversation}>Delete</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Desktop Sidebar (In-flow flex layout item strictly for lg+ screens) */}
      <aside 
        className={cn(
          "relative z-40 hidden h-full shrink-0 flex-col overflow-hidden border-r border-border bg-secondary transition-all duration-350 ease-in-out lg:flex",
          collapsed ? "w-[68px]" : "w-[280px]"
        )}
      >
        {renderSidebarContent(false)}
      </aside>
    </>
  )
}
