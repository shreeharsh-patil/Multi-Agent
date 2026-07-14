'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { useSession } from 'next-auth/react'
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
import { Send, Bot, User, MessageSquare, Paperclip, FileText, ImageIcon, X, Loader2, Upload, Mic, Volume2, Square, Sparkles, Users, CheckCircle2, FolderOpen, Share2 } from 'lucide-react'
import type { AgentId } from '@shared/types'
import { CodePreviewButton, type CodeSandboxProps } from '@/components/code-sandbox'
import { CodePreviewPanel } from '@/components/code-preview-panel'

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
  { id: 'calendar', name: 'Calendar Agent' },
]

const teamworkAgents = agents.filter((agent) => agent.id !== 'auto' && agent.id !== 'tool')

const isImage = (file: File) => file.type.startsWith('image/')

interface Attachment {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'done' | 'error'
  progress?: number
  documentId?: string
  imageUrl?: string
  previewUrl?: string
}

const isImageExt = (name: string) => /\.(png|jpg|jpeg|webp|gif|svg|bmp)$/i.test(name)

export default function ChatPage() {
  const { data: session } = useSession()
  const googleAccessToken = (session as any)?.accessToken as string | undefined
  const [messages, setMessages] = useState<Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    agentId?: string
    attachments?: Array<{ name: string; size: number; documentId?: string }>
  }>>([])
  const [input, setInput] = useState('')
  const [selectedAgent, setSelectedAgent] = useState<string>('auto')
  const [customAgents, setCustomAgents] = useState<Array<{ id: string; name: string }>>([])
  const [teamMode, setTeamMode] = useState(false)
  const [teamAgents, setTeamAgents] = useState<string[]>(['research', 'coding', 'planner'])
  const [workspaces, setWorkspaces] = useState<Array<{ id: string; name: string; color: string; documentCount: number }>>([])
  const [selectedWorkspace, setSelectedWorkspace] = useState('all')
  const [voiceMode, setVoiceMode] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [speakingId, setSpeakingId] = useState<string | null>(null)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [sending, setSending] = useState(false)
  const [isDragging, setIsDragging] = useState(false)
  const [codePreview, setCodePreview] = useState<CodeSandboxProps | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const dropZoneRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<any>(null)
  const lastSpokenRef = useRef<string | null>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const uploadAttachment = useCallback(async (att: Attachment): Promise<Attachment> => {
    setAttachments((prev) => prev.map((a) => a.id === att.id ? { ...a, status: 'uploading', progress: 0 } : a))
    try {
      const uploadWorkspace = selectedWorkspace !== 'all' && selectedWorkspace !== 'unfiled' ? selectedWorkspace : undefined
      const res = await api.documents.upload(att.file, 'default', (progress) => {
        setAttachments((prev) => prev.map((a) => a.id === att.id ? { ...a, progress } : a))
      }, uploadWorkspace)
      if (res.success && res.data) {
        return { ...att, status: 'done', documentId: res.data.id, imageUrl: res.data.imageUrl, progress: 100 }
      }
      return { ...att, status: 'error', progress: 0 }
    } catch {
      return { ...att, status: 'error', progress: 0 }
    }
  }, [selectedWorkspace])

  const speakMessage = useCallback((id: string, content: string) => {
    if (typeof window === 'undefined' || !('speechSynthesis' in window)) return
    window.speechSynthesis.cancel()
    if (speakingId === id) {
      setSpeakingId(null)
      return
    }
    const utterance = new SpeechSynthesisUtterance(content)
    utterance.rate = 1.02
    utterance.onend = () => setSpeakingId(null)
    window.speechSynthesis.speak(utterance)
    setSpeakingId(id)
  }, [speakingId])

  const toggleVoiceInput = useCallback(() => {
    if (isListening) {
      recognitionRef.current?.stop()
      setIsListening(false)
      return
    }
    if (typeof window === 'undefined') return
    const browserWindow = window as any
    const SpeechRecognition = browserWindow.SpeechRecognition || browserWindow.webkitSpeechRecognition
    if (!SpeechRecognition) return
    const recognition = new SpeechRecognition()
    recognition.onresult = (event: any) => {
      const transcript = event.results[0]?.[0]?.transcript
      if (transcript) setInput((current) => `${current}${current ? ' ' : ''}${transcript}`)
    }
    recognition.onend = () => setIsListening(false)
    recognitionRef.current = recognition
    recognition.start()
    setIsListening(true)
  }, [isListening])

  const toggleVoiceMode = useCallback(() => {
    setVoiceMode((current) => {
      if (current) {
        recognitionRef.current?.stop()
        window.speechSynthesis?.cancel()
        setIsListening(false)
        setSpeakingId(null)
      }
      return !current
    })
  }, [])

  useEffect(() => {
    if (!voiceMode || sending) return
    const latest = [...messages].reverse().find((message) => message.role === 'assistant' && message.content)
    if (!latest || lastSpokenRef.current === latest.id) return
    lastSpokenRef.current = latest.id
    speakMessage(latest.id, latest.content)
  }, [messages, sending, voiceMode, speakMessage])

  useEffect(() => () => {
    recognitionRef.current?.stop()
    window.speechSynthesis?.cancel()
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

  const shareConversation = useCallback(async () => {
    if (!conversationId) return
    const res = await api.chat.createShare(conversationId)
    if (res.success && res.data) {
      const url = `${window.location.origin}/shared/chat/${res.data.token}`
      setShareUrl(url)
      await navigator.clipboard?.writeText(url)
    }
  }, [conversationId])

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
    api.workspaces.list().then((res) => {
      if (res.success && res.data) setWorkspaces(res.data)
    })
    api.agents.list().then((res) => {
      if (res.success && res.data) setCustomAgents(res.data.filter((agent) => agent.custom).map((agent) => ({ id: agent.id, name: agent.name })))
    })
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
    if ((!input.trim() && attachments.length === 0) || sending || (teamMode && teamAgents.length === 0)) return

    const text = input.trim()
    const attachmentCount = attachments.length
    const currentConvId = conversationId
    const currentAgent = teamMode || selectedAgent === 'auto' ? undefined : selectedAgent
    const currentWorkspace = selectedWorkspace === 'all' ? undefined : selectedWorkspace === 'unfiled' ? '__unfiled__' : selectedWorkspace

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
        team_agents: teamMode ? teamAgents as AgentId[] : undefined,
        workspace_id: currentWorkspace,
        attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
      }, googleAccessToken)

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
            team_agents: teamMode ? teamAgents as AgentId[] : undefined,
            workspace_id: currentWorkspace,
            attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
          }, googleAccessToken)
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
  }, [input, attachments, sending, uploadAttachment, conversationId, selectedAgent, teamMode, teamAgents, selectedWorkspace, googleAccessToken, fetchConversations])

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
  const attachmentsRef = useRef(attachments)
  attachmentsRef.current = attachments
  useEffect(() => {
    return () => {
      attachmentsRef.current.forEach((a) => { if (a.previewUrl) URL.revokeObjectURL(a.previewUrl) })
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
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" className="gap-2" onClick={shareConversation} disabled={!conversationId}>
              <Share2 className="h-4 w-4" /> <span className="hidden sm:inline">Share</span>
            </Button>
            <Button
              variant={voiceMode ? 'default' : 'outline'}
              size="sm"
              className={`gap-2 ${voiceMode ? 'bg-violet-600 text-white shadow-[0_0_24px_rgba(124,58,237,.28)] hover:bg-violet-600/90' : ''}`}
              onClick={toggleVoiceMode}
              aria-pressed={voiceMode}
            >
              <Volume2 className="h-4 w-4" />
              <span className="hidden sm:inline">Voice mode</span>
            </Button>
            <Button
              variant={teamMode ? 'default' : 'outline'}
              size="sm"
              className={`gap-2 ${teamMode ? 'shadow-[0_0_24px_hsl(var(--primary)/.22)]' : ''}`}
              onClick={() => setTeamMode((current) => !current)}
              aria-pressed={teamMode}
            >
              <Users className="h-4 w-4" />
              Teamwork
              <span className="rounded-full bg-emerald-500/15 px-1.5 py-0.5 text-[10px] font-semibold text-emerald-600 dark:text-emerald-400">BETA</span>
            </Button>
            {!teamMode && <Select value={selectedAgent} onValueChange={setSelectedAgent}>
              <SelectTrigger className="w-[200px]"><SelectValue placeholder="Select agent" /></SelectTrigger>
              <SelectContent>
                {agents.concat(customAgents).map((agent) => <SelectItem key={agent.id} value={agent.id}>{agent.name}</SelectItem>)}
              </SelectContent>
            </Select>}
          </div>
        </div>
        {shareUrl && <div className="mb-4 flex items-center gap-2 rounded-lg border border-emerald-500/25 bg-emerald-500/[.06] px-3 py-2 text-xs"><Share2 className="h-3.5 w-3.5 text-emerald-600" /><span className="font-medium">Share link copied</span><Input readOnly value={shareUrl} className="ml-auto h-7 max-w-md text-[11px]" /></div>}

        {voiceMode && (
          <Card className="mb-4 border-violet-500/25 bg-gradient-to-r from-violet-500/[.08] via-background to-fuchsia-500/[.05]">
            <div className="flex items-center gap-3 px-4 py-3">
              <div className="relative flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-violet-500/15 text-violet-600 dark:text-violet-300">
                <Volume2 className="h-4 w-4" />
                <span className="absolute inset-0 rounded-full border border-violet-500/30 animate-ping [animation-duration:2.5s]" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold">Voice mode is on</p>
                <p className="truncate text-xs text-muted-foreground">Tap the microphone to speak. Agent responses will be read aloud automatically.</p>
              </div>
              <Badge variant="outline" className="hidden shrink-0 border-violet-500/30 text-violet-600 dark:text-violet-300 sm:flex">Browser audio</Badge>
            </div>
          </Card>
        )}

        <div className="mb-4 flex items-center gap-2 rounded-lg border bg-card px-3 py-2 text-xs">
          <FolderOpen className="h-3.5 w-3.5 text-primary" />
          <span className="font-medium">Knowledge scope</span>
          <select value={selectedWorkspace} onChange={(e) => setSelectedWorkspace(e.target.value)} className="ml-auto h-8 rounded-md border bg-background px-2 text-xs">
            <option value="all">All documents</option>
            <option value="unfiled">Unfiled documents</option>
            {workspaces.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}
          </select>
        </div>

        {teamMode && (
          <Card className="mb-4 overflow-hidden border-primary/20 bg-gradient-to-r from-primary/[.06] via-background to-emerald-500/[.05]">
            <div className="flex items-start gap-3 p-4">
              <div className="mt-0.5 rounded-lg bg-primary/10 p-2 text-primary"><Sparkles className="h-4 w-4" /></div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center justify-between gap-3">
                  <div><p className="text-sm font-semibold">Build a specialist team</p><p className="text-xs text-muted-foreground">Agents will collaborate on your request in sequence.</p></div>
                  <Badge variant="outline" className="hidden shrink-0 gap-1 sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-emerald-500" /> Ready</Badge>
                </div>
                <div className="mt-3 flex flex-wrap gap-2">
                  {teamworkAgents.map((agent) => {
                    const active = teamAgents.includes(agent.id)
                    return <button key={agent.id} type="button" onClick={() => setTeamAgents((current) => active ? current.filter((id) => id !== agent.id) : [...current, agent.id])} className={`flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs transition-colors ${active ? 'border-primary/40 bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:bg-secondary'}`} aria-pressed={active}>
                      {active ? <CheckCircle2 className="h-3 w-3" /> : <span className="h-3 w-3 rounded-full border" />}{agent.name.replace(' Agent', '')}
                    </button>
                  })}
                </div>
              </div>
            </div>
          </Card>
        )}

        <div
          className="flex-1 flex flex-col relative bg-background"
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
              <div className="space-y-6 max-w-4xl mx-auto w-full">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                    {msg.role === 'assistant' && (
                      <Avatar className="h-8 w-8 shrink-0">
                        <AvatarFallback className="bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-zinc-200 dark:border-zinc-800">
                          <Bot className="h-4 w-4" />
                        </AvatarFallback>
                      </Avatar>
                    )}
                    <div className={`max-w-[75%] ${msg.role === 'user' ? 'order-1' : ''}`}>
                      {msg.agentId && msg.role === 'assistant' && (
                        <Badge variant="outline" className="mb-1.5 text-[10px] uppercase tracking-wider font-mono bg-secondary/30">
                          {agents.concat(customAgents).find((a) => a.id === msg.agentId)?.name}
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
                      <div className="group relative">
                        <div
                          className={`rounded-2xl px-4 py-3 text-sm ${
                            msg.role === 'user'
                              ? 'bg-zinc-100 dark:bg-zinc-800 text-zinc-900 dark:text-zinc-100 border border-zinc-200/50 dark:border-zinc-700/30 shadow-sm'
                              : 'text-foreground leading-relaxed'
                          }`}
                        >
                          <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
                        </div>
                        {msg.role === 'assistant' && msg.content && (
                          <div className="absolute -bottom-7 left-0 flex items-center gap-1 opacity-0 transition-opacity group-hover:opacity-100">
                            <button type="button" onClick={() => speakMessage(msg.id, msg.content)} className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground" aria-label={speakingId === msg.id ? 'Stop speaking' : 'Read response aloud'}>
                              {speakingId === msg.id ? <><Square className="h-3 w-3 fill-current" /> Stop</> : <><Volume2 className="h-3 w-3" /> Listen</>}
                            </button>
                            <CodePreviewButton content={msg.content} onPreview={setCodePreview} />
                          </div>
                        )}
                      </div>
                    </div>
                    {msg.role === 'user' && (
                      <Avatar className="h-8 w-8 shrink-0">
                        <AvatarFallback className="bg-zinc-100 dark:bg-zinc-800 border">
                          <User className="h-4 w-4" />
                        </AvatarFallback>
                      </Avatar>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}

          <div className="px-4 py-4 max-w-4xl mx-auto w-full space-y-2">
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
                    {att.status === 'uploading' && (
                      <span className="text-[10px] text-muted-foreground flex items-center gap-1 shrink-0">
                        <Loader2 className="h-3 w-3 animate-spin text-primary" />
                        {att.progress !== undefined ? `${att.progress}%` : '0%'}
                      </span>
                    )}
                    {att.status === 'pending' && (
                      <button onClick={() => removeAttachment(att.id)} className="shrink-0">
                        <X className="h-3 w-3 hover:text-destructive" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}
            <div className="relative flex items-center bg-secondary/40 dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-850 rounded-2xl p-1.5 focus-within:ring-1 focus-within:ring-zinc-400 dark:focus-within:ring-zinc-700 transition-all duration-150 shadow-sm w-full gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".pdf,.docx,.pptx,.txt,.md,.png,.jpg,.jpeg,.webp,.gif"
                multiple
                className="hidden"
                onChange={handleFileSelect}
              />
              <Button
                variant="ghost"
                size="icon"
                onClick={() => fileInputRef.current?.click()}
                disabled={sending}
                className="rounded-xl h-8 w-8 hover:bg-zinc-200/50 dark:hover:bg-zinc-800/50 text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 shrink-0"
              >
                <Paperclip className="h-4 w-4" />
              </Button>
              <Input
                placeholder={teamMode ? 'Give your team a multi-step mission...' : 'Ask about your documents or images...'}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                className="flex-1 bg-transparent border-0 focus-visible:ring-0 focus-visible:ring-offset-0 px-2 py-1.5 text-sm placeholder:text-zinc-500 h-9"
                disabled={sending}
              />
              <Button 
                variant={isListening ? 'default' : 'ghost'} 
                size="icon" 
                onClick={toggleVoiceInput} 
                disabled={sending} 
                aria-label={isListening ? 'Stop listening' : 'Start voice input'} 
                className={`rounded-xl h-8 w-8 text-zinc-500 hover:text-zinc-800 dark:hover:text-zinc-200 shrink-0 ${isListening ? 'animate-pulse' : 'hover:bg-zinc-200/50 dark:hover:bg-zinc-800/50'}`}
              >
                {isListening ? <Square className="h-3.5 w-3.5 fill-current text-destructive" /> : <Mic className="h-4 w-4" />}
              </Button>
              <Button 
                onClick={handleSend} 
                disabled={sending || (!input.trim() && attachments.length === 0) || (teamMode && teamAgents.length === 0)} 
                className="rounded-xl h-8 px-3 text-xs gap-1.5 bg-zinc-900 hover:bg-zinc-850 dark:bg-zinc-100 dark:hover:bg-zinc-200 dark:text-zinc-900 text-zinc-100 shrink-0"
              >
                {sending ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Send className="h-3.5 w-3.5" />}
                Send
              </Button>
            </div>
          </div>
        </div>
      </div>

      {codePreview && (
        <div className="fixed inset-0 z-30 bg-black/30" onClick={() => setCodePreview(null)} />
      )}
      <CodePreviewPanel preview={codePreview} onClose={() => setCodePreview(null)} />
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
