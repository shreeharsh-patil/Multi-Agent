'use client'

import { useEffect } from 'react'
import { AlertCircle, RotateCcw } from 'lucide-react'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Button } from '@/components/ui/button'

export default function ErrorPage({ error, reset }: { error: Error & { digest?: string }; reset: () => void }) {
  useEffect(() => {
    console.error('Unhandled application error', error)
  }, [error])

  return (
    <main className="flex min-h-[60vh] items-center justify-center px-4 py-10">
      <div className="w-full max-w-lg space-y-4">
        <Alert variant="destructive">
          <AlertCircle className="h-4 w-4" />
          <AlertTitle>Something went wrong</AlertTitle>
          <AlertDescription>
            The page could not finish loading. Your saved data has not been changed. Try the request again.
          </AlertDescription>
        </Alert>
        <Button type="button" onClick={reset} className="gap-2">
          <RotateCcw className="h-4 w-4" />
          Try again
        </Button>
      </div>
    </main>
  )
}
