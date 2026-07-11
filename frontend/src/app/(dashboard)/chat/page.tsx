'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { api } from '@/lib/api'
import { formatBytes } from '@/lib/utils'
import { Send, Bot, User, MessageSquare, Paperclip, FileText, X, Loader2 } from 'lucide-react'

const agents = [
  { id: 'auto', name: 'Auto (Orchestrator)' },
  { id: 'knowledge', name: 'Knowledge Agent' },
  { id: 'drive', name: 'Drive Agent' },
  { id: 'notes', name: 'Notes Agent' },
  { id: 'quiz', name: 'Quiz Agent' },
  { id: 'planner', name: 'Planner Agent' },
  { id: 'research', name: 'Research Agent' },
  { id: 'coding', name: 'Coding Agent' },
  { id: 'memory', name: 'Memory Agent' },
  { id: 'tool', name: 'Tool Agent' },
]

interface Attachment {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'done' | 'error'
  documentId?: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    agentId?: string
    attachments?: Array<{ name: string; size: number }>
  }>>([])
  const [input, setInput] = useState('')
  const [selectedAgent, setSelectedAgent] = useState('auto')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [sending, setSending] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const uploadAttachment = useCallback(async (att: Attachment): Promise<Attachment> => {
    setAttachments((prev) => prev.map((a) => a.id === att.id ? { ...a, status: 'uploading' } : a))
    try {
      const res = await api.documents.upload(att.file)
      if (res.success && res.data) {
        return { ...att, status: 'done', documentId: res.data.id }
      }
      return { ...att, status: 'error' }
    } catch {
      return { ...att, status: 'error' }
    }
  }, [])

  const handleSend = useCallback(async () => {
    if ((!input.trim() && attachments.length === 0) || sending) return

    setSending(true)

    const userMsg = {
      id: crypto.randomUUID(),
      role: 'user' as const,
      content: input.trim() || `Uploaded ${attachments.length} file(s)`,
      attachments: attachments.map((a) => ({ name: a.file.name, size: a.file.size })),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setAttachments([])

    for (const att of attachments) {
      const updated = await uploadAttachment(att)
      setAttachments((prev) => prev.map((a) => a.id === att.id ? updated : a))
    }

    setMessages((prev) => [...prev, {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: 'Backend chat integration is ready. Send your message to the API at POST /api/chat.',
    }])
    setSending(false)
  }, [input, attachments, sending, uploadAttachment])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const newAttachments: Attachment[] = files.map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
    }))
    setAttachments((prev) => [...prev, ...newAttachments])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const removeAttachment = (id: string) => {
    setAttachments((prev) => prev.filter((a) => a.id !== id))
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  return (
    <div className="flex h-full gap-6 animate-fade-in">
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Chat</h1>
            <p className="text-muted-foreground mt-1">
              Upload PDFs and chat with your AI agents
            </p>
          </div>
          <Select value={selectedAgent} onValueChange={setSelectedAgent}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select agent" />
            </SelectTrigger>
            <SelectContent>
              {agents.map((agent) => (
                <SelectItem key={agent.id} value={agent.id}>
                  {agent.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Card className="flex-1 flex flex-col">
          {messages.length === 0 ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center text-muted-foreground">
                <MessageSquare className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p className="text-lg font-medium">Start a conversation</p>
                <p className="text-sm">Upload a PDF and ask questions about it</p>
              </div>
            </div>
          ) : (
            <ScrollArea ref={scrollRef} className="flex-1 p-6">
              <div className="space-y-6">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                    {msg.role === 'assistant' && (
                      <Avatar className="h-8 w-8 shrink-0">
                        <AvatarFallback className="bg-primary text-primary-foreground">
                          <Bot className="h-4 w-4" />
                        </AvatarFallback>
                      </Avatar>
                    )}
                    <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-1' : ''}`}>
                      {msg.agentId && (
                        <Badge variant="outline" className="mb-1 text-xs">
                          {agents.find((a) => a.id === msg.agentId)?.name}
                        </Badge>
                      )}
                      {msg.attachments && msg.attachments.length > 0 && (
                        <div className="flex flex-wrap gap-2 mb-2">
                          {msg.attachments.map((att, i) => (
                            <Badge key={i} variant="secondary" className="gap-1 text-xs">
                              <FileText className="h-3 w-3" />
                              {att.name} ({formatBytes(att.size)})
                            </Badge>
                          ))}
                        </div>
                      )}
                      <div
                        className={`rounded-lg px-4 py-3 text-sm ${
                          msg.role === 'user'
                            ? 'bg-primary text-primary-foreground'
                            : 'bg-secondary text-secondary-foreground'
                        }`}
                      >
                        <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
                      </div>
                    </div>
                    {msg.role === 'user' && (
                      <Avatar className="h-8 w-8 shrink-0">
                        <AvatarFallback className="bg-muted">
                          <User className="h-4 w-4" />
                        </AvatarFallback>
                      </Avatar>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}

          <div className="p-4 border-t space-y-2">
            {attachments.length > 0 && (
              <div className="flex flex-wrap gap-2">
                {attachments.map((att) => (
                  <Badge
                    key={att.id}
                    variant={att.status === 'error' ? 'destructive' : 'secondary'}
                    className="gap-1 pr-1"
                  >
                    <FileText className="h-3 w-3" />
                    {att.file.name}
                    {att.status === 'uploading' && <Loader2 className="h-3 w-3 animate-spin ml-1" />}
                    {att.status === 'pending' && (
                      <button onClick={() => removeAttachment(att.id)} className="ml-1">
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </Badge>
                ))}
              </div>
            )}
            <div className="flex gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.pptx,.txt,.md"
                multiple
                className="hidden"
                onChange={handleFileSelect}
              />
              <Button
                variant="outline"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
                disabled={sending}
              >
                <Paperclip className="h-4 w-4" />
              </Button>
              <Input
                placeholder="Ask about your documents..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1"
                disabled={sending}
              />
              <Button onClick={handleSend} disabled={sending || (!input.trim() && attachments.length === 0)} className="gap-2">
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
                Send
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <div className="hidden lg:block w-80 space-y-4">
        <Card className="p-4">
          <h3 className="font-semibold flex items-center gap-2 mb-3">
            <MessageSquare className="h-4 w-4" />
            Quick Actions
          </h3>
          <div className="space-y-2">
            <Button
              variant="outline"
              className="w-full justify-start gap-2 text-sm"
              size="sm"
              onClick={() => fileInputRef.current?.click()}
            >
              <Paperclip className="h-4 w-4" />
              Upload PDF
            </Button>
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="font-semibold mb-3">Suggestions</h3>
          <div className="space-y-2">
            {[
              'Summarize this document',
              'What are the key findings?',
              'Extract all important dates',
              'Create flashcards from this',
              'Generate a quiz from the content',
            ].map((suggestion) => (
              <Button
                key={suggestion}
                variant="ghost"
                className="w-full justify-start text-sm h-auto py-2"
                onClick={() => setInput(suggestion)}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="font-semibold mb-2 text-sm">Supported Formats</h3>
          <p className="text-xs text-muted-foreground">
            PDF · DOCX · PPTX · TXT · MD
          </p>
        </Card>
      </div>
    </div>
  )
}
