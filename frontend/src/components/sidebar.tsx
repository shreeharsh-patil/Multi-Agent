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
  ChevronDown,
  Trash2,
  FolderOpen,
  FileText,
  ImageIcon,
  Pencil,
  BrainCircuit,
  Workflow,
  GalleryVerticalEnd,
  LibraryBig,
  BarChart2,
  CloudSun,
  X,
} from 'lucide-react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { openCommandPalette } from '@/components/command-palette'

// Map existing functional routes to standard names from prompt style
const navigation = [
  { name: 'Workspace', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Search', href: '/research', icon: Search },
  { name: 'Library', href: '/documents', icon: BookOpen },
  { name: 'Drive', href: '/drive', icon: HardDrive },
  { name: 'Agents', href: '/agents', icon: Bot },
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
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false)
  const [workspaces, setWorkspaces] = useState<Array<{ id: string; name: string }>>([])
  const [activeWorkspace, setActiveWorkspace] = useState('all')

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

  // Fetch the user's real workspaces for the selector
  useEffect(() => {
    if (session) {
      api.workspaces.list()
        .then((res) => {
          if (res.success && res.data) {
            setWorkspaces(res.data.map(w => ({ id: w.id, name: w.name })))
          }
        })
        .catch(err => console.error("Error loading workspaces", err))
    }
  }, [session])

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

  const handleDeleteConversation = async (id: string, e: React.MouseEvent) => {
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
                  "group relative flex items-center justify-between px-3 py-2 rounded-[8px] text-sm cursor-pointer transition-all duration-150",
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
                    <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center opacity-0 group-hover:opacity-100 transition-opacity gap-1">
                      <button
                        onClick={(e) => startRename(conv.id, conv.title, e)}
                        className="p-1 hover:bg-secondary rounded text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                        title="Rename"
                      >
                        <Pencil className="h-3 w-3 stroke-[1.5]" />
                      </button>
                      <button
                        onClick={(e) => handleDeleteConversation(conv.id, e)}
                        className="p-1 hover:bg-secondary rounded text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                        title="Delete"
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

  return (
    <>
      {mobileMenuOpen && (
        <div 
          className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}
      <aside 
        className={cn(
          "flex-col border-r h-full bg-secondary border-border transition-all duration-350 ease-in-out shrink-0 overflow-hidden overflow-x-hidden",
          "hidden lg:flex relative z-40",
          collapsed ? "lg:w-[68px]" : "lg:w-[280px]",
          mobileMenuOpen ? "!flex fixed inset-y-0 left-0 z-50 w-[280px] animate-in slide-in-from-left duration-200 shadow-lg" : ""
        )}
      >
      {/* Top Header Section */}
      <div className="p-4 flex flex-col gap-4 border-b border-border shrink-0">
        <div className="flex items-center justify-between h-9">
          {collapsed ? (
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
                  <Image src="/logo.png" alt="Agents Logo" width={24} height={24} className="h-6 w-6 object-contain" />
                </div>
                <span className="font-sans font-normal text-lg tracking-[-0.03em] text-[#26251e]">
                  Agents
                </span>
              </Link>
              <button
                onClick={mobileMenuOpen ? () => setMobileMenuOpen(false) : toggle}
                className="p-1.5 hover:bg-card rounded-[8px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                title={mobileMenuOpen ? "Close menu" : "Collapse sidebar (Ctrl+B)"}
              >
                {mobileMenuOpen ? (
                  <X className="h-4.5 w-4.5 stroke-[1.5]" />
                ) : (
                  <PanelLeftClose className="h-4.5 w-4.5 stroke-[1.5]" />
                )}
              </button>
            </>
          )}
        </div>

        {/* Workspace Selector */}
        <div className={cn(
          "transition-all duration-300 ease-in-out overflow-hidden",
          collapsed ? "opacity-0 h-0 pointer-events-none" : "opacity-100 h-9"
        )}>
          <div className="relative">
            <button
              onClick={() => setShowWorkspaceMenu(!showWorkspaceMenu)}
              className="w-full flex items-center justify-between px-3 py-2 rounded-[8px] bg-card border border-border text-xs font-semibold text-foreground hover:bg-secondary/40 transition-colors shadow-xs cursor-pointer"
            >
              <div className="flex items-center gap-2 truncate">
                <div className="h-2 w-2 rounded-full bg-[#1f8a65]" />
                <span className="truncate">                    {activeWorkspace === 'all'
                      ? 'Personal Space'
                      : workspaces.find((w) => w.id === activeWorkspace)?.name || 'Personal Space'}

                </span>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground stroke-[1.5]" />
            </button>

            {showWorkspaceMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowWorkspaceMenu(false)} />
                <div className="absolute top-full left-0 right-0 mt-1.5 p-1 rounded-[8px] bg-card border border-border shadow-xs z-20 space-y-0.5">
                  {[{ id: 'all', name: 'Personal Space' }, ...workspaces].map((space) => (
                    <button
                      key={space.id}
                      onClick={() => {
                    setActiveWorkspace(space.id)
                    setShowWorkspaceMenu(false)
                    window.dispatchEvent(new CustomEvent('workspace-changed', { detail: space.id }))
                  }}
                  className={cn(
                    "w-full text-left px-3 py-1.5 rounded-[6px] text-xs transition-colors cursor-pointer",
                    activeWorkspace === space.id
                      ? "bg-secondary text-[#26251e] font-semibold"
                      : "text-muted-foreground hover:text-[#26251e] hover:bg-secondary/50"
                      )}
                    >
                      {space.name}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

        <button
          type="button"
          onClick={openCommandPalette}
          className={cn(
            'flex h-9 items-center rounded-[8px] border border-border bg-card text-muted-foreground shadow-xs transition-colors hover:bg-secondary/40 hover:text-foreground',
            collapsed ? 'w-9 justify-center self-center' : 'w-full gap-2.5 px-3',
          )}
          title="Search workspace (Ctrl+K)"
          aria-label="Search workspace"
        >
          <Search className="h-4 w-4 shrink-0" strokeWidth={1.5} />
          {!collapsed ? (
            <>
              <span className="flex-1 text-left text-xs">Search workspace</span>
              <kbd className="rounded-[4px] border border-border bg-secondary px-1.5 py-0.5 text-[9px] text-muted-foreground">Ctrl K</kbd>
            </>
          ) : null}
        </button>

        {/* New Chat Button */}
        <button
          onClick={handleNewChat}
          className={cn(
            "flex items-center justify-center rounded-[8px] border border-border text-[13px] font-semibold text-foreground transition-all active:scale-[0.98] shadow-xs bg-card cursor-pointer",
            isCollapsed 
              ? "h-9 w-9 hover:bg-secondary/40 mx-auto gap-0" 
              : "w-full py-2 hover:bg-secondary/40 gap-2"
          )}
          title="New Chat"
        >
          <Plus className="h-4 w-4 stroke-[1.5]" />
          <span className={cn(
            "transition-all duration-300 ease-in-out whitespace-nowrap overflow-hidden",
            collapsed ? "opacity-0 w-0" : "opacity-100 w-auto"
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
                  onClick={() => setMobileMenuOpen(false)}
                  className={cn(
                    "flex items-center rounded-[8px] font-semibold text-sm transition-all duration-200 relative h-10",
                    collapsed 
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
                    collapsed ? "opacity-0 w-0" : "opacity-100 w-auto"
                  )}>
                    {item.name}
                  </span>
                </Link>

                {/* Collapsed Tooltip */}
                {collapsed && (
                  <div className="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-2.5 py-1.5 rounded-[6px] bg-card border border-border text-xs font-semibold text-foreground whitespace-nowrap opacity-0 pointer-events-none group-hover/tooltip:opacity-100 transition-opacity duration-150 z-50 shadow-xs">
                    {item.name}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Documents Explorer Section (Only on Chat route and when not collapsed) */}
        {isChatRoute && !collapsed && (
          <div className="space-y-2 pt-4 border-t border-border">
            <div className="px-3 flex items-center justify-between">
              <span className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider select-none">
                Documents Explorer
              </span>
              <FolderOpen className="h-3.5 w-3.5 text-muted-foreground" />
            </div>
            
            <div className="px-1 max-h-[220px] overflow-y-auto scrollbar-thin">
              {loadingDocuments ? (
                <div className="flex items-center justify-center py-4">
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-primary border-t-transparent" />
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

        {/* History / Conversations Section (Hidden when collapsed) */}
        <div className={cn(
          "transition-all duration-300 ease-in-out overflow-hidden",
          collapsed ? "opacity-0 h-0 pointer-events-none" : "opacity-100 h-auto pt-4 border-t border-border"
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
              {conversationSearch.trim() && today.length + yesterday.length + previous7Days.length + older.length === 0 && (
                <p className="px-2 py-1.5 text-xs text-muted-foreground">No chats found.</p>
              )}
            </>
          )}
        </div>
      </div>

      {/* Footer Profile Section */}
      <div className={cn("p-4 border-t border-border bg-secondary/85 shrink-0", collapsed ? "px-2" : "px-4")}>
        <div className={cn("flex items-center", collapsed ? "justify-center" : "gap-3")}>
          <div className="relative group/tooltip">
            <Avatar className="h-9 w-9 border border-border cursor-pointer shrink-0" onClick={() => router.push('/settings')}>
              <AvatarImage src={session?.user?.image ?? ''} alt={session?.user?.name ?? ''} />
              <AvatarFallback className="bg-card text-xs text-muted-foreground font-semibold uppercase">
                {session?.user?.name?.charAt(0) ?? 'U'}
              </AvatarFallback>
            </Avatar>

            {/* Collapsed profile tooltip */}
            {collapsed && (
              <div className="absolute left-full bottom-0 ml-3 p-3 rounded-[8px] bg-card border border-border shadow-xs z-50 flex flex-col gap-1.5 pointer-events-none opacity-0 group-hover/tooltip:opacity-100 transition-opacity duration-150">
                <span className="text-xs font-semibold text-[#26251e] whitespace-nowrap">{session?.user?.name}</span>
                <span className="text-[10px] text-muted-foreground whitespace-nowrap">{session?.user?.email}</span>
                <span className="text-[9px] bg-primary text-primary-foreground px-1.5 py-0.5 rounded-[4px] font-bold w-fit uppercase tracking-wider">
                  Pro
                </span>
              </div>
            )}
          </div>

          {!collapsed && (
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
                className="p-1.5 hover:bg-card rounded-[8px] text-muted-foreground hover:text-foreground transition-colors shrink-0 ml-2"
                title="Settings"
              >
                <Settings className="h-4 w-4 stroke-[1.5]" />
              </Link>
            </div>
          )}
        </div>
      </div>
    </aside>
    </>
  )
}
