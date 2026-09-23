import { Sidebar } from '@/components/sidebar'
import { TopBar } from '@/components/top-bar'
import { requireAuth } from '@/lib/session'
import { SidebarProvider } from '@/context/sidebar-context'
import { HealthPing } from '@/components/health-ping'
import { CommandPalette } from '@/components/command-palette'
import { DashboardContent } from '@/components/dashboard-content'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  await requireAuth()

  return (
    <SidebarProvider>
      <HealthPing />
      <CommandPalette />
      <div className="flex h-screen h-[100svh] supports-[height:100dvh]:h-dvh min-h-0 min-w-0 overflow-hidden bg-background text-foreground font-sans">
        <a href="#dashboard-main" className="sr-only fixed left-3 top-3 z-[100] rounded-md bg-card px-3 py-2 text-sm font-medium text-foreground shadow-lg ring-1 ring-border focus:not-sr-only">Skip to content</a>
        <Sidebar />
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <TopBar />
          <DashboardContent>
            {children}
          </DashboardContent>
        </div>
      </div>
    </SidebarProvider>
  )
}
