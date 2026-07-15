'use client'

import React, { useState, useEffect } from 'react'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useSession } from 'next-auth/react'
import { cn } from '@/lib/utils'
import { useSidebar } from '@/context/sidebar-context'
import { api } from '@/lib/api'
import {
  LayoutDashboard,
  Bot,
  MessageSquare,
  BookOpen,
  FileText,
  StickyNote,
  Search,
  Calendar,
  HardDrive,
  Settings,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  Plus,
  ChevronDown,
  Trash2,
  Pin,
  Edit3,
  MoreHorizontal
} from 'lucide-react'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'

// Map existing functional routes to standard names from prompt style
const navigation = [
  { name: 'Workspace', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Search', href: '/research', icon: Search },
  { name: 'Library', href: '/documents', icon: BookOpen },
  { name: 'Drive', href: '/drive', icon: HardDrive },
  { name: 'Agents / Plugins', href: '/agents', icon: Bot },
  { name: 'Notes', href: '/notes', icon: StickyNote },
  { name: 'Scheduled / Planner', href: '/planner', icon: Calendar },
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
  const { isCollapsed, toggle, setCollapsed } = useSidebar()
  
  const [conversations, setConversations] = useState<SidebarConversation[]>([])
  const [showWorkspaceMenu, setShowWorkspaceMenu] = useState(false)
  const [selectedWorkspace, setSelectedWorkspace] = useState('Personal Space')

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
      }
    }
  }

  const renderHistorySection = (title: string, list: SidebarConversation[]) => {
    if (list.length === 0) return null
    return (
      <div className="space-y-1 mb-4">
        <h4 className="px-3 text-[10px] font-semibold text-[#71717A] uppercase tracking-wider select-none">
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
                  "group relative flex items-center justify-between px-3 py-2 rounded-[12px] text-sm cursor-pointer transition-all duration-150",
                  isActive 
                    ? "bg-[#1A1A1D] text-[#F5F5F7] border border-[#2A2A2F]" 
                    : "text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1A1A1D]/60"
                )}
              >
                <span className="truncate w-full pr-6 font-medium text-xs">
                  {conv.title}
                </span>

                {/* Hover actions */}
                <div className="absolute right-2 top-1/2 -translate-y-1/2 flex items-center opacity-0 group-hover:opacity-100 transition-opacity gap-1">
                  <button 
                    onClick={(e) => handleDeleteConversation(conv.id, e)}
                    className="p-1 hover:bg-[#232326] rounded text-[#71717A] hover:text-white transition-colors"
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
        "hidden md:flex flex-col border-r h-full bg-[#111111] border-[#2A2A2F] transition-all duration-250 ease-in-out relative shrink-0",
        isCollapsed ? "w-[68px]" : "w-[300px]"
      )}
    >

      {/* Top Header Section */}
      <div className="p-4 flex flex-col gap-4 border-b border-[#2A2A2F]">
        <div className={cn("flex items-center", isCollapsed ? "justify-center" : "justify-between")}>
          <Link href="/dashboard" className="flex items-center gap-2.5 group">
            <div className="h-9 w-9 rounded-[12px] border border-[#2A2A2F] bg-[#1A1A1D] flex items-center justify-center transition-all group-hover:scale-105 duration-200">
              <Sparkles className="h-4 w-4 text-white stroke-[1.25]" />
            </div>
            {!isCollapsed && (
              <span className="font-semibold text-[15px] tracking-tight text-[#F5F5F7]">
                AI Workspace
              </span>
            )}
          </Link>
        </div>

        {/* Workspace Selector */}
        {!isCollapsed && (
          <div className="relative">
            <button
              onClick={() => setShowWorkspaceMenu(!showWorkspaceMenu)}
              className="w-full flex items-center justify-between px-3 py-2 rounded-[12px] bg-[#1A1A1D] border border-[#2A2A2F] text-xs font-medium text-[#F5F5F7] hover:bg-[#232326] transition-colors"
            >
              <div className="flex items-center gap-2 truncate">
                <div className="h-2 w-2 rounded-full bg-emerald-500" />
                <span className="truncate">{selectedWorkspace}</span>
              </div>
              <ChevronDown className="h-3.5 w-3.5 text-[#71717A] stroke-[1.5]" />
            </button>
            
            {showWorkspaceMenu && (
              <>
                <div className="fixed inset-0 z-10" onClick={() => setShowWorkspaceMenu(false)} />
                <div className="absolute top-full left-0 right-0 mt-1.5 p-1 rounded-[12px] bg-[#1A1A1D] border border-[#2A2A2F] shadow-lg z-20 space-y-0.5">
                  {['Personal Space', 'Project Alpha', 'Engineering Team'].map((space) => (
                    <button
                      key={space}
                      onClick={() => {
                        setSelectedWorkspace(space)
                        setShowWorkspaceMenu(false)
                      }}
                      className={cn(
                        "w-full text-left px-3 py-1.5 rounded-[8px] text-xs transition-colors",
                        selectedWorkspace === space
                          ? "bg-[#232326] text-white"
                          : "text-[#A1A1AA] hover:text-white hover:bg-[#232326]/60"
                      )}
                    >
                      {space}
                    </button>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* New Chat Button */}
        <button
          onClick={handleNewChat}
          className={cn(
            "flex items-center justify-center gap-2 rounded-[16px] border border-[#2A2A2F] text-[14px] font-medium text-white transition-all active:scale-[0.98]",
            isCollapsed 
              ? "h-9 w-9 bg-[#1A1A1D] hover:bg-[#232326]" 
              : "w-full py-2.5 bg-[#1A1A1D] hover:bg-[#232326]"
          )}
          title="New Chat"
        >
          <Plus className="h-4 w-4 stroke-[1.5]" />
          {!isCollapsed && <span>New Chat</span>}
        </button>
      </div>

      {/* Main Navigation Links */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-6 scrollbar-thin">
        <div className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
            return (
              <div key={item.name} className="relative group/tooltip">
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 px-3 py-2.5 rounded-[12px] font-medium text-[15px] transition-all duration-150 relative",
                    isCollapsed ? "justify-center px-0 h-10 w-10 mx-auto" : "w-full h-10",
                    isActive 
                      ? "bg-[#1A1A1D] text-white border border-[#2A2A2F]" 
                      : "text-[#A1A1AA] hover:text-[#F5F5F7] hover:bg-[#1A1A1D]/60"
                  )}
                >
                  <item.icon className={cn("h-4.5 w-4.5 stroke-[1.5] shrink-0", isActive ? "text-white" : "text-[#71717A] group-hover/tooltip:text-[#F5F5F7]")} />
                  {!isCollapsed && <span className="truncate">{item.name}</span>}
                </Link>

                {/* Collapsed Tooltip */}
                {isCollapsed && (
                  <div className="absolute left-full top-1/2 -translate-y-1/2 ml-3 px-2.5 py-1.5 rounded-[8px] bg-[#232326] border border-[#2A2A2F] text-xs font-medium text-[#F5F5F7] whitespace-nowrap opacity-0 pointer-events-none group-hover/tooltip:opacity-100 transition-opacity duration-150 z-50 shadow-lg">
                    {item.name}
                  </div>
                )}
              </div>
            )
          })}
        </div>

        {/* History / Conversations Section (Hidden when collapsed) */}
        {!isCollapsed && conversations.length > 0 && (
          <div className="pt-4 border-t border-[#2A2A2F]/60">
            {renderHistorySection("Today", today)}
            {renderHistorySection("Yesterday", yesterday)}
            {renderHistorySection("Previous 7 Days", previous7Days)}
            {renderHistorySection("Older", older)}
          </div>
        )}
      </div>

      {/* Footer Profile Section */}
      <div className="p-4 border-t border-[#2A2A2F] bg-[#0B0B0D]/30">
        <div className={cn("flex items-center", isCollapsed ? "justify-center" : "gap-3")}>
          <div className="relative group/tooltip">
            <Avatar className="h-9 w-9 border border-[#2A2A2F] cursor-pointer" onClick={() => router.push('/settings')}>
              <AvatarImage src={session?.user?.image ?? ''} alt={session?.user?.name ?? ''} />
              <AvatarFallback className="bg-[#1A1A1D] text-xs text-[#A1A1AA] font-semibold uppercase">
                {session?.user?.name?.charAt(0) ?? 'U'}
              </AvatarFallback>
            </Avatar>

            {/* Collapsed profile tooltip */}
            {isCollapsed && (
              <div className="absolute left-full bottom-0 ml-3 p-3 rounded-[12px] bg-[#1A1A1D] border border-[#2A2A2F] shadow-lg z-50 flex flex-col gap-1.5 pointer-events-none opacity-0 group-hover/tooltip:opacity-100 transition-opacity duration-150">
                <span className="text-xs font-semibold text-white whitespace-nowrap">{session?.user?.name}</span>
                <span className="text-[10px] text-[#71717A] whitespace-nowrap">{session?.user?.email}</span>
                <span className="text-[9px] bg-white text-black px-1.5 py-0.5 rounded-[4px] font-bold w-fit uppercase">
                  Pro
                </span>
              </div>
            )}
          </div>

          {!isCollapsed && (
            <div className="flex-1 min-w-0 flex items-center justify-between">
              <div className="flex flex-col min-w-0">
                <div className="flex items-center gap-1.5">
                  <span className="text-[13px] font-semibold text-[#F5F5F7] truncate leading-tight">
                    {session?.user?.name}
                  </span>
                  <span className="px-1.5 py-0.5 rounded-[6px] bg-white text-black text-[9px] font-black tracking-wider uppercase select-none">
                    Pro
                  </span>
                </div>
                <span className="text-[11px] text-[#71717A] truncate">
                  {session?.user?.email}
                </span>
              </div>
              
              <Link 
                href="/settings"
                className="p-1.5 hover:bg-[#1A1A1D] rounded-[8px] text-[#71717A] hover:text-white transition-colors"
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
