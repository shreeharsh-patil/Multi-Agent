'use client'

import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'

export function DashboardContent({ children }: { children: React.ReactNode }) {
  const pathname = usePathname()
  // Workflows and Chat pages need edge-to-edge layout without outer padding or outer scrollbars
  const isFullCanvasPage = pathname === '/workflows' || pathname === '/chat'

  return (
    <main
      className={cn(
        'flex-1 bg-background',
        isFullCanvasPage
          ? 'flex flex-col overflow-hidden p-0'
          : 'overflow-y-auto overflow-x-hidden p-3 sm:p-6 scrollbar-thin'
      )}
    >
      {children}
    </main>
  )
}
