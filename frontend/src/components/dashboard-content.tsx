'use client'

import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

export function DashboardContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  // Workflows and Chat pages need edge-to-edge layout without outer padding or outer scrollbars
  const isFullCanvasPage = pathname === '/workflows' || pathname === '/chat'

  return (
    <main
      id="dashboard-main"
      tabIndex={-1}
      className={cn(
        'min-h-0 min-w-0 w-full flex-1 bg-background overscroll-contain',
        isFullCanvasPage
          ? 'flex flex-col overflow-hidden p-0'
          : 'overflow-y-auto p-3 sm:p-4 md:p-6 scrollbar-thin'
      )}
    >
      {children}
    </main>
  )
}
