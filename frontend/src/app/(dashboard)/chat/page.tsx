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
import { Send, Bot, User, MessageSquare, Paperclip, FileText, ImageIcon, X, Loader2 } from 'lucide-react'
import type { AgentId } from '@shared/types'

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

const isImage = (file: File) => file.type.startsWith('image/')

interface Attachment {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'done' | 'error'
  documentId?: string
  previewUrl?: string
}

const isImageExt = (name: string) => /\.(png|jpg|jpeg|webp|gif|svg|bmp)$/i.test(name)

export default function ChatPage() {
  const [messages, setMessages] = useState<Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    agentId?: string
    attachments?: Array<{ name: string; size: number }>
  }>>([])
  const [input, setInput] = useState('')
  const [selectedAgent, setSelectedAgent] = useState<string>('auto')
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

  const [conversationId, setConversationId] = useState<string>()

  const handleSend = useCallback(async () => {
    if ((!input.trim() && attachments.length === 0) || sending) return

    setSending(true)

    const text = input.trim()
    const userMsg = {
      id: crypto.randomUUID(),
      role: 'user' as const,
      content: text || `Uploaded ${attachments.length} file(s)`,
      attachments: attachments.map((a) => ({ name: a.file.name, size: a.file.size })),
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')

    // Upload attachments if any
    for (const att of attachments) {
      const updated = await uploadAttachment(att)
      setAttachments((prev) => prev.map((a) => a.id === att.id ? updated : a))
    }
    setAttachments([])

    // Add placeholder assistant message (will be updated incrementally via SSE)
    const assistantId = crypto.randomUUID()
    setMessages((prev) => [...prev, { id: assistantId, role: 'assistant', content: '' }])

    try {
      const streamUrl = api.chat.streamUrl({
        message: text || `Uploaded ${attachments.length} file(s)`,
        conversation_id: conversationId,
        agent_id: selectedAgent === 'auto' ? undefined : selectedAgent as AgentId,
      })

      const response = await fetch(streamUrl)
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      const reader = response.body?.getReader()
      if (!reader) throw new Error('No reader available')

      const decoder = new TextDecoder()
      let buffer = ''
      let accumulatedContent = ''
      let receivedConversationId = conversationId

      // Read the SSE stream
      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE messages from buffer
        const lines = buffer.split('\n')
        buffer = lines.pop() || '' // Keep incomplete line in buffer

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const dataStr = line.slice(6)
            try {
              const data = JSON.parse(dataStr)

              if (currentEvent === 'chunk' && data.text) {
                accumulatedContent += data.text
                // Update the assistant message incrementally
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, content: accumulatedContent }
                      : msg,
                  ),
                )
              } else if (currentEvent === 'agent' && data.agent_id) {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, agentId: data.agent_id }
                      : msg,
                  ),
                )
              } else if (currentEvent === 'complete' && data.conversation_id) {
                receivedConversationId = data.conversation_id
                setConversationId(data.conversation_id)
                // Final update with full content
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, content: data.output || accumulatedContent }
                      : msg,
                  ),
                )
              } else if (currentEvent === 'error' && data.error) {
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, content: `Error: ${data.error}` }
                      : msg,
                  ),
                )
              }
            } catch (e) {
              // Skip malformed JSON
            }
          }
        }
      }

      // Final update with accumulated content if complete event wasn't processed
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? { ...msg, content: accumulatedContent || msg.content }
            : msg,
        ),
      )
    } catch (err) {
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? { ...msg, content: 'Network error. Ensure the backend is running on port 8000.' }
            : msg,
        ),
      )
    } finally {
      setSending(false)
    }
  }, [input, attachments, sending, uploadAttachment, conversationId, selectedAgent])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])
    const newAttachments: Attachment[] = files.map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
      previewUrl: isImage(file) ? URL.createObjectURL(file) : undefined,
    }))
    setAttachments((prev) => [...prev, ...newAttachments])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // Cleanup object URLs on unmount
  useEffect(() => {
    return () => {
      attachments.forEach((a) => { if (a.previewUrl) URL.revokeObjectURL(a.previewUrl) })
    }
  }, [])

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
              Upload documents, images, and chat with your AI agents
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
                <p className="text-sm">Upload documents or images and ask questions</p>
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
                              {isImageExt(att.name) ? <ImageIcon className="h-3 w-3" /> : <FileText className="h-3 w-3" />}
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
                  <div
                    key={att.id}
                    className={`flex items-center gap-2 rounded-md border px-2 py-1 text-xs ${
                      att.status === 'error' ? 'border-destructive' : ''
                    }`}
                  >
                    {att.previewUrl ? (
                      <img
                        src={att.previewUrl}
                        alt={att.file.name}
                        className="h-8 w-8 rounded object-cover"
                      />
                    ) : (
                      <FileText className="h-4 w-4 text-muted-foreground" />
                    )}
                    <span className="max-w-[120px] truncate">{att.file.name}</span>
                    {att.status === 'uploading' && <Loader2 className="h-3 w-3 animate-spin shrink-0" />}
                    {att.status === 'pending' && (
                      <button onClick={() => removeAttachment(att.id)} className="shrink-0">
                        <X className="h-3 w-3 hover:text-destructive" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
            <div className="flex gap-3">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.pptx,.txt,.md,.png,.jpg,.jpeg,.webp,.gif"
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
                placeholder="Ask about your documents or images..."
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
              Upload Files
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
            PDF · DOCX · PPTX · TXT · MD · PNG · JPG · WEBP
          </p>
        </Card>
      </div>
    </div>
  )
}
