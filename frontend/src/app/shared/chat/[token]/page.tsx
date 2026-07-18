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

  if (error) return <main className="mx-auto flex min-h-screen max-w-2xl items-center justify-center p-6"><Card className="p-8 text-center"><MessageSquare className="mx-auto mb-3 h-10 w-10 text-muted-foreground" /><h1 className="text-xl font-semibold">Link unavailable</h1><p className="mt-2 text-sm text-muted-foreground">{error}</p></Card></main>
  if (!chat) return <main className="flex min-h-screen items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></main>
  return <main className="mx-auto min-h-screen max-w-3xl p-4 py-10 sm:p-8"><div className="mb-8"><Badge variant="outline">Shared conversation</Badge><h1 className="mt-3 text-3xl font-bold tracking-tight">{chat.title}</h1><p className="mt-2 text-sm text-muted-foreground">Read-only link · updated {formatDate(chat.updatedAt)}</p></div><Card className="space-y-6 p-4 sm:p-8">{chat.messages.map((message, index) => <div key={index} className={`flex gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}><div className={`max-w-[85%] rounded-xl px-4 py-3 text-sm ${message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'}`}><p className="mb-1 text-[10px] font-semibold uppercase tracking-wider opacity-60">{message.role === 'user' ? 'You' : message.agentId || 'Assistant'}</p><pre className="whitespace-pre-wrap font-sans">{message.content}</pre></div></div>)}</Card></main>
}
