'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { api } from '@/lib/api'
import { Loader2 } from 'lucide-react'

export default function JoinWorkspacePage({ params }: { params: Promise<{ id: string }> }) {
  const router = useRouter()
  const [error, setError] = useState('')

  useEffect(() => {
    params.then(({ id }) => api.workspaces.join(id).then((res) => {
      if (res.success) router.replace('/documents')
      else setError(res.error || 'Sign in to join this workspace')
    }))
  }, [params, router])

  return (
    <main className="flex min-h-screen min-h-[100svh] w-full min-w-0 items-center justify-center p-4 text-center supports-[height:100dvh]:min-h-dvh sm:p-6">
      {error ? (
        <div className="min-w-0">
          <h1 className="text-xl font-semibold">Workspace invite</h1>
          <p className="mt-2 break-words text-sm text-muted-foreground">{error}</p>
        </div>
      ) : (
        <div>
          <Loader2 className="mx-auto h-6 w-6 animate-spin text-primary" />
          <p className="mt-3 text-sm text-muted-foreground">Joining workspace…</p>
        </div>
      )}
    </main>
  )
}
