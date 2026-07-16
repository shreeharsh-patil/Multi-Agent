'use client'

import React, { useState, useEffect, useCallback } from 'react'
import Link from 'next/link'
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
  ImageIcon
} from 'lucide-react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

// Map existing functional routes to standard names from prompt style
const navigation = [
  { name: 'Workspace', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Search', href: '/research', icon: Search },
  { name: 'Library', href: '/documents', icon: BookOpen },
  { name: 'Drive', href: '/drive', icon: HardDrive },
  { name: 'Agents', href: '/agents', icon: Bot },
  { name: 'Notes', href: '/notes', icon: StickyNote },
  { name: 'Scheduled', href: '/planner', icon: Calendar },
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
  const { isCollapsed, toggle } = useSidebar()
  
  const [conversations, setConversations] = useState<SidebarConversation[]>([])
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false)
  const [selectedWorkspace, setSelectedWorkspace] = useState('Personal Space')

  const isChatRoute = pathname === '/chat' || pathname.startsWith('/chat/')
  const [documents, setDocuments] = useState<any[]>([])
  const [loadingDocuments, setLoadingDocuments] = useState(false)
  const [currentWorkspace, setCurrentWorkspace] = useState('all')

  const fetchDocuments = useCallback(async () => {
    if (!isChatRoute) return
    setLoadingDocuments(true)
    try {
      const res = await api.documents.list(currentWorkspace === 'all' ? undefined : currentWorkspace === 'unfiled' ? '__unfiled__' : currentWorkspace)
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
  }, [isChatRoute, currentWorkspace])

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
      setCurrentWorkspace(workspaceId)
    }
    window.addEventListener('workspace-changed', handleWorkspaceChange)
    return () => window.removeEventListener('workspace-changed', handleWorkspaceChange)
  }, [])

  // Fetch recent conversations for history section
  useEffect(() => {
    if (session) {
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
    }
  }, [session, pathname])

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
  const groupConversations = () => {
    const today: SidebarConversation[] = []
    const yesterday: SidebarConversation[] = []
    const previous7Days: SidebarConversation[] = []
    const older: SidebarConversation[] = []

    const now = new Date()
    const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate())
    const yesterdayStart = new Date(todayStart)
    yesterdayStart.setDate(yesterdayStart.getDate() - 1)
    const sevenDaysAgo = new Date(todayStart)
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7)

    conversations.forEach((conv) => {
      const date = new Date(conv.createdAt)
      if (date >= todayStart) {
        today.push(conv)
      } else if (date >= yesterdayStart) {
        yesterday.push(conv)
      } else if (date >= sevenDaysAgo) {
        previous7Days.push(conv)
      } else {
        older.push(conv)
      }
    })

    return { today, yesterday, previous7Days, older }
  }

  const { today, yesterday, previous7Days, older } = groupConversations()

  const handleNewChat = () => {
    router.push('/chat')
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
            return (
              <div
                key={conv.id}
                onClick={() => router.push(`/chat?id=${conv.id}`)}
                className={cn(
                  "group relative flex items-center justify-between px-3 py-2 rounded-[8px] text-sm cursor-pointer transition-all duration-150",
                  isActive 
                    ? "bg-background text-foreground border border-border font-semibold shadow-xs" 
                    : "text-muted-foreground hover:text-foreground hover:bg-background/50"
                )}
              >
                <span className="truncate w-full pr-6 text-xs">
                  {conv.title}
                </span>

                {/* Hover actions */}
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center opacity-0 group-hover:opacity-100 transition-opacity gap-1">
                  <button 
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                    className="p-1 hover:bg-secondary rounded text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                  >
                    <Trash2 className="h-3 w-3 stroke-[1.5]" />
                  </button>
                </div>
              </div>
            )
          })}
        </div>
      </div>
    )
  }

  return (
    <aside 
      className={cn(
        "flex flex-col border-r h-full bg-secondary border-border transition-all duration-350 ease-in-out relative shrink-0 overflow-hidden overflow-x-hidden",
        isCollapsed ? "w-[68px]" : "w-[280px]"
      )}
    >
      {/* Top Header Section */}
      <div className="p-4 flex flex-col gap-4 border-b border-border shrink-0">
        <div className="flex items-center justify-between h-9">
          {isCollapsed ? (
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
                  <img src="/logo.png" alt="Agents Logo" className="h-6 w-6 object-contain" />
                </div>
                <span className="font-sans font-normal text-lg tracking-[-0.03em] text-[#26251e]">
                  Agents
                </span>
              </Link>
              <button
                onClick={toggle}
                className="p-1.5 hover:bg-card rounded-[8px] text-muted-foreground hover:text-foreground transition-colors cursor-pointer"
                title="Collapse sidebar (Ctrl+B)"
              >
                <PanelLeftClose className="h-4.5 w-4.5 stroke-[1.5]" />
              </button>
            </>
          )}
        </div>

        {/* Workspace Selector */}
        <div className={cn(
          "transition-all duration-300 ease-in-out overflow-hidden",
          isCollapsed ? "opacity-0 h-0 pointer-events-none" : "opacity-100 h-9"
        )}>
          <div className="relative">
            <button
              onClick={() => setShowWorkspaceMenu(!showWorkspaceMenu)}
              className="w-full flex items-center justify-between px-3 py-2 rounded-[8px] bg-card border border-border text-xs font-semibold text-foreground hover:bg-secondary/40 transition-colors shadow-xs cursor-pointer"
            >
              <div className="flex items-center gap-2 truncate">
                <div className="h-2 w-2 rounded-full bg-[#1f8a65]" />
                <span className="truncate">{selectedWorkspace}</span>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-muted-foreground stroke-[1.5]" />
            </button>
            
            {showWorkspaceMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowWorkspaceMenu(false)} />
                <div className="absolute top-full left-0 right-0 mt-1.5 p-1 rounded-[8px] bg-card border border-border shadow-xs z-20 space-y-0.5">
                  {['Personal Space', 'Project Alpha', 'Engineering Team'].map((space) => (
                    <button
                      key={space}
                      onClick={() => {
                        setSelectedWorkspace(space)
                        setShowWorkspaceMenu(false)
                      }}
                      className={cn(
                        "w-full text-left px-3 py-1.5 rounded-[6px] text-xs transition-colors cursor-pointer",
                        selectedWorkspace === space
                          ? "bg-secondary text-[#26251e] font-semibold"
                          : "text-muted-foreground hover:text-[#26251e] hover:bg-secondary/50"
                      )}
                    >
                      {space}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        </div>

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
            isCollapsed ? "opacity-0 w-0" : "opacity-100 w-auto"
          )}>
            New Chat
          </span>
        </button>
      </div>

      {/* Main Navigation Links */}
      <div className={cn(
        "flex-1 px-3 py-4 space-y-6",
        isCollapsed ? "overflow-hidden" : "overflow-y-auto overflow-x-hidden scrollbar-thin"
      )}>
        <div className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
            return (
              <div key={item.name} className="relative group/tooltip">
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center rounded-[8px] font-semibold text-sm transition-all duration-200 relative h-10",
                    isCollapsed 
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
                    isCollapsed ? "opacity-0 w-0" : "opacity-100 w-auto"
                  )}>
                    {item.name}
                  </span>
                </Link>

                {/* Collapsed Tooltip */}
                {isCollapsed && (
                  <div className="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-2.5 py-1.5 rounded-[6px] bg-card border border-border text-xs font-semibold text-foreground whitespace-nowrap opacity-0 pointer-events-none group-hover/tooltip:opacity-100 transition-opacity duration-150 z-50 shadow-xs">
                    {item.name}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* Documents Explorer Section (Only on Chat route and when not collapsed) */}
        {isChatRoute && !isCollapsed && (
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
          isCollapsed ? "opacity-0 h-0 pointer-events-none" : "opacity-100 h-auto pt-4 border-t border-border"
        )}>
          {conversations.length > 0 && (
            <>
              {renderHistorySection("Today", today)}
              {renderHistorySection("Yesterday", yesterday)}
              {renderHistorySection("Previous 7 Days", previous7Days)}
              {renderHistorySection("Older", older)}
            </>
          )}
        </div>
      </div>

      {/* Footer Profile Section */}
      <div className={cn("p-4 border-t border-border bg-secondary/85 shrink-0", isCollapsed ? "px-2" : "px-4")}>
        <div className={cn("flex items-center", isCollapsed ? "justify-center" : "gap-3")}>
          <div className="relative group/tooltip">
            <Avatar className="h-9 w-9 border border-border cursor-pointer shrink-0" onClick={() => router.push('/settings')}>
              <AvatarImage src={session?.user?.image ?? ''} alt={session?.user?.name ?? ''} />
              <AvatarFallback className="bg-card text-xs text-muted-foreground font-semibold uppercase">
                {session?.user?.name?.charAt(0) ?? 'U'}
              </AvatarFallback>
            </Avatar>

            {/* Collapsed profile tooltip */}
            {isCollapsed && (
              <div className="absolute left-full bottom-0 ml-3 p-3 rounded-[8px] bg-card border border-border shadow-xs z-50 flex flex-col gap-1.5 pointer-events-none opacity-0 group-hover/tooltip:opacity-100 transition-opacity duration-150">
                <span className="text-xs font-semibold text-[#26251e] whitespace-nowrap">{session?.user?.name}</span>
                <span className="text-[10px] text-muted-foreground whitespace-nowrap">{session?.user?.email}</span>
                <span className="text-[9px] bg-primary text-primary-foreground px-1.5 py-0.5 rounded-[4px] font-bold w-fit uppercase tracking-wider">
                  Pro
                </span>
              </div>
            )}
          </div>

          {!isCollapsed && (
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
  )
}
