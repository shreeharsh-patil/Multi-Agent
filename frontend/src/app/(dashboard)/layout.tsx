import { Sidebar } from '@/components/sidebar'
import { TopBar } from '@/components/top-bar'
import { requireAuth } from '@/lib/session'
import { SidebarProvider } from '@/context/sidebar-context'

export default async function DashboardLayout({
  children,
}: {
  children: React.ReactNode
}) {
  await requireAuth()

  return (
    <SidebarProvider>
      <div className="flex h-screen overflow-hidden bg-background text-foreground">
        <Sidebar />
        <div className="flex flex-col flex-1 overflow-hidden">
          <TopBar />
          <main className="flex-1 overflow-y-auto overflow-x-hidden p-6 scrollbar-thin bg-background">
            {children}
          </main>
        </div>
      </div>
    </SidebarProvider>
  )
}
