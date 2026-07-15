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
import { Send, Bot, User, MessageSquare, Paperclip, FileText, ImageIcon, X, Loader2, Upload, Mic, Volume2, Square, Sparkles, Users, CheckCircle2, FolderOpen, Share2, ChevronDown } from 'lucide-react'
import type { AgentId, DocumentInfo } from '@shared/types'
import { CodePreviewButton, CodeSandbox, type CodeSandboxProps, extractCodeFromContent } from '@/components/code-sandbox'
import { CodePreviewPanel } from '@/components/code-preview-panel'
import { FileCode, FileImage, Globe, Play, Code as CodeIcon } from 'lucide-react'




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

  // Split pane resizing states
  const containerRef = useRef<HTMLDivElement>(null)
  const [leftWidthPercent, setLeftWidthPercent] = useState(50)
  const [isResizing, setIsResizing] = useState(false)

  const handleMouseDown = useCallback((e: React.MouseEvent) => {
    e.preventDefault()
    setIsResizing(true)
  }, [])

  useEffect(() => {
    if (!isResizing) return

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return
      const containerRect = containerRef.current.getBoundingClientRect()
      const newLeftWidth = e.clientX - containerRect.left
      const newPercent = (newLeftWidth / containerRect.width) * 100
      const clampedPercent = Math.min(Math.max(newPercent, 20), 80)
      setLeftWidthPercent(clampedPercent)
    }

    const handleMouseUp = () => {
      setIsResizing(false)
    }

    document.addEventListener('mousemove', handleMouseMove)
    document.addEventListener('mouseup', handleMouseUp)

    return () => {
      document.removeEventListener('mousemove', handleMouseMove)
      document.removeEventListener('mouseup', handleMouseUp)
    }
  }, [isResizing])

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
  const mediaRecorderRef = useRef<MediaRecorder | null>(null)
  const audioChunksRef = useRef<Blob[]>([])
  const activeAudioRef = useRef<HTMLAudioElement | null>(null)
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
      if (res.success && res.data) {
        final = { ...att, status: 'done', documentId: res.data.id, imageUrl: res.data.imageUrl, progress: 100 }
        window.dispatchEvent(new Event('refresh-documents-list'))
      } else {
        final = { ...att, status: 'error', progress: 0 }
      }
    } catch {
      final = { ...att, status: 'error', progress: 0 }
    }
    setAttachments((prev) => prev.map((a) => a.id === att.id ? final : a))
    uploadPromises.current.delete(att.id)
    return final
  }, [selectedWorkspace])

  const speakMessage = useCallback(async (id: string, content: string) => {
    if (speakingId === id) {
      if (activeAudioRef.current) {
        activeAudioRef.current.pause()
        activeAudioRef.current = null
      }
      setSpeakingId(null)
      return
    }
    
    // Stop any existing playing audio
    if (activeAudioRef.current) {
      activeAudioRef.current.pause()
      activeAudioRef.current = null
    }

    setSpeakingId(id)

    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/voice/synthesize`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: content }),
        }
      )

      if (!response.ok) {
        throw new Error('Failed to synthesize speech')
      }

      const blob = await response.blob()
      const audioUrl = URL.createObjectURL(blob)
      const audio = new Audio(audioUrl)
      activeAudioRef.current = audio
      
      audio.onended = () => {
        setSpeakingId(null)
        activeAudioRef.current = null
        URL.revokeObjectURL(audioUrl)
      }
      
      audio.onerror = () => {
        setSpeakingId(null)
        activeAudioRef.current = null
        URL.revokeObjectURL(audioUrl)
      }
      
      await audio.play()
    } catch (error) {
      console.error('Text-to-speech error:', error)
      setSpeakingId(null)
    }
  }, [speakingId])

  const toggleVoiceInput = useCallback(async () => {
    if (isListening) {
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
      setIsListening(false)
      return
    }

    if (typeof window === 'undefined' || !navigator.mediaDevices) return

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      mediaRecorderRef.current = recorder
      audioChunksRef.current = []

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data)
        }
      }

      recorder.onstop = async () => {
        // Stop all audio track elements
        stream.getTracks().forEach((track) => track.stop())

        const audioBlob = new Blob(audioChunksRef.current, { type: recorder.mimeType || 'audio/webm' })
        if (audioBlob.size === 0) return

        try {
          const formData = new FormData()
          const ext = recorder.mimeType?.includes('ogg') ? 'ogg' : 'webm'
          formData.append('file', audioBlob, `input.${ext}`)

          const response = await fetch(
            `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/voice/transcribe`,
            {
              method: 'POST',
              body: formData,
            }
          )

          if (response.ok) {
            const data = await response.json()
            if (data.success && data.data?.transcript) {
              const transcript = data.data.transcript
              setInput((current) => `${current}${current ? ' ' : ''}${transcript}`)
            } else if (data.transcript) {
              const transcript = data.transcript
              setInput((current) => `${current}${current ? ' ' : ''}${transcript}`)
            }
          } else {
            console.error('Failed to transcribe audio:', response.statusText)
          }
        } catch (err) {
          console.error('Error uploading/transcribing audio:', err)
        }
      }

      recorder.start()
      setIsListening(true)
    } catch (err) {
      console.error('Failed to start recording:', err)
    }
  }, [isListening])

  const toggleVoiceMode = useCallback(() => {
    setVoiceMode((current) => {
      if (current) {
        if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
          mediaRecorderRef.current.stop()
        }
        if (activeAudioRef.current) {
          activeAudioRef.current.pause()
          activeAudioRef.current = null
        }
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
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop()
    }
    if (activeAudioRef.current) {
      activeAudioRef.current.pause()
      activeAudioRef.current = null
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
      } else {
        console.warn('Failed to load conversations:', res.error)
      }
    } catch (e) {
      console.error('Failed to load conversations:', e)
    } finally {
      setLoadingConversations(false)
    }
  }, [])

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
    const handleOpenDoc = (e: Event) => {
      const doc = (e as CustomEvent).detail
      handleDocumentClick(doc)
    }
    window.addEventListener('open-document-tab', handleOpenDoc)
    return () => window.removeEventListener('open-document-tab', handleOpenDoc)
  }, [handleDocumentClick])

  useEffect(() => {
    const event = new CustomEvent('workspace-changed', { detail: selectedWorkspace })
    window.dispatchEvent(event)
  }, [selectedWorkspace])

  useEffect(() => {
    fetchConversations()
    api.workspaces.list().then((res) => {
      if (res.success && res.data) {
        setWorkspaces(res.data)
      } else {
        console.warn('Failed to load workspaces:', res.error)
      }
    })
    api.agents.list().then((res) => {
      if (res.success && res.data) {
        setCustomAgents(res.data.filter((agent) => agent.custom).map((agent) => ({ id: agent.id, name: agent.name })))
      } else {
        console.warn('Failed to load agents:', res.error)
      }
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
      } else {
        console.error('Failed to load conversation:', res.error)
      }
    } catch (e) {
      console.error('Failed to load conversation:', e)
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
      window.dispatchEvent(new Event('refresh-documents-list'))
    }
  }, [input, attachments, sending, uploadAttachment, conversationId, selectedAgent, teamMode, teamAgents, selectedWorkspace, googleAccessToken, fetchConversations])

  const addFiles = useCallback((files: FileList | File[]) => {
    const fileArray = Array.from(files)
    const newAttachments: Attachment[] = fileArray.map((file) => ({
      id: crypto.randomUUID(),
      file,
      status: 'uploading',
      progress: 0,
      previewUrl: isImage(file) ? URL.createObjectURL(file) : undefined,
    }))
    setAttachments((prev) => [...prev, ...newAttachments])
    // Begin uploading immediately on select so files are ready before Send.
    newAttachments.forEach((att) => {
      uploadPromises.current.set(att.id, uploadAttachment(att))
    })
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
      <div className="flex-1 overflow-auto bg-card text-[#26251e] font-mono text-xs sm:text-sm p-4 select-text border-t border-border scrollbar-thin">
        <div className="flex min-w-full">
          <div className="text-muted-foreground/60 select-none text-right pr-4 border-r border-border mr-4 min-w-[2.5rem]">
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
    <div
      ref={containerRef}
      className={`flex h-screen gap-0 -m-6 overflow-hidden bg-background animate-fade-in relative ${isResizing ? 'select-none cursor-col-resize' : ''}`}
    >
      {/* Explorer panel is merged into the main application sidebar */}

      {/* 2. CENTRAL PANEL: Agents Conversation Feed */}
      <div
        className="flex flex-col h-full bg-background relative min-w-0"
        style={tabs.length > 0 ? { width: `${leftWidthPercent}%`, flex: 'none' } : { flex: 1 }}
        onDragEnter={handleDragEnter}
        onDragLeave={handleDragLeave}
        onDragOver={handleDragOver}
        onDrop={handleDrop}
        ref={dropZoneRef}
      >
        {/* Drag & Drop overlay */}
        {isDragging && (
          <div className="absolute inset-0 z-50 flex items-center justify-center bg-[#26251e]/30 backdrop-blur-xs">
            <div className="text-center p-8 border border-dashed border-primary rounded-[12px] max-w-sm mx-4 bg-card shadow-xs">
              <Upload className="h-10 w-10 mx-auto mb-3 text-primary animate-bounce" />
              <p className="text-sm font-semibold text-[#26251e]">Drop files here to upload</p>
              <p className="text-[11px] text-muted-foreground mt-1">
                We support PDF, DOCX, PPTX, TXT, MD, PNG, JPG, WEBP
              </p>
            </div>
          </div>
        )}

        {/* Top Header / Toolbar */}
        <div className="flex items-center justify-between border-b border-border px-6 py-3 min-h-[56px] shrink-0 bg-card select-none z-10 shadow-xs">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold truncate text-[#26251e] flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-primary shrink-0" />
              <span>{chatTitle || 'New Conversation'}</span>
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="h-8 w-8 hover:bg-secondary rounded-lg" onClick={shareConversation} disabled={!conversationId} title="Share Link">
              <Share2 className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 gap-1.5 hover:bg-secondary rounded-lg px-2.5 ${
                voiceMode ? 'bg-primary/10 text-primary border border-primary/20 shadow-xs' : 'text-muted-foreground'
              }`}
              onClick={toggleVoiceMode}
            >
              <Volume2 className="h-3.5 w-3.5" />
              <span className="text-xs hidden sm:inline">Voice Mode</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 gap-1.5 hover:bg-secondary rounded-lg px-2.5 ${
                teamMode ? 'bg-[#1f8a65]/10 text-[#1f8a65] border border-[#1f8a65]/20' : 'text-muted-foreground'
              }`}
              onClick={() => setTeamMode((current) => !current)}
            >
              <Users className="h-3.5 w-3.5" />
              <span className="text-xs hidden sm:inline">Teamwork</span>
              <span className="rounded bg-[#1f8a65]/10 px-1 py-0.5 text-[9px] font-bold text-[#1f8a65]">BETA</span>
            </Button>

            {!teamMode && (
              <div className="relative flex items-center">
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="h-8 rounded-[8px] bg-card border border-border pl-3 pr-8 text-xs font-semibold text-[#26251e] focus:outline-none hover:bg-secondary/60 transition-all cursor-pointer appearance-none shadow-2xs w-[160px] font-sans"
                >
                  {agents.concat(customAgents).map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-2.5 h-3.5 w-3.5 text-muted-foreground pointer-events-none stroke-[1.5]" />
              </div>
            )}
          </div>
        </div>

        {shareUrl && (
          <div className="mx-6 mt-4 flex items-center gap-2 rounded-[8px] border border-[#1f8a65]/20 bg-[#1f8a65]/5 px-3 py-2 text-xs">
            <Share2 className="h-3.5 w-3.5 text-[#1f8a65]" />
            <span className="font-medium text-[#1f8a65]">Conversation link copied:</span>
            <Input readOnly value={shareUrl} className="ml-auto h-7 max-w-sm text-[10px] bg-card border-border text-[#26251e]" />
          </div>
        )}

        {/* Voice Mode Banner */}
        {voiceMode && (
          <div className="mx-6 mt-4 border border-primary/20 bg-[#f7f7f4] rounded-[12px] p-3 shrink-0">
            <div className="flex items-center gap-3">
              <div className="relative flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary border border-primary/20">
                <Volume2 className="h-3.5 w-3.5" />
                <span className="absolute inset-0 rounded-full border border-primary/30 animate-ping [animation-duration:2.5s]" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-xs font-semibold text-[#26251e]">Voice mode active</p>
                <p className="text-[10px] text-muted-foreground truncate">Speak by pressing the mic button. Agent answers will be spoken back.</p>
              </div>
            </div>
          </div>
        )}


        {/* Team Collaboration Banner */}
        {teamMode && (
          <div className="border-b border-border bg-secondary p-3 shrink-0">
            <div className="max-w-3xl mx-auto flex items-start gap-2 text-xs">
              <Sparkles className="h-3.5 w-3.5 text-primary mt-0.5" />
              <div className="flex-1 min-w-0">
                <p className="font-semibold text-[#26251e] text-[11px] uppercase tracking-wider">Agent Specialist Squad</p>
                <p className="text-[10px] text-muted-foreground">Pick which agents participate collaboratively in order.</p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {teamworkAgents.map((agent) => {
                    const active = teamAgents.includes(agent.id)
                    return (
                      <button
                        key={agent.id}
                        type="button"
                        onClick={() => setTeamAgents((current) => active ? current.filter((id) => id !== agent.id) : [...current, agent.id])}
                        className={`flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-[10px] transition-all ${
                          active ? 'border-primary bg-primary/10 text-primary' : 'border-border text-muted-foreground hover:bg-card'
                        }`}
                      >
                        {active ? <CheckCircle2 className="h-3 w-3 text-primary" /> : <span className="h-2 w-2 rounded-full border border-[#cfcdc4]" />}
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
            <div className="absolute inset-0 flex flex-col items-center justify-center p-6 text-center select-none bg-background">
              <div className="max-w-2xl w-full flex flex-col items-center justify-center space-y-12">
                <div className="space-y-4">
                  <div className="flex justify-center">
                    <div className="h-14 w-14 rounded-[8px] border border-border bg-secondary flex items-center justify-center transition-transform hover:scale-105 duration-300 shadow-xs">
                      <img src="/logo.png" alt="Agents Logo" className="h-7 w-7 object-contain" />
                    </div>
                  </div>
                  <h1 className="text-4xl font-serif font-normal tracking-[-0.01em] text-[#26251e] mb-1">
                    How can I help you today?
                  </h1>
                  <p className="text-sm text-[#5a5852]/80 max-w-md mx-auto leading-relaxed font-sans">
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
                      className="group flex flex-col items-start p-5 rounded-[12px] border border-border bg-card text-left transition-all duration-300 hover:-translate-y-0.5 hover:shadow-xs hover:border-primary/25 active:translate-y-0 shadow-2xs cursor-pointer"
                    >
                      <card.icon className="h-5 w-5 text-muted-foreground group-hover:text-primary transition-colors stroke-[1.5] mb-3" />
                      <span className="text-[15px] font-serif font-normal text-[#26251e] mb-1.5">{card.text}</span>
                      <span className="text-xs text-muted-foreground/85 leading-relaxed font-sans">{card.desc}</span>
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
                      <Avatar className="h-7 w-7 border border-border shrink-0 mt-0.5 shadow-xs">
                        <AvatarFallback className="bg-secondary text-[#5a5852] text-xs">
                          <Bot className="h-3.5 w-3.5 text-primary" />
                        </AvatarFallback>
                      </Avatar>
                    )}
                    <div className={`max-w-[80%] flex flex-col ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
                      {msg.agentId && msg.role === 'assistant' && (
                        <Badge variant="outline" className="mb-1 text-[9px] uppercase tracking-wider font-mono bg-secondary border-border text-muted-foreground">
                          {agents.concat(customAgents).find((a) => a.id === msg.agentId)?.name || msg.agentId}
                        </Badge>
                      )}
                      
                      {/* Message attachments */}
                      {msg.attachments && msg.attachments.length > 0 && (
                        <div className="flex flex-wrap gap-1.5 mb-2">
                          {msg.attachments.map((att, i) => {
                            const isImg = isImageExt(att.name)
                            return isImg && att.documentId ? (
                              <div key={i} className="relative group rounded-lg overflow-hidden border border-border bg-secondary shadow-xs">
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
                                className="flex items-center gap-1.5 rounded-lg border border-border bg-secondary hover:bg-secondary/70 px-2.5 py-1 text-xs text-muted-foreground hover:text-foreground transition-colors shadow-xs"
                              >
                                {isImg ? <ImageIcon className="h-3 w-3 text-[#1f8a65]" /> : <FileText className="h-3 w-3 text-primary" />}
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
                              ? 'bg-card text-[#26251e] border border-border shadow-xs font-sans'
                              : 'text-[#26251e] bg-transparent font-sans'
                          }`}
                        >
                          <pre className="whitespace-pre-wrap font-sans text-xs sm:text-sm">{msg.content}</pre>
                        </div>
                        {msg.role === 'assistant' && msg.content && (
                          <div className="flex items-center gap-3 mt-1.5 px-1 opacity-0 group-hover:opacity-100 transition-opacity select-none">
                            <button
                              type="button"
                              onClick={() => speakMessage(msg.id, msg.content)}
                              className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
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
                      <Avatar className="h-7 w-7 border border-border shrink-0 mt-0.5 shadow-xs">
                        <AvatarFallback className="bg-secondary text-muted-foreground text-xs">
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
        <div className="px-6 py-4 border-t border-border bg-background shrink-0">
          <div className="max-w-3xl mx-auto space-y-2">
            {attachments.length > 0 && (
              <div className="flex flex-wrap gap-1.5 pb-2">
                {attachments.map((att) => (
                  <div
                    key={att.id}
                    className="flex items-center gap-1.5 rounded-[8px] border border-border bg-card px-2.5 py-1 text-[11px] text-[#26251e] shadow-xs"
                  >
                    <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="max-w-[120px] truncate">{att.file.name}</span>
                    {att.status === 'uploading' ? (
                      <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
                    ) : (
                      <button onClick={() => removeAttachment(att.id)} className="shrink-0 text-muted-foreground hover:text-foreground">
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="relative flex items-center bg-card border border-border rounded-[16px] min-h-[56px] p-2 focus-within:border-primary/45 focus-within:ring-1 focus-within:ring-primary/10 shadow-xs w-full max-w-3xl mx-auto transition-all duration-200">
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
                className="rounded-[10px] h-9 w-9 hover:bg-secondary text-muted-foreground hover:text-foreground shrink-0 flex items-center justify-center"
              >
                <Paperclip className="h-4.5 w-4.5 stroke-[1.5]" />
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
                className="flex-1 bg-transparent border-0 px-3 py-1.5 text-xs sm:text-sm text-[#26251e] placeholder-muted-foreground focus:outline-none focus:ring-0 resize-none font-sans min-h-[28px] max-h-[140px] leading-relaxed"
              />
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleVoiceInput}
                  disabled={sending}
                  className={`rounded-[10px] h-9 w-9 text-muted-foreground shrink-0 flex items-center justify-center transition-colors ${
                    isListening 
                      ? 'bg-red-50 text-red-500 animate-pulse hover:bg-red-100' 
                      : 'hover:bg-secondary hover:text-foreground'
                  }`}
                >
                  {isListening ? <Square className="h-3 w-3 fill-current text-red-500" /> : <Mic className="h-4.5 w-4.5 stroke-[1.5]" />}
                </Button>
                <Button
                  onClick={handleSend}
                  disabled={sending || (!input.trim() && attachments.length === 0) || (teamMode && teamAgents.length === 0)}
                  className="rounded-[10px] h-9 w-9 hover:scale-[1.02] transition-all bg-primary hover:bg-primary/90 text-primary-foreground shadow-xs shrink-0 flex items-center justify-center cursor-pointer"
                  size="icon"
                  title="Send"
                >
                  {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4 stroke-[1.8]" />}
                </Button>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 3. RIGHT PANEL: Cursor-Style Editor Canvas */}
      {tabs.length > 0 && (
        <>
          <div
            onMouseDown={handleMouseDown}
            className={`w-1 hover:w-1.5 active:w-1.5 h-full cursor-col-resize select-none shrink-0 transition-all duration-150 z-30 relative ${
              isResizing ? 'bg-primary/50 w-1.5' : 'bg-border hover:bg-primary/30'
            }`}
          >
            <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-[1px] bg-border" />
          </div>
          <aside
            className="flex flex-col h-full bg-secondary border-l border-border overflow-hidden min-w-0"
            style={{ width: `${100 - leftWidthPercent}%`, flex: 'none' }}
          >
          {/* Tab Header bar */}
          <div className="flex bg-[#efe9de]/65 border-b border-border h-9 shrink-0 overflow-x-auto scrollbar-thin select-none">
            {tabs.map((tab) => {
              const isActive = activeTabId === tab.id
              return (
                <div
                  key={tab.id}
                  onClick={() => setActiveTabId(tab.id)}
                  className={`group flex items-center gap-2 px-3.5 border-r border-border h-full text-xs cursor-pointer select-none transition-all ${
                    isActive ? 'bg-[#fafaf7] text-[#26251e] font-semibold shadow-xs border-b border-[#fafaf7]' : 'text-muted-foreground hover:bg-[#fafaf7]/50'
                  }`}
                >
                  {tab.type === 'code' ? (
                    <FileCode className={`h-3.5 w-3.5 shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                  ) : (
                    <FileText className={`h-3.5 w-3.5 shrink-0 ${isActive ? 'text-primary' : 'text-muted-foreground'}`} />
                  )}
                  <span className="max-w-[120px] truncate text-[11px] font-sans">{tab.title}</span>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleCloseTab(tab.id)
                    }}
                    className="text-muted-foreground hover:text-foreground shrink-0 ml-1 opacity-0 group-hover:opacity-100 transition-opacity"
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
              <div className="flex items-center justify-between px-4 py-2 bg-secondary border-b border-border text-xs shrink-0 select-none">
                <span className="text-muted-foreground font-mono text-[10px]">
                  {activeTab.title} {activeTab.fileType ? `(${activeTab.fileType.toUpperCase()})` : ''}
                </span>
                
                <div className="flex items-center gap-1.5">
                  {activeTab.type === 'code' && activeTab.sandboxProps && (
                    <button
                      type="button"
                      onClick={() => setShowCodeSource(!showCodeSource)}
                      className="flex items-center gap-1 h-6 px-2.5 text-[10px] rounded-[6px] border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-secondary/40 transition-colors cursor-pointer"
                    >
                      {showCodeSource ? (
                        <>
                          <Play className="h-3 w-3 text-primary" />
                          <span>Show Sandbox</span>
                        </>
                      ) : (
                        <>
                          <CodeIcon className="h-3 w-3 text-primary" />
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
                    className="h-6 px-2.5 text-[10px] rounded-[6px] border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-secondary/40 transition-colors cursor-pointer"
                  >
                    Copy
                  </button>
                  <button
                    type="button"
                    onClick={() => {
                      alert('Saved to Drive successfully!')
                    }}
                    className="h-6 px-2.5 text-[10px] rounded-[6px] border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-secondary/40 transition-colors cursor-pointer"
                  >
                    Save to Drive
                  </button>
                </div>
              </div>

              {/* Main Tab Render Body */}
              <div className="flex-1 flex flex-col overflow-hidden relative min-h-0 bg-card">
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
                      <div className="flex items-center justify-center p-6 text-muted-foreground text-xs bg-card">
                        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground mr-2" />
                        Loading document text...
                      </div>
                    )
                  ) : ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'].includes((activeTab.fileType || '').toLowerCase()) ? (
                    <div className="flex-1 flex items-center justify-center bg-background p-6 overflow-auto">
                      <img
                        src={api.documents.downloadUrl(activeTab.docId!)}
                        alt={activeTab.title}
                        className="max-w-full max-h-full object-contain rounded-[12px] border border-border shadow-xs bg-card"
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
            <div className="flex-1 flex flex-col items-center justify-center text-muted-foreground text-center select-none bg-background">
              <FileText className="h-8 w-8 text-muted-foreground/60 mb-2" />
              <p className="text-xs">No active tab content</p>
            </div>
          )}
        </aside>
      </>
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
