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
    <aside className="hidden md:flex w-60 flex-col border-r bg-sidebar/50 backdrop-blur-md border-zinc-200/50 dark:border-zinc-900">
      <div className="px-6 py-7">
        <Link href="/dashboard" className="flex items-center gap-2.5 group">
          <div className="h-8 w-8 rounded-lg bg-zinc-900 dark:bg-zinc-100 flex items-center justify-center transition-transform group-hover:scale-105 duration-200">
            <Sparkles className="h-4 w-4 text-zinc-100 dark:text-zinc-900 stroke-[1.5]" />
          </div>
          <span className="font-medium text-base tracking-tight text-zinc-900 dark:text-zinc-50">AI Space</span>
        </Link>
      </div>

      <ScrollArea className="flex-1 px-4">
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
                  'w-full justify-start gap-3 px-3 py-2 h-9 rounded-md font-normal transition-all duration-150',
                  'text-zinc-500 hover:text-zinc-900 dark:text-zinc-400 dark:hover:text-zinc-100 hover:bg-zinc-100/50 dark:hover:bg-zinc-900/40',
                  isActive && 'bg-zinc-100 dark:bg-zinc-900/60 text-zinc-900 dark:text-zinc-50 font-medium border-l-2 border-zinc-900 dark:border-zinc-100 rounded-l-none pl-2.5',
                )}
              >
                <item.icon className={cn("h-4 w-4 stroke-[1.5]", isActive ? "text-zinc-900 dark:text-zinc-100" : "text-zinc-400 dark:text-zinc-500")} />
                <span className="text-xs tracking-wide">{item.name}</span>
              </Link>
            )
          })}
        </nav>
      </ScrollArea>

      <div className="p-4 border-t border-zinc-200/50 dark:border-zinc-900">
        <div className="flex items-center justify-between px-2">
          <p className="text-[10px] text-zinc-400 dark:text-zinc-650 font-mono">
            Platform v0.1
          </p>
          <span className="h-1.5 w-1.5 rounded-full bg-emerald-500" title="Connected" />
        </div>
      </div>
    </aside>
  )
}
