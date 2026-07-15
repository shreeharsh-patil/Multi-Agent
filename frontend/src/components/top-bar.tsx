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

function LogoSpike({ className = "h-4 w-4" }: { className?: string }) {
  return (
    <svg className={cn("text-[#cc785c] fill-current shrink-0", className)} viewBox="0 0 24 24">
      <path d="M12 2c.4 3.5 1.5 6.5 4 9 2.5 2.5 5.5 3.6 9 4-3.5.4-6.5 1.5-9 4-2.5 2.5-3.6 5.5-4 9-.4-3.5-1.5-6.5-4-9-2.5-2.5-5.5-3.6-9-4 3.5-.4 6.5-1.5 9-4 2.5-2.5 3.6-5.5 4-9z" />
    </svg>
  )
}

export function TopBar() {
  const { data: session } = useSession()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const pathname = usePathname()

  return (
    <header className="flex items-center justify-between gap-4 px-8 py-4 border-b bg-[#faf9f5]/80 backdrop-blur-md border-[#e6dfd8] w-full relative">
      {/* Mobile Menu Button */}
      <div className="md:hidden flex items-center">
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={() => setMobileMenuOpen(true)}
          className="text-[#6c6a64] hover:text-[#141413] hover:bg-[#efe9de] h-9 w-9"
        >
          <Menu className="h-5 w-5 stroke-[1.5]" />
        </Button>
      </div>

      {/* Mobile Sidebar Slide-over Drawer */}
      {mobileMenuOpen && (
        <>
          <div 
            className="fixed inset-0 z-50 bg-black/40 backdrop-blur-xs md:hidden"
            onClick={() => setMobileMenuOpen(false)}
          />
          <div className="fixed inset-y-0 left-0 z-50 w-72 bg-[#efe9de] border-r border-[#e6dfd8] p-6 flex flex-col md:hidden animate-in slide-in-from-left duration-200">
            <div className="flex items-center justify-between mb-8">
              <Link href="/dashboard" className="flex items-center gap-3" onClick={() => setMobileMenuOpen(false)}>
                <div className="h-8 w-8 rounded-lg bg-[#faf9f5] border border-[#e6dfd8] flex items-center justify-center shadow-sm">
                  <LogoSpike className="h-4.5 w-4.5" />
                </div>
                <span className="font-serif font-normal text-lg text-[#141413]">Agents</span>
              </Link>
              <Button 
                variant="ghost" 
                size="icon" 
                onClick={() => setMobileMenuOpen(false)}
                className="text-[#6c6a64] hover:text-[#141413] hover:bg-[#faf9f5]"
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
                      'w-full justify-start gap-3 font-normal text-[#6c6a64] hover:text-[#141413] hover:bg-[#faf9f5]/55',
                      isActive && 'bg-[#faf9f5] border border-[#e6dfd8] text-[#141413] font-medium shadow-xs',
                    )}
                  >
                    <item.icon className={cn("h-4 w-4 stroke-[1.5]", isActive ? "text-[#cc785c]" : "text-[#6c6a64]")} />
                    {item.name}
                  </Link>
                )
              })}
            </nav>
            
            <div className="pt-4 border-t border-[#e6dfd8] text-center">
              <p className="text-xs text-[#6c6a64]">Agents AI Platform v0.1</p>
            </div>
          </div>
        </>
      )}

      {/* Right Side Header Items */}
      <div className="flex items-center gap-3 ml-auto">
        <ThemeToggle />

        <Button variant="ghost" size="icon" className="relative h-9 w-9 rounded-lg hover:bg-[#efe9de] text-[#6c6a64]">
          <Bell className="h-4.5 w-4.5 stroke-[1.5] text-[#6c6a64]" />
          <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-[#5db872]" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-9 w-9 rounded-full hover:opacity-90">
              <Avatar className="h-8 w-8 border border-[#e6dfd8]">
                <AvatarImage src={session?.user?.image ?? ''} alt={session?.user?.name ?? ''} />
                <AvatarFallback className="bg-[#efe9de] text-xs text-[#6c6a64] font-medium">
                  {session?.user?.name?.charAt(0)?.toUpperCase() ?? 'U'}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="w-56 mt-1 border-[#e6dfd8] bg-[#faf9f5]" align="end">
            <DropdownMenuLabel className="font-normal py-2 px-3">
              <div className="flex flex-col space-y-0.5">
                <span className="text-sm font-medium text-[#141413]">{session?.user?.name}</span>
                <span className="text-xs text-[#6c6a64] font-normal truncate">
                  {session?.user?.email}
                </span>
              </div>
            </DropdownMenuLabel>
            <DropdownMenuSeparator className="bg-[#e6dfd8]" />
            <DropdownMenuItem asChild>
              <Link href="/settings" className="cursor-pointer flex items-center w-full px-3 py-1.5 text-xs text-[#6c6a64] hover:text-[#141413]">
                <User className="mr-2 h-4 w-4 stroke-[1.5] text-[#6c6a64]" />
                Profile Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuItem asChild>
              <Link href="/settings" className="cursor-pointer flex items-center w-full px-3 py-1.5 text-xs text-[#6c6a64] hover:text-[#141413]">
                <Settings className="mr-2 h-4 w-4 stroke-[1.5] text-[#6c6a64]" />
                Platform Settings
              </Link>
            </DropdownMenuItem>
            <DropdownMenuSeparator className="bg-[#e6dfd8]" />
            <DropdownMenuItem 
              className="cursor-pointer text-[#c64545] focus:bg-[#c64545]/10 focus:text-[#c64545] flex items-center px-3 py-1.5 text-xs font-medium"
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
