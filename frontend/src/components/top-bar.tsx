'use client'

import { useSession, signOut } from 'next-auth/react'
import { useSidebar } from '@/context/sidebar-context'
import { clearAccessToken } from '@/lib/auth-store'
import Link from 'next/link'
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
import {
  LogOut,
  User,
  Settings,
  Bell,
  Menu,
} from 'lucide-react'

export function TopBar() {
  const { data: session } = useSession()
  const { setMobileMenuOpen } = useSidebar()

  return (
    <header className="relative flex min-h-14 w-full min-w-0 shrink-0 items-center justify-between gap-2 border-b border-border bg-secondary/80 px-2.5 pb-2 pt-[max(0.5rem,env(safe-area-inset-top))] backdrop-blur-md sm:px-4 lg:hidden">
      {/* Mobile Menu Button */}
      <div className="lg:hidden flex items-center">
        <Button 
          variant="ghost" 
          size="icon" 
          onClick={() => setMobileMenuOpen(true)}
          className="h-11 w-11 text-muted-foreground hover:bg-accent hover:text-foreground"
          aria-label="Open navigation menu"
          title="Open navigation menu"
        >
          <Menu className="h-5 w-5 stroke-[1.5]" />
        </Button>
      </div>



      {/* Right Side Header Items */}
      <div className="ml-auto flex min-w-0 items-center gap-1.5 sm:gap-2">

        <Button variant="ghost" size="icon" className="relative hidden h-11 w-11 rounded-lg text-muted-foreground hover:bg-accent min-[360px]:inline-flex" aria-label="Notifications" title="Notifications">
          <Bell className="h-4.5 w-4.5 stroke-[1.5] text-muted-foreground" />
          <span className="absolute top-2 right-2 h-1.5 w-1.5 rounded-full bg-[#5db872]" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-11 w-11 rounded-full p-1.5 hover:opacity-90" aria-label="Open account menu" title="Account menu">
              <Avatar className="h-8 w-8 border border-border">
                <AvatarImage src={session?.user?.image ?? ''} alt={session?.user?.name ?? ''} />
                <AvatarFallback className="bg-accent text-xs text-muted-foreground font-medium">
                  {session?.user?.name?.charAt(0)?.toUpperCase() ?? 'U'}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="mt-1 w-[min(14rem,calc(100vw-1rem))] border-border bg-card" align="end" sideOffset={4} collisionPadding={8}>
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
              onClick={() => {
                clearAccessToken()
                signOut({ callbackUrl: '/login' })
              }}
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
