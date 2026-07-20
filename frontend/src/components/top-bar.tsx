'use client'

import { useState } from 'react'
import { useSession, signOut } from 'next-auth/react'
import { usePathname, useRouter } from 'next/navigation'
import { useSidebar } from '@/context/sidebar-context'
import Link from 'next/link'
import Image from 'next/image'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
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
  LayoutDashboard,
  Bot,
  BookOpen,

  HardDrive,
  StickyNote,
  Search,
  Calendar,
  Workflow,
  BarChart2,
  CloudSun,
  BrainCircuit,
  GalleryVerticalEnd,
  LibraryBig,
} from 'lucide-react'

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



export function TopBar() {
  const { data: session } = useSession()
  const { setMobileMenuOpen } = useSidebar()
  const pathname = usePathname()
  const router = useRouter()

  return (
    <header className="flex items-center justify-between gap-4 px-4 sm:px-8 py-4 border-b bg-secondary/80 backdrop-blur-md border-border w-full relative">
      {/* Mobile Menu Button */}
      <div className="lg:hidden flex items-center">
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={() => setMobileMenuOpen(true)}
          className="text-muted-foreground hover:text-foreground hover:bg-accent h-9 w-9"
        >
          <Menu className="h-5 w-5 stroke-[1.5]" />
        </Button>
      </div>



      {/* Right Side Header Items */}
      <div className="flex items-center gap-3 ml-auto">
        <div className="hidden lg:block">
          <ThemeToggle />
        </div>

        <Button variant="ghost" size="icon" className="relative h-9 w-9 rounded-lg hover:bg-accent text-muted-foreground">
          <Bell className="h-4.5 w-4.5 stroke-[1.5] text-muted-foreground" />
          <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-[#5db872]" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-9 w-9 rounded-full hover:opacity-90">
              <Avatar className="h-8 w-8 border border-border">
                <AvatarImage src={session?.user?.image ?? ''} alt={session?.user?.name ?? ''} />
                <AvatarFallback className="bg-accent text-xs text-muted-foreground font-medium">
                  {session?.user?.name?.charAt(0)?.toUpperCase() ?? 'U'}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56 mt-1 border-border bg-card" align="end">
            <DropdownMenuLabel className="font-normal py-2 px-3">
              <div className="flex flex-col space-y-0.5">
                <span className="text-sm font-medium text-foreground">{session?.user?.name}</span>
                <span className="text-xs text-muted-foreground font-normal truncate">
                  {session?.user?.email}
                </span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-border" />
            <DropdownMenuItem asChild>
              <Link href="/settings" className="cursor-pointer flex items-center w-full px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground">
                <User className="mr-2 h-4 w-4 stroke-[1.5] text-muted-foreground" />
                Profile Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/settings" className="cursor-pointer flex items-center w-full px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground">
                <Settings className="mr-2 h-4 w-4 stroke-[1.5] text-muted-foreground" />
                Platform Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-border" />
            <DropdownMenuItem 
              className="cursor-pointer text-destructive focus:bg-destructive/10 focus:text-destructive flex items-center px-3 py-1.5 text-xs font-medium"
              onClick={() => signOut({ callbackUrl: '/login' })}
            >
              <LogOut className="mr-2 h-4 w-4 stroke-[1.5]" />
              Sign out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
