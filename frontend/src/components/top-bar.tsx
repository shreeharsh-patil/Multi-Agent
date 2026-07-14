'use client'

import { useState } from 'react'
import { useSession, signOut } from 'next-auth/react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { cn } from '@/lib/utils'
import { Button, buttonVariants } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Avatar, AvatarFallback, AvatarImage } from '@/components/ui/avatar'
import { ThemeToggle } from '@/components/theme-toggle'
import {
  LogOut,
  User,
  Settings,
  Bell,
  Menu,
  X,
  Sparkles,
  LayoutDashboard,
  Bot,
  MessageSquare,
  BookOpen,
  FileText,
  HardDrive,
  StickyNote,
  Search,
  Calendar,
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

export function TopBar() {
  const { data: session } = useSession()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const pathname = usePathname()

  return (
    <header className="flex items-center justify-between gap-4 px-6 py-3 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 w-full relative">
      {/* Mobile Menu Button */}
      <div className="md:hidden flex items-center">
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={() => setMobileMenuOpen(true)}
          className="text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 h-9 w-9"
        >
          <Menu className="h-5 w-5 stroke-[1.5]" />
        </Button>
      </div>

      {/* Mobile Sidebar Slide-over Drawer */}
      {mobileMenuOpen && (
        <>
          <div 
            className="fixed inset-0 z-50 bg-black/60 backdrop-blur-xs md:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 w-72 bg-zinc-950 border-r border-zinc-800 p-6 flex flex-col md:hidden animate-in slide-in-from-left duration-200">
            <div className="flex items-center justify-between mb-8">
              <Link href="/dashboard" className="flex items-center gap-3" onClick={() => setMobileMenuOpen(false)}>
                <div className="h-8 w-8 rounded-lg bg-primary flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-primary-foreground" />
                </div>
                <span className="font-semibold text-lg text-white">AI Platform</span>
              </Link>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={() => setMobileMenuOpen(false)}
                className="text-zinc-400 hover:text-white"
              >
                <X className="h-5 w-5 stroke-[1.5]" />
              </Button>
            </div>
            
            <nav className="flex-1 space-y-1.5 overflow-y-auto scrollbar-thin pr-1">
              {navigation.map((item) => {
                const isActive = pathname === item.href || pathname.startsWith(item.href + '/')
                return (
                  <Link
                    key={item.name}
                    href={item.href}
                    onClick={() => setMobileMenuOpen(false)}
                    className={cn(
                      buttonVariants({ variant: 'ghost' }),
                      'w-full justify-start gap-3 font-normal text-zinc-400 hover:text-white hover:bg-zinc-900',
                      isActive && 'bg-zinc-900 text-white font-medium',
                    )}
                  >
                    <item.icon className="h-4 w-4 stroke-[1.5]" />
                    {item.name}
                  </Link>
                )
              })}
            </nav>
            
            <div className="pt-4 border-t border-zinc-900 text-center">
              <p className="text-xs text-zinc-500">Multi-Agent AI Platform v0.1</p>
            </div>
          </div>
        </>
      )}

      {/* Right Side Header Items */}
      <div className="flex items-center gap-3 ml-auto">
        <ThemeToggle />

        <Button variant="ghost" size="icon" className="relative">
          <Bell className="h-5 w-5 stroke-[1.5]" />
          <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-destructive" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-9 w-9 rounded-full">
              <Avatar className="h-9 w-9">
                <AvatarImage src={session?.user?.image ?? ''} alt={session?.user?.name ?? ''} />
                <AvatarFallback>
                  {session?.user?.name?.charAt(0)?.toUpperCase() ?? 'U'}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56" align="end">
            <DropdownMenuLabel>
              <div className="flex flex-col">
                <span>{session?.user?.name}</span>
                <span className="text-xs text-muted-foreground font-normal">
                  {session?.user?.email}
                </span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem>
              <User className="mr-2 h-4 w-4 stroke-[1.5]" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem>
              <Settings className="mr-2 h-4 w-4 stroke-[1.5]" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => signOut({ callbackUrl: '/login' })}>
              <LogOut className="mr-2 h-4 w-4 stroke-[1.5]" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}

