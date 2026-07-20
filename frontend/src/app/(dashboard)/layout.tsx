import { Sidebar } from '@/components/sidebar'
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
      <div className="flex h-screen overflow-hidden bg-background text-foreground font-sans">
        <Sidebar />
        <div className="flex flex-col flex-1 overflow-hidden">
          <DashboardContent>
            {children}
          </DashboardContent>
        </div>
      </div>
    </SidebarProvider>
  )
}
