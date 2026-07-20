'use client'

import { useState } from 'react'
import { useSession, signOut } from 'next-auth/react'
import { usePathname } from 'next/navigation'
import Link from 'next/link'
import Image from 'next/image'
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
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const pathname = usePathname()

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

      {/* Mobile Sidebar Slide-over Drawer */}
      {mobileMenuOpen && (
        <>
          <div 
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 w-72 bg-[#efe9de] border-r border-border p-6 flex flex-col lg:hidden animate-in slide-in-from-left duration-200 shadow-lg">
            <div className="flex items-center justify-between mb-8">
              <Link href="/dashboard" className="flex items-center gap-3" onClick={() => setMobileMenuOpen(false)}>
                <div className="h-8 w-8 rounded-lg bg-card border border-border flex items-center justify-center shadow-sm">
                  <Image src="/logo.png" alt="Agents Logo" width={20} height={20} className="h-5 w-5 object-contain" />
                </div>
                <span className="font-serif font-normal text-lg text-foreground">Agents</span>
              </Link>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={() => setMobileMenuOpen(false)}
                className="text-muted-foreground hover:text-foreground hover:bg-card"
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
                      'w-full justify-start gap-3 font-normal text-muted-foreground hover:text-foreground hover:bg-card/55',
                      isActive && 'bg-card border border-border text-foreground font-medium shadow-xs',
                    )}
                  >
                    <item.icon className={cn("h-4 w-4 stroke-[1.5]", isActive ? "text-primary" : "text-muted-foreground")} />
                    {item.name}
                  </Link>
                )
              })}
            </nav>
            
            <div className="pt-4 border-t border-border text-center">
              <p className="text-xs text-muted-foreground">Agents AI Platform v0.1</p>
            </div>
          </div>
        </>
      )}

      {/* Right Side Header Items */}
      <div className="flex items-center gap-3 ml-auto">
        <ThemeToggle />

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
