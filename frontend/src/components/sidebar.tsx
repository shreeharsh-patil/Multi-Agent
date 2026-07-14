'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import { buttonVariants } from '@/components/ui/button'
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
  HardDrive,
  Settings,
  Sparkles,
} from 'lucide-react'

const navigation = [
  { name: 'Dashboard', href: '/dashboard', icon: LayoutDashboard },
  { name: 'Agents', href: '/agents', icon: Bot },
  { name: 'Chat', href: '/chat', icon: MessageSquare },
  { name: 'Knowledge Base', href: '/knowledge-base', icon: BookOpen },
  { name: 'Documents', href: '/documents', icon: FileText },
  { name: 'Drive', href: '/drive', icon: HardDrive },
  { name: 'Notes', href: '/notes', icon: StickyNote },
  { name: 'Research', href: '/research', icon: Search },
  { name: 'Planner', href: '/planner', icon: Calendar },
  { name: 'Settings', href: '/settings', icon: Settings },
]

export function Sidebar() {
  const pathname = usePathname()

  return (
    <aside className="hidden md:flex w-64 flex-col border-r bg-sidebar border-zinc-200 dark:border-zinc-800">
      <div className="p-6">
        <Link href="/dashboard" className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-primary-foreground stroke-[1.5]" />
          </div>
          <span className="font-semibold text-lg tracking-tight">AI Platform</span>
        </Link>
      </div>

      <ScrollArea className="flex-1 px-3">
        <nav className="space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
            return (
              <Link
                key={item.name}
                href={item.href}
                aria-current={isActive ? 'page' : undefined}
                className={cn(
                  buttonVariants({ variant: 'ghost' }),
                  'w-full justify-start gap-3 font-normal text-zinc-500 dark:text-zinc-400 hover:text-zinc-950 dark:hover:text-zinc-50',
                  isActive && 'bg-sidebar-accent text-sidebar-accent-foreground font-medium text-zinc-950 dark:text-zinc-50',
                )}
              >
                <item.icon className="h-4 w-4 stroke-[1.5]" />
                {item.name}
              </Link>
            )
          })}
        </nav>
      </ScrollArea>

      <div className="p-4 border-t border-zinc-200 dark:border-zinc-850">
        <p className="text-[10px] text-zinc-400 dark:text-zinc-500 font-mono text-center">
          Multi-Agent AI Platform v0.1
        </p>
      </div>
    </aside>
  )
}
