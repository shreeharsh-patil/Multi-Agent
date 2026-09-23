import { Skeleton } from '@/components/ui/skeleton'

export default function DashboardLoading() {
  return (
    <div className="mx-auto w-full max-w-7xl space-y-6 py-2 sm:py-4" aria-label="Loading workspace">
      <div className="space-y-3">
        <Skeleton className="h-6 w-36 rounded-full" />
        <Skeleton className="h-10 w-56" />
        <Skeleton className="h-4 w-full max-w-lg" />
      </div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {[0, 1, 2, 3].map((item) => <Skeleton key={item} className="h-36 rounded-xl" />)}
      </div>
      <Skeleton className="h-72 w-full rounded-xl" />
    </div>
  )
}
