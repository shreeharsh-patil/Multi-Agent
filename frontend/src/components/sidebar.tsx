'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import {
  LayoutDashboard,
  Bot,
  MessageSquare,
  BookOpen,
  FileText,
  StickyNote,
  Search,
  Calendar,
  Settings,
  Sparkles,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Agents', href: '/agents', icon: Bot },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Knowledge Base', href: '/knowledge-base', icon: BookOpen },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Notes', href: '/notes', icon: StickyNote },
  { name: 'Research', href: '/research', icon: Search },
  { name: 'Planner', href: '/planner', icon: Calendar },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="hidden md:flex w-64 flex-col border-r bg-sidebar">
      <div className="p-6">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="font-semibold text-lg">AI Platform</span>
        </Link>
      </div>

      <ScrollArea className="flex-1 px-3">
        <nav className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
            return (
              <Link key={item.name} href={item.href}>
                <Button
                  variant="ghost"
                  className={cn(
                    'w-full justify-start gap-3 font-normal',
                    isActive && 'bg-sidebar-accent text-sidebar-accent-foreground font-medium',
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.name}
                </Button>
              </Link>
            )
          })}
        </nav>
      </ScrollArea>

      <div className="p-4 border-t">
        <p className="text-xs text-muted-foreground text-center">
          Multi-Agent AI Platform v0.1
        </p>
      </div>
    </aside>
  )
}
