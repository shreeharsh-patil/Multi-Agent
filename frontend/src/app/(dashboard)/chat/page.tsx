'use client'

import { useState, useRef, useEffect, useCallback, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
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
import type { AgentId, DocumentInfo } from '@shared/types'
import { CodePreviewButton, CodeSandbox, type CodeSandboxProps, extractCodeFromContent } from '@/components/code-sandbox'
import { CodePreviewPanel } from '@/components/code-preview-panel'
import { FileCode, FileImage, Globe, Play, Code as CodeIcon } from 'lucide-react'

function LogoSpike({ className = "h-4.5 w-4.5" }: { className?: string }) {
  return (
    <svg className={`text-[#cc785c] fill-current shrink-0 ${className}`} viewBox="0 0 24 24">
      <path d="M12 2c.4 3.5 1.5 6.5 4 9 2.5 2.5 5.5 3.6 9 4-3.5.4-6.5 1.5-9 4-2.5 2.5-3.6 5.5-4 9-.4-3.5-1.5-6.5-4-9-2.5-2.5-5.5-3.6-9-4 3.5-.4 6.5-1.5 9-4 2.5-2.5 3.6-5.5 4-9z" />
    </svg>
  )
}


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

interface PanelTab {
  id: string
  title: string
  type: 'document' | 'code'
  fileType?: string
  content?: string
  sandboxProps?: CodeSandboxProps
  docId?: string
}

function ChatContent() {
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

  // Hybrid layout UI states
  const [documents, setDocuments] = useState<DocumentInfo[]>([])
  const [loadingDocuments, setLoadingDocuments] = useState(false)
  const [tabs, setTabs] = useState<PanelTab[]>([])
  const [activeTabId, setActiveTabId] = useState<string | null>(null)
  const [showCodeSource, setShowCodeSource] = useState(false)

  const searchParams = useSearchParams()
  useEffect(() => {
    const agentParam = searchParams?.get('agent')
    if (agentParam && agents.concat(customAgents).some(a => a.id === agentParam)) {
      setSelectedAgent(agentParam)
    }
  }, [searchParams, customAgents])
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
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const dropZoneRef = useRef<HTMLDivElement>(null)
  const recognitionRef = useRef<any>(null)
  const lastSpokenRef = useRef<string | null>(null)
  // Tracks the in-flight upload promise for each attachment so Send can await
  // an upload already started on select instead of uploading a second time.
  const uploadPromises = useRef<Map<string, Promise<Attachment>>>(new Map())

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const uploadAttachment = useCallback(async (att: Attachment): Promise<Attachment> => {
    setAttachments((prev) => prev.map((a) => a.id === att.id ? { ...a, status: 'uploading', progress: 0 } : a))
    let final: Attachment
    try {
      const uploadWorkspace = selectedWorkspace !== 'all' && selectedWorkspace !== 'unfiled' ? selectedWorkspace : undefined
      const res = await api.documents.upload(att.file, 'default', (progress) => {
        setAttachments((prev) => prev.map((a) => a.id === att.id ? { ...a, progress } : a))
      }, uploadWorkspace)
      final = res.success && res.data
        ? { ...att, status: 'done', documentId: res.data.id, imageUrl: res.data.imageUrl, progress: 100 }
        : { ...att, status: 'error', progress: 0 }
    } catch {
      final = { ...att, status: 'error', progress: 0 }
    }
    setAttachments((prev) => prev.map((a) => a.id === att.id ? final : a))
    uploadPromises.current.delete(att.id)
    return final
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

  // Fetch documents for explorer
  const fetchDocuments = useCallback(async () => {
    setLoadingDocuments(true)
    try {
      const res = await api.documents.list(selectedWorkspace === 'all' ? undefined : selectedWorkspace)
      if (res.success && res.data) {
        setDocuments(res.data)
      }
    } catch (e) {
      // Silently fail
    } finally {
      setLoadingDocuments(false)
    }
  }, [selectedWorkspace])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  // Document Click handler to load text/media in right panel tab
  const handleDocumentClick = useCallback(async (doc: DocumentInfo) => {
    const existingTab = tabs.find(t => t.id === doc.id)
    if (existingTab) {
      setActiveTabId(doc.id)
      return
    }

    const newTab: PanelTab = {
      id: doc.id,
      title: doc.fileName,
      type: 'document',
      fileType: doc.fileType,
      docId: doc.id
    }

    setTabs(prev => [...prev, newTab])
    setActiveTabId(doc.id)

    const fileTypeLower = doc.fileType.toLowerCase()
    if (['txt', 'md'].includes(fileTypeLower)) {
      try {
        const downloadUrl = api.documents.downloadUrl(doc.id)
        const res = await fetch(downloadUrl)
        const text = await res.text()
        setTabs(prev => prev.map(t => t.id === doc.id ? { ...t, content: text } : t))
      } catch (e) {
        setTabs(prev => prev.map(t => t.id === doc.id ? { ...t, content: 'Failed to load file content.' } : t))
      }
    }
  }, [tabs])

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

    // Attachments already began uploading on select. Await any in-flight
    // upload; only kick off a fresh upload for ones that never started
    // (e.g. added programmatically) or previously errored.
    const uploadedAttachments: Array<{ name: string; size: number; documentId?: string }> = []
    for (const att of attachments) {
      let updated: Attachment
      const inFlight = uploadPromises.current.get(att.id)
      if (inFlight) {
        updated = await inFlight
      } else if (att.status === 'done') {
        updated = att
      } else {
        updated = await uploadAttachment(att)
      }
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
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }

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
      fetchDocuments()
    }
  }, [input, attachments, sending, uploadAttachment, conversationId, selectedAgent, teamMode, teamAgents, selectedWorkspace, googleAccessToken, fetchConversations, fetchDocuments])

  const addFiles = useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files)
    const newAttachments: Attachment[] = fileArray.map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: 'pending',
      previewUrl: isImage(file) ? URL.createObjectURL(file) : undefined,
    }))
    setAttachments((prev) => [...prev, ...newAttachments])
    // Begin uploading immediately on select so files are ready before Send.
    newAttachments.forEach((att) => { uploadPromises.current.set(att.id, uploadAttachment(att)) })
  }, [uploadAttachment])

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

  const handleSuggestionClick = (suggestion: string) => {
    setInput(suggestion)
    if (textareaRef.current) {
      textareaRef.current.value = suggestion
      textareaRef.current.style.height = 'auto'
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`
      textareaRef.current.focus()
    }
  }

  const handleCloseTab = (tabId: string) => {
    setTabs(prev => {
      const filtered = prev.filter(t => t.id !== tabId)
      if (activeTabId === tabId) {
        setActiveTabId(filtered.length > 0 ? filtered[filtered.length - 1]!.id : null)
      }
      return filtered
    })
  }

  const renderCodeContent = (content: string) => {
    const lines = content.split('\n')
    return (
      <div className="flex-1 overflow-auto bg-[#18181b] text-zinc-350 font-mono text-xs sm:text-sm p-4 select-text scrollbar-thin">
        <div className="flex min-w-full">
          <div className="text-zinc-650 select-none text-right pr-4 border-r border-[#27272a] mr-4 min-w-[2.5rem]">
            {lines.map((_, i) => (
              <div key={i} className="h-5">{i + 1}</div>
            ))}
          </div>
          <div className="flex-1 whitespace-pre">
            {lines.map((line, i) => (
              <div key={i} className="h-5">{line || ' '}</div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  const activeTab = tabs.find(t => t.id === activeTabId)

  return (
    <div className="flex h-[calc(100vh-84px)] gap-0 -m-6 overflow-hidden bg-[#212121] animate-fade-in relative">
      {/* 1. LEFT PANEL: Explorer & Past Conversations */}
      <aside className="hidden md:flex w-[260px] flex-col bg-[#171717] border-r border-[#2F2F2F] h-full shrink-0 select-none">
        {/* Upper Section: Documents Explorer */}
        <div className="flex-1 flex flex-col min-h-0 border-b border-[#2F2F2F]">
          <div className="p-4 border-b border-[#2F2F2F] flex items-center justify-between bg-[#171717]">
            <span className="text-[11px] font-semibold text-[#B4B4B4] uppercase tracking-wider">Documents Explorer</span>
            <FolderOpen className="h-4 w-4 text-[#B4B4B4]" />
          </div>
          <ScrollArea className="flex-1 p-2">
            {loadingDocuments ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
              </div>
            ) : documents.length === 0 ? (
              <div className="text-center py-6 text-[11px] text-[#B4B4B4] font-sans px-2">
                No documents found. Drag & drop files in chat or use paperclip.
              </div>
            ) : (
              <div className="space-y-0.5">
                {documents.map((doc) => {
                  const fileType = doc.fileType.toLowerCase()
                  const isImg = ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'].includes(fileType)
                  const Icon = isImg ? ImageIcon : FileText
                  const isTabActive = activeTabId === doc.id
                  return (
                    <button
                      key={doc.id}
                      onClick={() => handleDocumentClick(doc)}
                      className={`w-full flex items-center gap-2.5 rounded-[8px] px-3 py-2 text-left text-xs transition-all hover:bg-[#2F2F2F] ${
                        isTabActive ? 'bg-[#2F2F2F] text-white font-medium border border-[#2F2F2F]' : 'text-[#B4B4B4] hover:text-[#F9F9F9]'
                      }`}
                    >
                      <Icon className={`h-4 w-4 shrink-0 ${isTabActive ? 'text-white' : 'text-[#B4B4B4]'}`} />
                      <span className="truncate flex-1 font-sans text-xs">{doc.fileName}</span>
                    </button>
                  )
                })}
              </div>
            )}
          </ScrollArea>
        </div>

        {/* Lower Section: Past Conversations list */}
        <div className="flex-1 flex flex-col min-h-0 bg-[#171717]">
          <div className="p-4 border-b border-[#2F2F2F] flex items-center justify-between bg-[#171717]">
            <span className="text-[11px] font-semibold text-[#B4B4B4] uppercase tracking-wider">Conversations</span>
            <button
              onClick={startNewConversation}
              className="text-xs font-medium text-white hover:text-[#F9F9F9] flex items-center gap-1 transition-colors"
            >
              <Sparkles className="h-3.5 w-3.5" />
              New
            </button>
          </div>
          <ScrollArea className="flex-1 p-2">
            {loadingConversations ? (
              <div className="flex items-center justify-center py-4">
                <Loader2 className="h-4 w-4 animate-spin text-zinc-500" />
              </div>
            ) : conversations.length === 0 ? (
              <div className="text-center py-6 text-[11px] text-[#B4B4B4] font-sans">
                No past conversations.
              </div>
            ) : (
              <div className="space-y-0.5">
                {conversations.map((conv) => {
                  const isCurrent = conv.id === conversationId
                  return (
                    <div
                      key={conv.id}
                      className={`group flex items-center gap-2 rounded px-2.5 py-1.5 text-xs cursor-pointer transition-all hover:bg-zinc-900/60 ${
                        isCurrent ? 'bg-[#18181b] text-violet-400 font-medium shadow-sm' : 'text-zinc-400 hover:text-zinc-200'
                      }`}
                      onClick={() => loadConversation(conv.id)}
                    >
                      <MessageSquare className={`h-3.5 w-3.5 shrink-0 ${isCurrent ? 'text-violet-400' : 'text-zinc-500'}`} />
                      <span className="truncate flex-1 font-sans text-[11px]">{conv.title}</span>
                      <button
                        type="button"
                        className="opacity-0 group-hover:opacity-100 text-zinc-500 hover:text-red-400 transition-opacity"
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
                      </button>
                    </div>
                  )
                })}
              </div>
            )}
          </ScrollArea>
        </div>
      </aside>

      {/* 2. CENTRAL PANEL: ChatGPT Conversation Feed */}
      <div
        className="flex-1 flex flex-col h-full bg-[#121214] relative min-w-0"
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        ref={dropZoneRef}
      >
        {/* Drag & Drop overlay */}
        {isDragging && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
            <div className="text-center p-6 border-2 border-dashed border-violet-500/50 rounded-2xl max-w-sm mx-4 bg-zinc-900 shadow-2xl">
              <Upload className="h-10 w-10 mx-auto mb-3 text-violet-400 animate-bounce" />
              <p className="text-sm font-semibold text-zinc-200">Drop files here to upload</p>
              <p className="text-[11px] text-zinc-500 mt-1">
                We support PDF, DOCX, PPTX, TXT, MD, PNG, JPG, WEBP
              </p>
            </div>
          </div>
        )}

        {/* Top Header / Toolbar */}
        <div className="flex items-center justify-between border-b border-[#27272a] px-6 py-3 min-h-[56px] shrink-0 bg-[#0c0c0e]/90 backdrop-blur-md select-none z-10">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold truncate text-zinc-100 flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-violet-400 shrink-0" />
              <span>{chatTitle || 'New Conversation'}</span>
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-zinc-900 rounded-lg" onClick={shareConversation} disabled={!conversationId} title="Share Link">
              <Share2 className="h-3.5 w-3.5 text-zinc-400" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 gap-1.5 hover:bg-zinc-900 rounded-lg px-2.5 ${
                voiceMode ? 'bg-violet-950/40 text-violet-400 border border-violet-800/40 shadow-[0_0_12px_rgba(124,58,237,.1)]' : 'text-zinc-400'
              }`}
              onClick={toggleVoiceMode}
            >
              <Volume2 className="h-3.5 w-3.5" />
              <span className="text-xs hidden sm:inline">Voice Mode</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 gap-1.5 hover:bg-zinc-900 rounded-lg px-2.5 ${
                teamMode ? 'bg-emerald-950/40 text-emerald-400 border border-emerald-800/40' : 'text-zinc-400'
              }`}
              onClick={() => setTeamMode((current) => !current)}
            >
              <Users className="h-3.5 w-3.5" />
              <span className="text-xs hidden sm:inline">Teamwork</span>
              <span className="rounded bg-emerald-500/10 px-1 py-0.5 text-[9px] font-bold text-emerald-400">BETA</span>
            </Button>

            {!teamMode && (
              <select
                value={selectedAgent}
                onChange={(e) => setSelectedAgent(e.target.value)}
                className="h-8 rounded-lg bg-[#1e1e24] border border-[#27272a] px-2 text-xs text-zinc-300 focus:outline-none focus:ring-1 focus:ring-zinc-700 w-[160px] font-sans"
              >
                {agents.concat(customAgents).map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name}
                  </option>
                ))}
              </select>
            )}
          </div>
        </div>

        {shareUrl && (
          <div className="mx-6 mt-4 flex items-center gap-2 rounded-lg border border-emerald-500/25 bg-emerald-500/[.04] px-3 py-2 text-xs">
            <Share2 className="h-3.5 w-3.5 text-emerald-500" />
            <span className="font-medium text-emerald-400">Conversation link copied:</span>
            <Input readOnly value={shareUrl} className="ml-auto h-7 max-w-sm text-[10px] bg-[#1e1e24] border-[#27272a] text-zinc-300" />
          </div>
        )}

        {/* Voice Mode Banner */}
        {voiceMode && (
          <div className="mx-6 mt-4 border border-violet-500/20 bg-gradient-to-r from-violet-950/20 via-background to-fuchsia-950/10 rounded-xl p-3 shrink-0">
            <div className="flex items-center gap-3">
              <div className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-violet-950 text-violet-400 border border-violet-800/40">
                <Volume2 className="h-3.5 w-3.5" />
                <span className="absolute inset-0 rounded-full border border-violet-500/30 animate-ping [animation-duration:2.5s]" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-zinc-200">Voice mode active</p>
                <p className="text-[10px] text-zinc-500 truncate">Speak by pressing the mic button. Agent answers will be spoken back.</p>
              </div>
            </div>
          </div>
        )}

        {/* Workspace Scope Banner */}
        <div className="flex items-center gap-2 border-b border-[#27272a] bg-[#0c0c0e]/30 px-6 py-2 text-[10px] text-zinc-400 shrink-0 select-none">
          <FolderOpen className="h-3 w-3 text-violet-400" />
          <span>Scope:</span>
          <select
            value={selectedWorkspace}
            onChange={(e) => setSelectedWorkspace(e.target.value)}
            className="h-5 rounded bg-[#1e1e24] border border-[#27272a] px-1 text-[10px] text-zinc-300 focus:outline-none"
          >
            <option value="all">All documents</option>
            <option value="unfiled">Unfiled documents</option>
            {workspaces.map((workspace) => (
              <option key={workspace.id} value={workspace.id}>
                {workspace.name}
              </option>
            ))}
          </select>
        </div>

        {/* Team Collaboration Banner */}
        {teamMode && (
          <div className="border-b border-[#27272a] bg-[#1a1a24]/30 p-3 shrink-0">
            <div className="max-w-3xl mx-auto flex items-start gap-2 text-xs">
              <Sparkles className="h-3.5 w-3.5 text-violet-400 mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-zinc-300 text-[11px] uppercase tracking-wider">Agent Specialist Squad</p>
                <p className="text-[10px] text-zinc-500">Pick which agents participate collaboratively in order.</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {teamworkAgents.map((agent) => {
                    const active = teamAgents.includes(agent.id)
                    return (
                      <button
                        key={agent.id}
                        type="button"
                        onClick={() => setTeamAgents((current) => active ? current.filter((id) => id !== agent.id) : [...current, agent.id])}
                        className={`flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] transition-all ${
                          active ? 'border-violet-800 bg-violet-950/40 text-violet-300' : 'border-[#27272a] text-zinc-500 hover:bg-zinc-800'
                        }`}
                      >
                        {active ? <CheckCircle2 className="h-3 w-3 text-violet-400" /> : <span className="h-2 w-2 rounded-full border border-zinc-650" />}
                        {agent.name.replace(' Agent', '')}
                      </button>
                    )
                  })}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Message Feeds Scroll Area */}
        <div className="flex-1 overflow-y-auto scrollbar-thin relative min-h-0">
          {messages.length === 0 ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center select-none bg-[#faf9f5]">
              <div className="max-w-2xl w-full flex flex-col items-center justify-center space-y-12">
                <div className="space-y-4">
                  <div className="flex justify-center">
                    <div className="h-14 w-14 rounded-[8px] border border-[#e6dfd8] bg-[#efe9de] flex items-center justify-center transition-transform hover:scale-105 duration-300 shadow-sm">
                      <LogoSpike className="h-6 w-6" />
                    </div>
                  </div>
                  <h1 className="text-4xl font-serif font-normal tracking-tight text-[#141413]">
                    How can I help you today?
                  </h1>
                  <p className="text-sm text-[#6c6a64] max-w-md mx-auto leading-relaxed font-sans">
                    Ask anything, analyze documents, or delegate tasks to specialized AI agents in this collaborative workspace.
                  </p>
                </div>

                {/* Central quick suggestion buttons as premium cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4 w-full px-4">
                  {[
                    { text: 'Research a topic', desc: 'Perform deep search across the web', icon: Globe },
                    { text: 'Analyze a file', desc: 'Upload documents or spreadsheets', icon: FileText },
                    { text: 'Generate code', desc: 'Write, debug or refactor code', icon: CodeIcon },
                    { text: 'Create an image', desc: 'Generate high-fidelity visual assets', icon: ImageIcon },
                    { text: 'Write something', desc: 'Draft articles, copy, or summaries', icon: FileCode },
                  ].map((card) => (
                    <button
                      key={card.text}
                      onClick={() => handleSuggestionClick(card.text)}
                      className="group flex flex-col items-start p-5 rounded-[12px] border border-[#e6dfd8] bg-[#efe9de] text-left transition-all duration-200 hover:bg-[#e8e0d2]/75 active:scale-[0.99] shadow-xs"
                    >
                      <card.icon className="h-5 w-5 text-[#6c6a64] group-hover:text-[#cc785c] transition-colors stroke-[1.5] mb-3" />
                      <span className="text-[15px] font-semibold text-[#141413] mb-1 font-sans">{card.text}</span>
                      <span className="text-xs text-[#6c6a64] leading-normal font-sans">{card.desc}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <ScrollArea ref={scrollRef} className="h-full px-6 py-6">
              <div className="space-y-6 max-w-3xl mx-auto">
                {messages.map((msg) => (
                  <div key={msg.id} className={`flex gap-3.5 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                    {msg.role === 'assistant' && (
                      <Avatar className="h-7 w-7 border border-[#e6dfd8] shrink-0 mt-0.5 shadow-sm">
                        <AvatarFallback className="bg-[#efe9de] text-[#6c6a64] text-xs">
                          <Bot className="h-3.5 w-3.5 text-[#cc785c]" />
                        </AvatarFallback>
                      </Avatar>
                    )}
                    <div className={`max-w-[80%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                      {msg.agentId && msg.role === 'assistant' && (
                        <Badge variant="outline" className="mb-1 text-[9px] uppercase tracking-wider font-mono bg-[#faf9f5] border-[#e6dfd8] text-[#6c6a64]">
                          {agents.concat(customAgents).find((a) => a.id === msg.agentId)?.name || msg.agentId}
                        </Badge>
                      )}
                      
                      {/* Message attachments */}
                      {msg.attachments && msg.attachments.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mb-2">
                          {msg.attachments.map((att, i) => {
                            const isImg = isImageExt(att.name)
                            return isImg && att.documentId ? (
                              <div key={i} className="relative group rounded-lg overflow-hidden border border-[#e6dfd8] bg-[#faf9f5] shadow-sm">
                                <img
                                  src={api.documents.downloadUrl(att.documentId)}
                                  alt={att.name}
                                  className="max-w-[200px] max-h-[140px] object-cover cursor-pointer hover:opacity-90 transition-opacity"
                                  onClick={() => handleDocumentClick({ id: att.documentId!, fileName: att.name, fileType: 'png' } as any)}
                                />
                              </div>
                            ) : (
                              <button
                                key={i}
                                onClick={() => att.documentId && handleDocumentClick({ id: att.documentId, fileName: att.name, fileType: att.name.split('.').pop() || 'txt' } as any)}
                                className="flex items-center gap-1.5 rounded-lg border border-[#e6dfd8] bg-[#faf9f5] hover:bg-[#f5f0e8] px-2.5 py-1 text-xs text-[#6c6a64] hover:text-[#141413] transition-colors shadow-xs"
                              >
                                {isImg ? <ImageIcon className="h-3 w-3 text-[#5db872]" /> : <FileText className="h-3 w-3 text-[#cc785c]" />}
                                <span className="max-w-[120px] truncate">{att.name}</span>
                              </button>
                            )
                          })}
                        </div>
                      )}

                      <div className="group relative">
                        <div
                          className={`rounded-[12px] px-4 py-2.5 text-sm leading-relaxed ${
                            msg.role === 'user'
                              ? 'bg-[#efe9de] text-[#141413] border border-[#e6dfd8] shadow-xs font-sans'
                              : 'text-[#141413] bg-transparent font-sans'
                          }`}
                        >
                          <pre className="whitespace-pre-wrap font-sans text-xs sm:text-sm">{msg.content}</pre>
                        </div>
                        {msg.role === 'assistant' && msg.content && (
                          <div className="flex items-center gap-3 mt-1.5 px-1 opacity-0 group-hover:opacity-100 transition-opacity select-none">
                            <button
                              type="button"
                              onClick={() => speakMessage(msg.id, msg.content)}
                              className="flex items-center gap-1 text-[10px] text-[#6c6a64] hover:text-[#141413] transition-colors"
                            >
                              {speakingId === msg.id ? <Square className="h-2.5 w-2.5 fill-current text-red-600" /> : <Volume2 className="h-3 w-3" />}
                              <span>{speakingId === msg.id ? 'Stop' : 'Listen'}</span>
                            </button>
                            <CodePreviewButton
                              content={msg.content}
                              onPreview={(sandboxProps) => {
                                const tabId = `code-preview-${msg.id}`
                                const existingTab = tabs.find(t => t.id === tabId)
                                if (existingTab) {
                                  setActiveTabId(tabId)
                                  return
                                }
                                const newTab: PanelTab = {
                                  id: tabId,
                                  title: 'Live Sandbox',
                                  type: 'code',
                                  fileType: 'html',
                                  sandboxProps,
                                  content: (sandboxProps.html || '') + '\n' + (sandboxProps.css || '') + '\n' + (sandboxProps.js || '')
                                }
                                setTabs(prev => [...prev, newTab])
                                setActiveTabId(tabId)
                              }}
                            />
                          </div>
                        )}
                      </div>
                    </div>
                    {msg.role === 'user' && (
                      <Avatar className="h-7 w-7 border border-[#e6dfd8] shrink-0 mt-0.5 shadow-sm">
                        <AvatarFallback className="bg-[#efe9de] text-[#6c6a64] text-xs">
                          <User className="h-3.5 w-3.5" />
                        </AvatarFallback>
                      </Avatar>
                    )}
                  </div>
                ))}
              </div>
            </ScrollArea>
          )}
        </div>

        {/* Anchored bottom input block */}
        <div className="px-6 py-4 border-t border-[#27272a] bg-[#0c0c0e]/30 shrink-0">
          <div className="max-w-3xl mx-auto space-y-2">
            {attachments.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pb-2">
                {attachments.map((att) => (
                  <div
                    key={att.id}
                    className="flex items-center gap-1.5 rounded-lg border border-[#27272a] bg-zinc-950 px-2.5 py-1 text-[11px] text-zinc-400"
                  >
                    <FileText className="h-3.5 w-3.5 text-zinc-500" />
                    <span className="max-w-[120px] truncate">{att.file.name}</span>
                    {att.status === 'uploading' ? (
                      <Loader2 className="h-3 w-3 animate-spin text-violet-400 shrink-0" />
                    ) : (
                      <button onClick={() => removeAttachment(att.id)} className="shrink-0 text-zinc-500 hover:text-zinc-300">
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="relative flex items-center bg-[#efe9de] border border-[#e6dfd8] rounded-[12px] min-h-20 p-3.5 focus-within:border-[#cc785c]/60 shadow-md w-full max-w-3xl mx-auto transition-all duration-200">
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
                className="rounded-[8px] h-10 w-10 hover:bg-[#e8e0d2] text-[#6c6a64] hover:text-[#141413] shrink-0"
              >
                <Paperclip className="h-5 w-5 stroke-[1.5]" />
              </Button>
              <textarea
                ref={textareaRef}
                placeholder={teamMode ? 'Assign your specialists a multi-step task...' : 'Ask anything...'}
                value={input}
                onChange={(e) => {
                  setInput(e.target.value)
                  e.target.style.height = 'auto'
                  e.target.style.height = `${Math.min(e.target.scrollHeight, 140)}px`
                }}
                onKeyDown={handleKeyDown}
                rows={1}
                className="flex-1 bg-transparent border-0 focus:outline-none focus:ring-0 focus-visible:ring-0 resize-none px-4 py-2 text-[15px] text-[#141413] placeholder:text-[#6c6a64] min-h-[40px] max-h-[140px] scrollbar-thin"
                disabled={sending}
              />
              <Button
                variant={isListening ? 'default' : 'ghost'}
                size="icon"
                onClick={toggleVoiceInput}
                disabled={sending}
                className={`rounded-[8px] h-10 w-10 text-[#6c6a64] hover:text-[#141413] shrink-0 ${isListening ? 'bg-[#cc785c]/10 text-[#cc785c] animate-pulse' : 'hover:bg-[#efe9de]'}`}
              >
                {isListening ? <Square className="h-4 w-4 fill-current" /> : <Mic className="h-5 w-5 stroke-[1.5]" />}
              </Button>
              <Button
                onClick={handleSend}
                disabled={sending || (!input.trim() && attachments.length === 0) || (teamMode && teamAgents.length === 0)}
                className="rounded-[8px] h-10 w-10 hover:scale-[1.03] transition-all bg-[#cc785c] hover:bg-[#a9583e] text-white shadow-sm font-medium shrink-0 ml-2"
                size="icon"
                title="Send"
              >
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4 stroke-[2]" />}
              </Button>
            </div>
          </div>
        </div>
      </div>

      {/* 3. RIGHT PANEL: Cursor-Style Editor Canvas */}
      {tabs.length > 0 && (
        <aside className="flex flex-col flex-1 h-full bg-[#18181b] border-l border-[#27272a] overflow-hidden min-w-0">
          {/* Tab Header bar */}
          <div className="flex bg-[#0c0c0e] border-b border-[#27272a] h-9 shrink-0 overflow-x-auto scrollbar-thin select-none">
            {tabs.map((tab) => {
              const isActive = activeTabId === tab.id
              return (
                <div
                  key={tab.id}
                  onClick={() => setActiveTabId(tab.id)}
                  className={`group flex items-center gap-2 px-3.5 border-r border-[#27272a] h-full text-xs cursor-pointer select-none transition-all ${
                    isActive ? 'bg-[#18181b] text-white font-medium shadow-inner' : 'bg-[#0c0c0e]/60 text-zinc-400 hover:bg-zinc-900'
                  }`}
                >
                  {tab.type === 'code' ? (
                    <FileCode className={`h-3.5 w-3.5 shrink-0 ${isActive ? 'text-violet-400' : 'text-zinc-500'}`} />
                  ) : (
                    <FileText className={`h-3.5 w-3.5 shrink-0 ${isActive ? 'text-emerald-400' : 'text-zinc-500'}`} />
                  )}
                  <span className="max-w-[120px] truncate text-[11px] font-sans">{tab.title}</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleCloseTab(tab.id)
                    }}
                    className="text-zinc-500 hover:text-zinc-200 shrink-0 ml-1 opacity-0 group-hover:opacity-100 transition-opacity"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              )
            })}
          </div>

          {/* Tab content view */}
          {activeTab ? (
            <div className="flex-1 flex flex-col overflow-hidden min-h-0">
              {/* Unified Control Header */}
              <div className="flex items-center justify-between px-4 py-2 bg-[#121214] border-b border-[#27272a] text-xs shrink-0 select-none">
                <span className="text-zinc-400 font-mono text-[10px]">
                  {activeTab.title} {activeTab.fileType ? `(${activeTab.fileType.toUpperCase()})` : ''}
                </span>
                
                <div className="flex items-center gap-1.5">
                  {activeTab.type === 'code' && activeTab.sandboxProps && (
                    <button
                      type="button"
                      onClick={() => setShowCodeSource(!showCodeSource)}
                      className="flex items-center gap-1 h-6 px-2.5 text-[10px] rounded border border-[#27272a] bg-[#1e1e24] text-zinc-300 hover:text-white transition-colors"
                    >
                      {showCodeSource ? (
                        <>
                          <Play className="h-3 w-3 text-violet-400" />
                          <span>Show Sandbox</span>
                        </>
                      ) : (
                        <>
                          <CodeIcon className="h-3 w-3 text-violet-400" />
                          <span>Show Code</span>
                        </>
                      )}
                    </button>
                  )}
                  
                  <button
                    type="button"
                    onClick={() => {
                      if (activeTab.content) {
                        navigator.clipboard?.writeText(activeTab.content)
                        alert('Copied to clipboard!')
                      }
                    }}
                    className="h-6 px-2.5 text-[10px] rounded border border-[#27272a] bg-[#1e1e24] text-zinc-300 hover:text-white transition-colors"
                  >
                    Copy
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      alert('Saved to Drive successfully!')
                    }}
                    className="h-6 px-2.5 text-[10px] rounded border border-[#27272a] bg-[#1e1e24] text-zinc-300 hover:text-white transition-colors"
                  >
                    Save to Drive
                  </button>
                </div>
              </div>

              {/* Main Tab Render Body */}
              <div className="flex-1 flex flex-col overflow-hidden relative min-h-0 bg-[#18181b]">
                {activeTab.type === 'code' && activeTab.sandboxProps ? (
                  showCodeSource ? (
                    renderCodeContent(activeTab.content || '')
                  ) : (
                    <CodeSandbox
                      html={activeTab.sandboxProps.html}
                      css={activeTab.sandboxProps.css}
                      js={activeTab.sandboxProps.js}
                      fullHtml={activeTab.sandboxProps.fullHtml}
                      className="h-full border-none rounded-none w-full bg-white flex-1"
                    />
                  )
                ) : activeTab.type === 'document' ? (
                  ['txt', 'md'].includes((activeTab.fileType || '').toLowerCase()) ? (
                    activeTab.content !== undefined ? (
                      renderCodeContent(activeTab.content)
                    ) : (
                      <div className="flex items-center justify-center p-6 text-zinc-500 text-xs">
                        <Loader2 className="h-4 w-4 animate-spin text-zinc-500 mr-2" />
                        Loading document text...
                      </div>
                    )
                  ) : ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'].includes((activeTab.fileType || '').toLowerCase()) ? (
                    <div className="flex-1 flex items-center justify-center bg-[#121214] p-6 overflow-auto">
                      <img
                        src={api.documents.downloadUrl(activeTab.docId!)}
                        alt={activeTab.title}
                        className="max-w-full max-h-full object-contain rounded-lg border border-[#27272a] shadow-2xl bg-zinc-950"
                      />
                    </div>
                  ) : (
                    <iframe
                      src={api.documents.downloadUrl(activeTab.docId!)}
                      className="w-full h-full border-none bg-white flex-1"
                      title={activeTab.title}
                    />
                  )
                ) : null}
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-zinc-550 text-center select-none bg-[#18181b]">
              <FileText className="h-8 w-8 text-zinc-600 mb-2" />
              <p className="text-xs">No active tab content</p>
            </div>
          )}
        </aside>
      )}

      {codePreview && (
        <div className="fixed inset-0 z-30 bg-black/30 animate-fade-in" onClick={() => setCodePreview(null)}>
          <CodePreviewPanel preview={codePreview} onClose={() => setCodePreview(null)} />
        </div>
      )}
    </div>
  )
}

export default function ChatPage() {
  return (
    <Suspense fallback={
      <div className="flex h-[50vh] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-zinc-400" />
      </div>
    }>
      <ChatContent />
    </Suspense>
  )
}
