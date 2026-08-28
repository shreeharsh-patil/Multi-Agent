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
