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
import { Send, Bot, User, MessageSquare, Paperclip, FileText, ImageIcon, X, Loader2, Upload } from 'lucide-react'
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
  imageUrl?: string
  previewUrl?: string
}

const isImageExt = (name: string) => /\.(png|jpg|jpeg|webp|gif|svg|bmp)$/i.test(name)

export default function ChatPage() {
  const [messages, setMessages] = useState<Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    agentId?: string
    attachments?: Array<{ name: string; size: number; documentId?: string }>
  }>>([])
  const [input, setInput] = useState('')
  const [selectedAgent, setSelectedAgent] = useState<string>('auto')
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [sending, setSending] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const dropZoneRef = useRef<HTMLDivElement>(null)

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
        return { ...att, status: 'done', documentId: res.data.id, imageUrl: res.data.imageUrl }
      }
      return { ...att, status: 'error' }
    } catch {
      return { ...att, status: 'error' }
    }
  }, [])

  const [conversationId, setConversationId] = useState<string>()
  const [conversations, setConversations] = useState<Array<{
    id: string
    title: string
    agentId?: string
    messageCount: number
    lastMessage: string
    updatedAt: string
  }>>([])
  const [loadingConversations, setLoadingConversations] = useState(true)
  const [chatTitle, setChatTitle] = useState('')

  // Fetch conversations list
  const fetchConversations = useCallback(async () => {
    setLoadingConversations(true)
    try {
      const res = await api.chat.listConversations()
      if (res.success && res.data) {
        setConversations(res.data)
      }
    } catch (e) {
      // Silently fail
    } finally {
      setLoadingConversations(false)
    }
  }, [])

  useEffect(() => {
    fetchConversations()
  }, [fetchConversations])

  // Load a conversation's messages
  const loadConversation = useCallback(async (id: string) => {
    try {
      const res = await api.chat.getConversation(id)
      if (res.success && res.data) {
        setConversationId(res.data.id)
        setChatTitle(res.data.title)
        setMessages(res.data.messages.map((m) => ({
          id: m.id,
          role: m.role as 'user' | 'assistant',
          content: m.content,
          agentId: m.agentId,
          attachments: (m.metadata as { attachments?: Array<{ name: string; size: number; documentId?: string }> } | undefined)?.attachments,
        })))
      }
    } catch (e) {
      // Silently fail
    }
  }, [])

  // Start a new conversation
  const startNewConversation = useCallback(() => {
    setConversationId(undefined)
    setChatTitle('')
    setMessages([])
  }, [])

  const handleSend = useCallback(async () => {
    if ((!input.trim() && attachments.length === 0) || sending) return

    const text = input.trim()
    const attachmentCount = attachments.length
    const currentConvId = conversationId
    const currentAgent = selectedAgent === 'auto' ? undefined : selectedAgent as AgentId

    setSending(true)

    // Upload attachments first, collecting results
    const uploadedAttachments: Array<{ name: string; size: number; documentId?: string }> = []
    for (const att of attachments) {
      const updated = await uploadAttachment(att)
      setAttachments((prev) => prev.map((a) => a.id === att.id ? updated : a))
      uploadedAttachments.push({
        name: att.file.name,
        size: att.file.size,
        documentId: updated.documentId,
      })
    }
    setAttachments([])

    const userMsg = {
      id: crypto.randomUUID(),
      role: 'user' as const,
      content: text || `Uploaded ${attachmentCount} file(s)`,
      attachments: uploadedAttachments,
    }
    setMessages((prev) => [...prev, userMsg])
    setInput('')

    // Add placeholder assistant message (will be updated incrementally via SSE)
    const assistantId = crypto.randomUUID()
    setMessages((prev) => [...prev, { id: assistantId, role: 'assistant', content: '' }])

    // Try SSE streaming first, fall back to non-streaming
    let streamingAttempted = false

    try {
      const streamResponse = await api.chat.stream({
        message: text || `Uploaded ${attachmentCount} file(s)`,
        conversation_id: currentConvId,
        agent_id: currentAgent,
        attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
      })

      if (!streamResponse.ok) {
        throw new Error(`HTTP ${streamResponse.status}`)
      }

      const contentType = streamResponse.headers.get('content-type') || ''
      if (!contentType.includes('text/event-stream')) {
        throw new Error('Not an SSE stream')
      }

      streamingAttempted = true

      const reader = streamResponse.body?.getReader()
      if (!reader) throw new Error('No reader available')

      const decoder = new TextDecoder()
      let buffer = ''
      let accumulatedContent = ''
      let newConvId = currentConvId

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        buffer += decoder.decode(value, { stream: true })

        // Parse SSE messages from buffer
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''

        let currentEvent = ''
        for (const line of lines) {
          if (line.startsWith('event: ')) {
            currentEvent = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            const dataStr = line.slice(6).trim()
            try {
              const data = JSON.parse(dataStr)

              if (currentEvent === 'chunk' && data.text) {
                accumulatedContent += data.text
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
                newConvId = data.conversation_id
                setConversationId(data.conversation_id)
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

      // Final safety update
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? { ...msg, content: accumulatedContent || msg.content }
            : msg,
        ),
      )
      if (newConvId && newConvId !== currentConvId) {
        setConversationId(newConvId)
      }
    } catch (err) {
      if (!streamingAttempted) {
        // Fall back to non-streaming API
        try {
          const res = await api.chat.send({
            message: text || `Uploaded ${attachmentCount} file(s)`,
            conversation_id: currentConvId,
            agent_id: currentAgent,
            attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
          })
          if (res.success && res.data) {
            setConversationId(res.data.conversation_id)
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      content: res.data!.output,
                      agentId: res.data!.agent_traces?.[0]?.agent_id,
                    }
                  : msg,
              ),
            )
          } else {
            setMessages((prev) =>
              prev.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: res.error || 'Request failed' }
                  : msg,
              ),
            )
          }
        } catch (fallbackErr) {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? { ...msg, content: 'Network error. Ensure the backend is running on port 8000.' }
                : msg,
            ),
          )
        }
      } else {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: 'Connection interrupted during streaming.' }
              : msg,
          ),
        )
      }
    } finally {
      setSending(false)
      fetchConversations()
    }
  }, [input, attachments, sending, uploadAttachment, conversationId, selectedAgent, fetchConversations])

  const addFiles = useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files)
    const newAttachments: Attachment[] = fileArray.map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
      previewUrl: isImage(file) ? URL.createObjectURL(file) : undefined,
    }))
    setAttachments((prev) => [...prev, ...newAttachments])
  }, [])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    addFiles(e.target.files || [])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  // Drag & Drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(true)
  }, [])

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    // Only hide if leaving the drop zone
    if (dropZoneRef.current && !dropZoneRef.current.contains(e.relatedTarget as Node)) {
      setIsDragging(false)
    }
  }, [])

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
  }, [])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setIsDragging(false)
    if (e.dataTransfer.files.length > 0) {
      addFiles(e.dataTransfer.files)
    }
  }, [addFiles])

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
    <div className="flex h-[calc(100vh-112px)] gap-6 animate-fade-in">
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

        <Card
          className="flex-1 flex flex-col relative"
          onDragEnter={handleDragEnter}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
          ref={dropZoneRef}
        >
          {/* Drag & Drop overlay */}
          {isDragging && (
            <div className="absolute inset-0 z-50 flex items-center justify-center rounded-lg border-2 border-dashed border-primary bg-background/80 backdrop-blur-sm">
              <div className="text-center">
                <Upload className="h-12 w-12 mx-auto mb-3 text-primary animate-bounce" />
                <p className="text-lg font-semibold">Drop files here</p>
                <p className="text-sm text-muted-foreground mt-1">
                  PDF, DOCX, TXT, MD, PNG, JPG, GIF, WEBP
                </p>
              </div>
            </div>
          )}

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
                            isImageExt(att.name) && att.documentId ? (
                              <div key={i} className="relative group">
                                <img
                                  src={api.documents.downloadUrl(att.documentId)}
                                  alt={att.name}
                                  className="max-w-[240px] max-h-[180px] rounded-lg border object-cover cursor-pointer hover:opacity-90 transition-opacity"
                                />
                                <Badge variant="secondary" className="absolute bottom-1 left-1 text-[10px] opacity-0 group-hover:opacity-80 transition-opacity gap-1">
                                  <ImageIcon className="h-3 w-3" />
                                  {att.name} ({formatBytes(att.size)})
                                </Badge>
                              </div>
                            ) : isImageExt(att.name) ? (
                              <Badge key={i} variant="secondary" className="gap-1 text-xs">
                                <ImageIcon className="h-3 w-3" />
                                {att.name} ({formatBytes(att.size)})
                              </Badge>
                            ) : (
                              <Badge key={i} variant="secondary" className="gap-1 text-xs">
                                <FileText className="h-3 w-3" />
                                {att.name} ({formatBytes(att.size)})
                              </Badge>
                            )
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
          <div className="flex items-center justify-between mb-3">
            <h3 className="font-semibold flex items-center gap-2">
              <MessageSquare className="h-4 w-4" />
              Conversations
            </h3>
            <Button
              variant="outline"
              size="sm"
              className="h-7 text-xs gap-1"
              onClick={startNewConversation}
            >
              <MessageSquare className="h-3 w-3" />
              New
            </Button>
          </div>

          {loadingConversations ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
            </div>
          ) : conversations.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p className="text-xs">No conversations yet</p>
              <p className="text-xs mt-1">Start chatting to see them here</p>
            </div>
          ) : (
            <ScrollArea className="h-[calc(100vh-320px)] -mx-1">
              <div className="space-y-1 px-1">
                {conversations.map((conv) => (
                  <div
                    key={conv.id}
                    className={`group flex items-center gap-2 rounded-md px-3 py-2 text-sm cursor-pointer transition-colors ${
                      conv.id === conversationId
                        ? 'bg-primary/10 text-primary'
                        : 'hover:bg-secondary'
                    }`}
                    onClick={() => loadConversation(conv.id)}
                  >
                    <MessageSquare className="h-3.5 w-3.5 shrink-0 opacity-60" />
                    <div className="flex-1 min-w-0">
                      <p className="truncate text-xs font-medium">{conv.title}</p>
                      {conv.lastMessage && (
                        <p className="truncate text-[11px] text-muted-foreground">
                          {conv.lastMessage}
                        </p>
                      )}
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-6 w-6 shrink-0 opacity-40 hover:opacity-100 hover:text-destructive transition-opacity"
                      onClick={(e) => {
                        e.stopPropagation()
                        if (window.confirm('Delete this conversation?')) {
                          api.chat.deleteConversation(conv.id).then(() => {
                            fetchConversations()
                            if (conversationId === conv.id) {
                              startNewConversation()
                            }
                          })
                        }
                      }}
                    >
                      <X className="h-3 w-3" />
                    </Button>
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </Card>

        <Card className="p-4">
          <h3 className="font-semibold mb-3 text-xs uppercase tracking-wider text-muted-foreground">
            Suggestions
          </h3>
          <div className="space-y-1">
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
                className="w-full justify-start text-xs h-auto py-1.5 font-normal"
                onClick={() => setInput(suggestion)}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="font-semibold mb-2 text-xs uppercase tracking-wider text-muted-foreground">
            Supported Formats
          </h3>
          <p className="text-[11px] text-muted-foreground leading-relaxed">
            PDF · DOCX · PPTX · TXT · MD · PNG · JPG · WEBP
          </p>
        </Card>
      </div>
    </div>
  )
}
