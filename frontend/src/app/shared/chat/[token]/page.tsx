'use client'

import { useEffect, useState } from 'react'
import { api } from '@/lib/api'
import { Card } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Loader2, MessageSquare } from 'lucide-react'
import { formatDate } from '@/lib/utils'

export default function SharedChatPage({ params }: { params: Promise<{ token: string }> }) {
  const [chat, setChat] = useState<Awaited<ReturnType<typeof api.shares.chat>>['data']>()
  const [error, setError] = useState('')

  useEffect(() => {
    params.then(({ token }) => api.shares.chat(token).then((res) => {
      if (res.success) setChat(res.data)
      else setError(res.error || 'This share link is unavailable')
    }))
  }, [params])

  if (error) {
    return (
      <main className="mx-auto flex min-h-screen min-h-[100svh] w-full min-w-0 max-w-2xl items-center justify-center p-3 supports-[height:100dvh]:min-h-dvh sm:p-6">
        <Card className="p-5 text-center sm:p-8">
          <MessageSquare className="mx-auto mb-3 h-10 w-10 text-muted-foreground" />
          <h1 className="text-xl font-semibold">Link unavailable</h1>
          <p className="mt-2 break-words text-sm text-muted-foreground">{error}</p>
        </Card>
      </main>
    )
  }

  if (!chat) {
    return (
      <main className="flex min-h-screen min-h-[100svh] items-center justify-center supports-[height:100dvh]:min-h-dvh">
        <Loader2 className="h-6 w-6 animate-spin text-primary" />
      </main>
    )
  }

  return (
    <main className="mx-auto min-h-screen min-h-[100svh] w-full min-w-0 max-w-3xl px-3 py-6 supports-[height:100dvh]:min-h-dvh sm:p-8">
      <div className="mb-6 min-w-0 sm:mb-8">
        <Badge variant="outline">Shared conversation</Badge>
        <h1 className="mt-3 break-words text-2xl font-bold tracking-tight sm:text-3xl">{chat.title}</h1>
        <p className="mt-2 text-sm text-muted-foreground">Read-only link · updated {formatDate(chat.updatedAt)}</p>
      </div>
      <Card className="min-w-0 max-w-full space-y-5 overflow-hidden p-3 sm:space-y-6 sm:p-8">
        {chat.messages.map((message, index) => (
          <div key={index} className={`flex w-full max-w-full min-w-0 overflow-hidden gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}>
            <div className={`min-w-0 max-w-[92%] overflow-hidden rounded-xl px-3 py-3 text-sm sm:max-w-[85%] sm:px-4 ${message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'}`}>
              <p className="mb-1 text-[10px] font-semibold uppercase tracking-wider opacity-60">
                {message.role === 'user' ? 'You' : message.agentId || 'Assistant'}
              </p>
              <pre className="max-w-full whitespace-pre-wrap break-words font-sans [overflow-wrap:anywhere]">{message.content}</pre>
            </div>
          </div>
        ))}
      </Card>
    </main>
  )
}
