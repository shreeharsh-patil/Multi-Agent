'use client'

import { useState, useRef, useEffect, useCallback, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useSession } from 'next-auth/react'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import { Send, User, Paperclip, FileText, ImageIcon, X, Loader2, Upload, Mic, Volume2, Square, CheckCircle2, ChevronDown, Copy, RefreshCw, Pencil, AlertCircle, Terminal, MoreHorizontal, ArrowLeft } from 'lucide-react'
import type { AgentId, DocumentInfo } from '@shared/types'
import { CodePreviewButton, CodeSandbox, type CodeSandboxProps } from '@/components/code-sandbox'
import { CodePreviewPanel } from '@/components/code-preview-panel'
import { FileCode, Play, Code as CodeIcon } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { preprocessLaTeX } from '@/lib/latex'
import { ImagePreviewCard } from '@/components/image-preview-card'
import { MermaidWorkspace, repairMermaidMarkdown } from '@/components/mermaid-workspace'
import { clearAccessToken, getAccessToken, setAccessToken } from '@/lib/auth-store'
import { downloadSecureFile } from '@/lib/download'

const typingKeyframes = `
@keyframes typing-dot {
  0%, 40%, 100% { opacity: 0.3; transform: translateY(0); }
  20% { opacity: 1; transform: translateY(-3px); }
}
.typing-dot {
  animation: typing-dot 1.4s ease-in-out infinite;
}
`




const agents = [
  { id: 'auto', name: 'BossAgent (Executive)' },
  { id: 'image', name: 'Image Generation Agent' },
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
  { id: 'data_analysis', name: 'Data Analysis Agent' },
  { id: 'weather_news', name: 'Weather & News Agent' },
  { id: 'gmail', name: 'Gmail Agent' },
  { id: 'tasks', name: 'Tasks Agent' },
  { id: 'youtube', name: 'YouTube Agent' },
  { id: 'engineer', name: 'Engineer Agent' },
  { id: 'pharmacologist', name: 'Pharmacologist Agent' },
  { id: 'doctor', name: 'Doctor Agent' },
  { id: 'finance', name: 'Finance Agent' },
  { id: 'accountant', name: 'Accountant (CA) Agent' },
  { id: 'economics', name: 'Economics Agent' },
  { id: 'architect', name: 'Architect Agent' },
  { id: 'hacker', name: 'Cyber & Security Agent' },
  { id: 'cooking', name: 'Cooking & Chef Agent' },
  { id: 'music', name: 'Music Agent' },
  { id: 'fitness', name: 'Fitness & Health Agent' },
  { id: 'art', name: 'Art & Design Agent' },
]

const isImage = (file: File) => file.type.startsWith('image/')

interface Attachment {
  id: string
  file: File
  status: 'pending' | 'uploading' | 'done' | 'error'
  progress?: number
  documentId?: string
  imageUrl?: string
  previewUrl?: string
  driveFileId?: string
  driveWebViewLink?: string
}

type SentAttachment = {
  name: string
  size: number
  documentId?: string
  driveFileId?: string
  driveWebViewLink?: string
}

const isImageExt = (name: string) => /\.(png|jpg|jpeg|webp|gif|svg|bmp)$/i.test(name)
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

const resolveApiUrl = (url?: string) => url?.startsWith('/api/') ? `${backendUrl}${url}` : url

async function safelyReadResponse(response: Response): Promise<{ message?: string; requestId?: string; body?: unknown }> {
  const raw = await response.text().catch(() => '')
  if (!raw) return { requestId: response.headers.get('x-request-id') || undefined }
  try {
    const body = JSON.parse(raw) as { error?: unknown; detail?: unknown; message?: unknown; requestId?: unknown }
    const error = body.error
    const nestedMessage = typeof error === 'object' && error !== null ? (error as { message?: unknown }).message : undefined
    const message = [nestedMessage, body.message, error, body.detail].find((value): value is string => typeof value === 'string' && value.trim().length > 0)
    const requestId = typeof body.requestId === 'string' ? body.requestId : response.headers.get('x-request-id') || undefined
    return { message, requestId, body }
  } catch {
    return { message: raw.slice(0, 500), requestId: response.headers.get('x-request-id') || undefined }
  }
}

const toSpeechText = (content: string) => content
  .replace(/!\[[^\]]*\]\([^)]*\)/g, 'Generated image.')
  .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
  .replace(/[`#*_>~-]/g, '')
  .trim()

interface PanelTab {
  id: string
  title: string
  type: 'document' | 'code'
  fileType?: string
  content?: string
  sandboxProps?: CodeSandboxProps
  docId?: string
  driveFileId?: string
  driveWebViewLink?: string
}

function ChatContent() {
  const { data: session, status: sessionStatus } = useSession()
  const googleAccessToken = (session as any)?.accessToken as string | undefined
  const googleRefreshToken = (session as any)?.refreshToken as string | undefined
  const ensureBackendAuth = useCallback(async (forceRefresh = false): Promise<string> => {
    const existing = getAccessToken()
    if (existing && !forceRefresh) return existing
    if (sessionStatus !== 'authenticated' || !session?.user?.email || !googleAccessToken) {
      throw new Error('Your session is not ready. Please sign in again.')
    }

    if (forceRefresh) clearAccessToken()
    const result = await api.auth.login({
      email: session.user.email,
      name: session.user.name || session.user.email,
      image: session.user.image || undefined,
      google_id: (session.user as { id?: string }).id,
      access_token: googleAccessToken,
      refresh_token: googleRefreshToken,
    })
    if (!result.success || !result.data?.access_token) {
      throw new Error(result.error || 'Unable to establish a backend session.')
    }
    setAccessToken(result.data.access_token)
    return result.data.access_token
  }, [googleAccessToken, googleRefreshToken, session, sessionStatus])
  const [messages, setMessages] = useState<Array<{
    id: string
    role: 'user' | 'assistant'
    content: string
    error?: boolean
    requestId?: string
    agentId?: string
    attachments?: Array<{ name: string; size: number; documentId?: string; driveFileId?: string; driveWebViewLink?: string }>
    citations?: Array<{
      file_name?: string
      page_number?: number
      section?: string
      text?: string
      score?: number
      document_id?: string
      chunk_id?: string
      chunk_index?: number
    }>
  }>>([])
  const [input, setInput] = useState('')
  const [selectedAgent, setSelectedAgent] = useState<string>('auto')
  const [customAgents, setCustomAgents] = useState<Array<{ id: string; name: string }>>([])
  const [teamMode] = useState(false)
  const [teamAgents] = useState<string[]>(['research', 'coding', 'planner'])

  // Hybrid layout UI states
  const [tabs, setTabs] = useState<PanelTab[]>([])
  const [activeTabId, setActiveTabId] = useState<string | null>(null)
  const [showCodeSource, setShowCodeSource] = useState(false)
  const [compactPreviewOpen, setCompactPreviewOpen] = useState(false)

  // Split pane resizing states
  const containerRef = useRef<HTMLDivElement>(null)
  const [leftWidthPercent, setLeftWidthPercent] = useState(50)
  const [isResizing, setIsResizing] = useState(false)


  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault()
    e.currentTarget.setPointerCapture(e.pointerId)
    setIsResizing(true)
  }, [])

  useEffect(() => {
    if (!isResizing) return

    const handlePointerMove = (e: PointerEvent) => {
      if (!containerRef.current) return
      const containerRect = containerRef.current.getBoundingClientRect()
      const newLeftWidth = e.clientX - containerRect.left
      const newPercent = (newLeftWidth / containerRect.width) * 100
      const clampedPercent = Math.min(Math.max(newPercent, 20), 80)
      setLeftWidthPercent(clampedPercent)
    }

    const handlePointerUp = () => {
      setIsResizing(false)
    }

    document.addEventListener('pointermove', handlePointerMove)
    document.addEventListener('pointerup', handlePointerUp)

    return () => {
      document.removeEventListener('pointermove', handlePointerMove)
      document.removeEventListener('pointerup', handlePointerUp)
    }
  }, [isResizing])

  const searchParams = useSearchParams()
  useEffect(() => {
    const agentParam = searchParams?.get('agent')
    if (agentParam && agents.concat(customAgents).some(a => a.id === agentParam)) {
      setSelectedAgent(agentParam)
    }
  }, [searchParams, customAgents])
  const [, setWorkspaces] = useState<Array<{ id: string; name: string; color: string; documentCount: number }>>([])
  const [selectedWorkspace, setSelectedWorkspace] = useState('all')
  const [voiceMode, setVoiceMode] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [speakingId, setSpeakingId] = useState<string | null>(null)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [sending, setSending] = useState(false)
  const [chatDebug, setChatDebug] = useState<{ requestId?: string; status: string; agent?: string; step?: string; startedAt: number; error?: string } | null>(null)
  const [showDebugPanel] = useState(false)
  const [orchestration, setOrchestration] = useState<{ complexity?: string; domain?: string; agents: Array<{ agent_id: string; label: string; reason?: string; status?: 'queued' | 'working' | 'complete' | 'failed' }> } | null>(null)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
  const [openActionsId, setOpenActionsId] = useState<string | null>(null)
  const [editText, setEditText] = useState('')
  const [showScrollToBottom, setShowScrollToBottom] = useState(false)
  // Use a ref to track sending state synchronously — React setState is async
  // and won't prevent double-clicks fast enough when both calls see sending=false.
  const sendingRef = useRef(false)
  // Holds the AbortController for the in-flight streaming request so the user
  // can stop generation mid-stream.
  const abortControllerRef = useRef<AbortController | null>(null)
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

  // The Radix ScrollArea scrolls its inner viewport, not the Root element.
  const getScrollViewport = useCallback((): HTMLElement | null => {
    return scrollRef.current?.querySelector('[data-radix-scroll-area-viewport]') ?? null
  }, [])

  const scrollToBottom = useCallback((behavior: ScrollBehavior = 'smooth') => {
    const vp = getScrollViewport()
    if (vp) vp.scrollTo({ top: vp.scrollHeight, behavior })
  }, [getScrollViewport])

  useEffect(() => {
    // Only auto-follow new messages when already near the bottom, so we don't
    // yank the view away while the user is reading scrollback.
    const vp = getScrollViewport()
    if (!vp) return
    const nearBottom = vp.scrollHeight - vp.scrollTop - vp.clientHeight < 120
    if (nearBottom) scrollToBottom('auto')
  }, [messages, getScrollViewport, scrollToBottom])

  // Toggle the scroll-to-bottom button based on scroll position.
  useEffect(() => {
    const vp = getScrollViewport()
    if (!vp) return
    const onScroll = () => {
      const distance = vp.scrollHeight - vp.scrollTop - vp.clientHeight
      setShowScrollToBottom(distance > 200)
    }
    vp.addEventListener('scroll', onScroll)
    onScroll()
    return () => vp.removeEventListener('scroll', onScroll)
  }, [getScrollViewport])

  const uploadAttachment = useCallback(async (att: Attachment): Promise<Attachment> => {
    setAttachments((prev) => prev.map((a) => a.id === att.id ? { ...a, status: 'uploading', progress: 0 } : a))
    let final: Attachment
    try {
      const uploadWorkspace = selectedWorkspace !== 'all' && selectedWorkspace !== 'unfiled' ? selectedWorkspace : undefined
      const res = await api.documents.upload(att.file, 'default', (progress) => {
        setAttachments((prev) => prev.map((a) => a.id === att.id ? { ...a, progress } : a))
      }, uploadWorkspace, googleAccessToken, googleRefreshToken)
      if (res.success && res.data) {
        final = { ...att, status: 'done', documentId: res.data.id, imageUrl: res.data.imageUrl, driveFileId: res.data.driveFileId, driveWebViewLink: res.data.driveWebViewLink, progress: 100 }
        if (res.data.driveFileId) {
          final.driveFileId = res.data.driveFileId
          final.driveWebViewLink = res.data.driveWebViewLink
        }
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
  }, [selectedWorkspace, googleAccessToken, googleRefreshToken])

  const speakMessage = useCallback(async (id: string, content: string) => {
    if (speakingId === id) {
      if (activeAudioRef.current) {
        activeAudioRef.current.pause()
        activeAudioRef.current = null
      }
      window.speechSynthesis?.cancel()
      setSpeakingId(null)
      return
    }
    
    // Stop any existing playing audio
    if (activeAudioRef.current) {
      activeAudioRef.current.pause()
      activeAudioRef.current = null
    }

    setSpeakingId(id)

    let audioUrl: string | null = null
    try {
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'}/api/voice/synthesize`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ text: toSpeechText(content) }),
        }
      )

      if (!response.ok) {
        let detail = `TTS failed (${response.status})`
        try {
          const err = await response.json()
          if (err.detail) detail = err.detail
        } catch {}
        throw new Error(detail)
      }

      const blob = await response.blob()
      audioUrl = URL.createObjectURL(blob)
      const audio = new Audio(audioUrl)
      activeAudioRef.current = audio
      
      audio.onended = () => {
        setSpeakingId(null)
        activeAudioRef.current = null
        if (audioUrl) URL.revokeObjectURL(audioUrl)
      }
      
      audio.onerror = () => {
        setSpeakingId(null)
        activeAudioRef.current = null
        if (audioUrl) URL.revokeObjectURL(audioUrl)
      }
      
      await audio.play()
    } catch (error) {
      if (audioUrl) {
        URL.revokeObjectURL(audioUrl)
      }
      console.error('Text-to-speech error:', error)
      if ('speechSynthesis' in window) {
        const utterance = new SpeechSynthesisUtterance(toSpeechText(content))
        utterance.onend = () => setSpeakingId(null)
        utterance.onerror = () => setSpeakingId(null)
        window.speechSynthesis.cancel()
        window.speechSynthesis.speak(utterance)
      } else {
        setSpeakingId(null)
      }
    }
  }, [speakingId])

  const toggleVoiceInput = useCallback(async () => {
    if (isListening) {
      if ((window as any).__speechRecognitionInstance) {
        (window as any).__speechRecognitionInstance.stop()
      }
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop()
      }
      setIsListening(false)
      return
    }

    if (typeof window === 'undefined') return

    // Try Web Speech API SpeechRecognition first for instant real-time transcription
    const SpeechRecognition = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition
    if (SpeechRecognition) {
      try {
        const recognition = new SpeechRecognition()
        recognition.continuous = true
        recognition.interimResults = true
        recognition.lang = 'en-US'

        recognition.onresult = (event: any) => {
          let transcript = ''
          for (let i = event.resultIndex; i < event.results.length; i++) {
            transcript += event.results[i][0].transcript
          }
          if (transcript) {
            setInput((prev) => {
              const base = prev.trim()
              return base ? `${base} ${transcript.trim()}` : transcript.trim()
            })
          }
        }

        recognition.onerror = (event: any) => {
          console.error('Speech recognition error:', event.error)
          setIsListening(false)
        }

        recognition.onend = () => {
          setIsListening(false)
        }

        (window as any).__speechRecognitionInstance = recognition
        recognition.start()
        setIsListening(true)
        return
      } catch (err) {
        console.warn('SpeechRecognition failed, falling back to MediaRecorder:', err)
      }
    }

    if (!navigator.mediaDevices) return

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
            const transcript = data.data?.transcript || data.transcript
            if (transcript) {
              setInput((current) => `${current}${current ? ' ' : ''}${transcript}`)
            }
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
        window.speechSynthesis?.cancel()
        setIsListening(false)
        setSpeakingId(null)
      }
      return !current
    })
  }, [])
  void toggleVoiceMode

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
    window.speechSynthesis?.cancel()
  }, [])

  const [conversationId, setConversationId] = useState<string>()
  // Track which conversationIds we created locally this session so we don't
  // re-fetch and overwrite in-progress streaming messages.
  const locallyCreatedIds = useRef<Set<string>>(new Set())
  const loadedIdRef = useRef<string | null>(null)
  const [, setConversations] = useState<Array<{
    id: string
    title: string
    agentId?: string
    messageCount: number
    lastMessage: string
    updatedAt: string
  }>>([])
  const [, setLoadingConversations] = useState(true)
  const [, setChatTitle] = useState('')
  const [loadingHistory, setLoadingHistory] = useState(false)

  // Persist unsent composer text per-conversation so it survives navigation
  // and refreshes. Keyed by conversation id ("new" for a fresh chat).
  const draftKey = `chat-draft:${conversationId ?? 'new'}`
  const draftRestoredRef = useRef<string | null>(null)
  useEffect(() => {
    // Restore the saved draft once per conversation switch.
    if (draftRestoredRef.current === draftKey) return
    draftRestoredRef.current = draftKey
    try {
      const saved = localStorage.getItem(draftKey)
      setInput(saved ?? '')
    } catch {
      // localStorage may be unavailable (private mode); ignore.
    }
  }, [draftKey])
  useEffect(() => {
    try {
      if (input.trim()) localStorage.setItem(draftKey, input)
      else localStorage.removeItem(draftKey)
    } catch {
      // ignore storage failures
    }
  }, [input, draftKey])

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
    setCompactPreviewOpen(true)
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

    // Fetch full document metadata (includes Drive info)
    const metaRes = await api.documents.get(doc.id)
    if (metaRes.success && metaRes.data) {
      const d = metaRes.data as any
      setTabs(prev => prev.map(t => t.id === doc.id ? {
        ...t,
        driveFileId: d.driveFileId,
        driveWebViewLink: d.driveWebViewLink,
      } : t))
    }

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

  // Sync workspace with sidebar selection via events
  useEffect(() => {
    const handleWorkspaceChange = (e: Event) => {
      const workspaceId = (e as CustomEvent).detail
      setSelectedWorkspace(workspaceId)
    }
    window.addEventListener('workspace-changed', handleWorkspaceChange)
    return () => window.removeEventListener('workspace-changed', handleWorkspaceChange)
  }, [])


  useEffect(() => {
    fetchConversations()
    api.workspaces.list().then((res) => {
      if (res.success && res.data) {
        setWorkspaces(res.data)
      } else {
        console.warn('Failed to load workspaces:', res.error)
      }
    }).catch(() => {})
    api.agents.list().then((res) => {
      if (res.success && res.data) {
        setCustomAgents(res.data.filter((agent) => agent.custom).map((agent) => ({ id: agent.id, name: agent.name })))
      } else {
        console.warn('Failed to load agents:', res.error)
      }
    }).catch(() => {})
  }, [fetchConversations])



  const [historyError, setHistoryError] = useState<string | null>(null)
  const activeFetchIdRef = useRef<number>(0)

  // Start a new conversation
  const startNewConversation = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    sendingRef.current = false
    setSending(false)
    loadedIdRef.current = null
    setConversationId(undefined)
    setChatTitle('')
    setMessages([])
    setAttachments([])
    setLoadingHistory(false)
    setHistoryError(null)
    if (typeof window !== 'undefined') window.history.replaceState(null, '', '/chat')
  }, [])

  const loadConversation = useCallback((targetId: string) => {
    if (!targetId) return
    const fetchId = ++activeFetchIdRef.current
    loadedIdRef.current = targetId
    setConversationId(targetId)
    setLoadingHistory(true)
    setHistoryError(null)

    api.chat.getConversation(targetId)
      .then((res) => {
        if (fetchId !== activeFetchIdRef.current) return
        if (res.success && res.data) {
          const conv = res.data
          setChatTitle(conv.title || '')
          if (conv.agentId) setSelectedAgent(conv.agentId)
          if (Array.isArray(conv.messages)) {
            setMessages(
              conv.messages.map((m: any, idx: number) => ({
                id: m.id || `msg_${idx}`,
                role: (m.role === 'user' ? 'user' : 'assistant') as 'user' | 'assistant',
                content: m.content || '',
                agentId: m.agentId,
                requestId: m.metadata?.request_id,
                attachments: m.metadata?.attachments,
                citations: m.citations,
              }))
            )
          } else {
            setMessages([])
          }
          setHistoryError(null)
        } else {
          console.warn('Conversation not found or empty:', res.error)
          setChatTitle('')
          setMessages([])
          setHistoryError(null)
        }
      })
      .catch((err) => {
        if (fetchId !== activeFetchIdRef.current) return
        console.error('Failed to load chat history:', err)
        setHistoryError('Unable to load this conversation. Please check your connection or retry.')
      })
      .finally(() => {
        if (fetchId === activeFetchIdRef.current) {
          setLoadingHistory(false)
        }
      })
  }, [])

  useEffect(() => {
    window.addEventListener('start-new-chat', startNewConversation)
    return () => window.removeEventListener('start-new-chat', startNewConversation)
  }, [startNewConversation])

  // Global keyboard shortcuts: Ctrl/Cmd+Shift+O starts a new chat; pressing
  // "/" while not already typing focuses the composer.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null
      const typing = target && (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable)
      if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key.toLowerCase() === 'o') {
        e.preventDefault()
        startNewConversation()
        return
      }
      if (e.key === '/' && !typing) {
        e.preventDefault()
        textareaRef.current?.focus()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [startNewConversation])

  // Single source of truth for URL search parameter sync & conversation loading
  const convParam = searchParams?.get('id') || searchParams?.get('c') || searchParams?.get('conversation_id') || searchParams?.get('conversation')
  useEffect(() => {
    if (!convParam) {
      if (loadedIdRef.current !== null && !locallyCreatedIds.current.has(conversationId || '')) {
        startNewConversation()
      }
      return
    }

    if (loadedIdRef.current === convParam || locallyCreatedIds.current.has(convParam)) {
      return
    }

    loadConversation(convParam)
  }, [convParam, conversationId, loadConversation, startNewConversation])

  const handleSend = useCallback(async (
    overrideText?: string,
    retryRequestId?: string,
    retryAttachments: SentAttachment[] = [],
  ) => {
    // Synchronous ref guard prevents double-submits even when state hasn't updated yet
    if (sendingRef.current) return
    const isRegenerate = typeof overrideText === 'string'
    if (!isRegenerate && ((!input.trim() && attachments.length === 0) || (teamMode && teamAgents.length === 0))) return

    const text = isRegenerate ? overrideText!.trim() : input.trim()
    const attachmentCount = isRegenerate ? retryAttachments.length : attachments.length
    const clientRequestId = retryRequestId || crypto.randomUUID()
    const currentConvId = conversationId
    const currentAgent = teamMode || selectedAgent === 'auto' ? undefined : selectedAgent
    const currentWorkspace = selectedWorkspace === 'all' ? undefined : selectedWorkspace === 'unfiled' ? '__unfiled__' : selectedWorkspace

    sendingRef.current = true
    setSending(true)
    setOrchestration(null)
    setChatDebug({ status: 'connecting', step: 'frontend_request', startedAt: Date.now() })

    // NextAuth and the backend use different JWTs. The bridge exchanges the
    // Google session in the background, but a user can press Send before that
    // exchange finishes. Establish it here before uploads or chat requests.
    try {
      await ensureBackendAuth()
    } catch (authError) {
      const message = authError instanceof Error ? authError.message : 'Authentication failed.'
      const failedRequestId = retryRequestId || crypto.randomUUID()
      if (!isRegenerate) {
        setMessages((prev) => [...prev, {
          id: crypto.randomUUID(),
          role: 'user',
          content: text || `Uploaded ${attachmentCount} file(s)`,
          requestId: failedRequestId,
        }])
      }
      setMessages((prev) => [...prev, {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: message,
        error: true,
      }])
      setChatDebug((current) => current ? { ...current, status: 'error', step: 'authentication', error: message } : current)
      sendingRef.current = false
      setSending(false)
      return
    }

    // Attachments already began uploading on select. Await any in-flight
    // upload; only kick off a fresh upload for ones that never started
    // (e.g. added programmatically) or previously errored.
    // On regenerate there are no new attachments to process.
    const uploadedAttachments: SentAttachment[] = [...retryAttachments]
    if (!isRegenerate) {
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
          driveFileId: updated.driveFileId,
          driveWebViewLink: updated.driveWebViewLink,
        })
      }
      attachments.forEach((att) => { if (att.previewUrl) URL.revokeObjectURL(att.previewUrl) })
      setAttachments([])

      const userMsg = {
        id: crypto.randomUUID(),
        role: 'user' as const,
        content: text || `Uploaded ${attachmentCount} file(s)`,
        attachments: uploadedAttachments,
        requestId: clientRequestId,
      }
      setMessages((prev) => [...prev, userMsg])
      setInput('')
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto'
      }
    }

    // Add placeholder assistant message (will be updated incrementally via SSE)
    const assistantId = crypto.randomUUID()
    setMessages((prev) => [...prev, { id: assistantId, role: 'assistant', content: '' }])

    // Fresh AbortController for this request so Stop can cancel it.
    const abortController = new AbortController()
    abortControllerRef.current = abortController

    // Try SSE streaming first, fall back to non-streaming
    let streamingAttempted = false
    let streamCompleted = false
    let streamRequestId = ''
    let accumulatedContent = ''
    let streamServerError = ''
    let frameId: number | null = null

    try {
      const requestPayload = {
        request_id: clientRequestId,
        message: text || `Uploaded ${attachmentCount} file(s)`,
        conversation_id: currentConvId,
        agent_id: currentAgent,
        team_agents: teamMode ? teamAgents as AgentId[] : undefined,
        workspace_id: currentWorkspace,
        attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
      }
      let streamResponse: Response | null = null
      let lastOpenError: unknown = null
      for (let attempt = 0; attempt < 3; attempt += 1) {
        try {
          streamResponse = await api.chat.stream(requestPayload, googleAccessToken, abortController.signal, googleRefreshToken)
          if (streamResponse.ok) break
          if (streamResponse.status === 401 && attempt === 0) {
            await ensureBackendAuth(true)
            continue
          }
          lastOpenError = new Error(`HTTP ${streamResponse.status}`)
          if (streamResponse.status < 500 && streamResponse.status !== 429) break
        } catch (openError) {
          lastOpenError = openError
        }
        if (attempt < 2) await new Promise((resolve) => setTimeout(resolve, 350 * 2 ** attempt))
      }

      if (!streamResponse) {
        throw lastOpenError || new Error('Unable to connect to the chat service')
      }
      if (!streamResponse.ok) {
        const errorBody = await safelyReadResponse(streamResponse)
        console.error('Chat API failed', {
          status: streamResponse.status,
          statusText: streamResponse.statusText,
          requestId: errorBody.requestId,
          error: errorBody.body ?? errorBody.message,
        })
        streamRequestId = errorBody.requestId || streamRequestId
        throw new Error(errorBody.message || `Chat request failed with status ${streamResponse.status}`)
      }

      const contentType = streamResponse.headers.get('content-type') || ''
      if (!contentType.includes('text/event-stream')) {
        throw new Error('Not an SSE stream')
      }

      streamingAttempted = true
      setChatDebug((current) => current ? { ...current, status: 'connected', step: 'sse_open' } : current)

      const reader = streamResponse.body?.getReader()
      if (!reader) throw new Error('No reader available')

      const decoder = new TextDecoder()
      let buffer = ''
      let newConvId = currentConvId

      const readWithTimeout = async () => {
        let timeoutId: ReturnType<typeof setTimeout> | undefined
        try {
          return await Promise.race([
            reader.read(),
            new Promise<never>((_, reject) => {
              timeoutId = setTimeout(() => {
                const timeout = new Error('The chat response timed out while waiting for data.')
                timeout.name = 'StreamTimeout'
                reject(timeout)
              }, 75000)
            }),
          ])
        } finally {
          if (timeoutId) clearTimeout(timeoutId)
        }
      }

      // Accumulate content in a ref and flush to React state at ~60 fps
      // to avoid hundreds of re-renders per second during streaming.
      const pendingContentRef = { current: '' }
      const flushState = () => {
        frameId = null
        if (pendingContentRef.current === accumulatedContent) return
        pendingContentRef.current = accumulatedContent
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: accumulatedContent }
              : msg,
          ),
        )
      }

      while (true) {
        const { done, value } = await readWithTimeout()
        if (done) break

        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, '\n')

        // Parse complete SSE blocks. Keeping the entire unfinished block in
        // the buffer is important because event/data lines can arrive in
        // separate network reads.
        const blocks = buffer.split('\n\n')
        buffer = blocks.pop() || ''

        for (const block of blocks) {
          let currentEvent = 'message'
          const dataLines: string[] = []
          for (const line of block.split('\n')) {
            if (line.startsWith('event:')) currentEvent = line.slice(6).trim()
            if (line.startsWith('data:')) dataLines.push(line.slice(5).trimStart())
          }
          if (!dataLines.length) continue

          try {
            const data = JSON.parse(dataLines.join('\n'))

            if (currentEvent === 'start' && data.request_id) {
                streamRequestId = data.request_id
                setChatDebug((current) => current ? { ...current, requestId: data.request_id, status: 'streaming', step: 'api_start' } : current)
            } else if (currentEvent === 'chunk' && data.text) {
                setChatDebug((current) => current ? { ...current, status: 'streaming', step: 'response_chunk' } : current)
                accumulatedContent += data.text
                // Schedule a single visual update per frame
                if (frameId === null) {
                  frameId = requestAnimationFrame(flushState)
                }
            } else if (currentEvent === 'plan' && Array.isArray(data.agents)) {
                setOrchestration({
                  complexity: data.complexity,
                  domain: data.domain,
                  agents: data.agents.map((agent: any) => ({ ...agent, status: 'queued' })),
                })
            } else if (currentEvent === 'agent_started' && data.agent_id) {
                setChatDebug((current) => current ? { ...current, agent: data.agent_id, step: 'agent_started' } : current)
                setOrchestration((current) => current ? {
                  ...current,
                  agents: current.agents.map((agent) => agent.agent_id === data.agent_id ? { ...agent, status: 'working' } : agent),
                } : current)
            } else if (currentEvent === 'agent_complete' && data.agent_id) {
                setChatDebug((current) => current ? { ...current, agent: data.agent_id, step: 'agent_complete' } : current)
                setOrchestration((current) => current ? {
                  ...current,
                  agents: current.agents.map((agent) => agent.agent_id === data.agent_id ? { ...agent, status: data.success ? 'complete' : 'failed' } : agent),
                } : current)
            } else if (currentEvent === 'agent' && data.agent_id) {
                setChatDebug((current) => current ? { ...current, agent: data.agent_id, step: 'agent' } : current)
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, agentId: data.agent_id }
                      : msg,
                  ),
                )
            } else if (currentEvent === 'complete' && data.conversation_id) {
                setChatDebug((current) => current ? { ...current, status: 'complete', step: 'response_complete' } : current)
                streamCompleted = true
                newConvId = data.conversation_id
                // Mark this id as locally created so we don't refetch it
                locallyCreatedIds.current.add(data.conversation_id)
                loadedIdRef.current = data.conversation_id
                if (frameId !== null) cancelAnimationFrame(frameId)
                accumulatedContent = data.output || accumulatedContent
                setConversationId(data.conversation_id)
                if (typeof window !== 'undefined') {
                  const url = new URL(window.location.href)
                  url.searchParams.set('id', data.conversation_id)
                  window.history.replaceState(null, '', url.toString())
                }
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, content: data.output || accumulatedContent, citations: data.citations || msg.citations }
                      : msg,
                  ),
                )
            } else if (currentEvent === 'error' && data.error) {
                streamServerError = String(data.error)
                setChatDebug((current) => current ? { ...current, status: 'error', step: 'server_error', error: data.error } : current)
                if (frameId !== null) cancelAnimationFrame(frameId)
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, content: `Error: ${data.error}` }
                      : msg,
                  ),
                )
            }
          } catch (parseError) {
            console.error('[chat] malformed SSE event', { parseError, block })
          }
        }
      }

      // A clean network close without a completion event is not a successful
      // response. Treat it as a failure so the assistant bubble never stays blank.
      if (streamServerError) {
        throw new Error(streamServerError)
      }
      if (!streamCompleted) {
        throw new Error(`Chat stream closed before completion${streamRequestId ? ` (request ${streamRequestId})` : ''}.`)
      }
      if (!accumulatedContent.trim()) {
        throw new Error('The model returned an empty response.')
      }

      // Cancel any remaining frame and apply the final state
      if (frameId !== null) cancelAnimationFrame(frameId)
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? { ...msg, content: accumulatedContent || msg.content }
            : msg,
        ),
      )
      if (newConvId && newConvId !== currentConvId) {
        loadedIdRef.current = newConvId
        setConversationId(newConvId)
        if (typeof window !== 'undefined') {
          const url = new URL(window.location.href)
          url.searchParams.set('id', newConvId)
          window.history.replaceState(null, '', url.toString())
        }
      }
    } catch (err) {
      let terminalError: unknown = err
      // User pressed Stop: keep whatever streamed so far, mark it as stopped.
      if (err instanceof DOMException && err.name === 'AbortError') {
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: msg.content ? msg.content + '\n\n_(stopped)_' : '_(stopped)_' }
              : msg,
          ),
        )
        return
      }

      // If we already received a valid response text during streaming, keep it!
      if (accumulatedContent.trim().length >= 30) {
        if (frameId !== null) cancelAnimationFrame(frameId)
        setMessages((prev) =>
          prev.map((msg) =>
            msg.id === assistantId
              ? { ...msg, content: accumulatedContent, error: false }
              : msg,
          ),
        )
        return
      }

      // Only retry through the non-streaming endpoint when the streaming
      // request never reached the server. Once an SSE response is accepted,
      // it may already be executing/persisting the request; replaying it
      // would duplicate agent work and conversation messages.
      if (!streamingAttempted) {
        try {
        const staleConversation = /(?:^|\b)(?:404:\s*)?conversation not found\b/i.test(
          err instanceof Error ? err.message : '',
        )
        if (staleConversation && currentConvId) {
          // Do not weaken backend authorization for a conversation owned by
          // another user. Retry the original request once as a new chat with
          // no conversation ID; the already-rendered user message and the
          // existing assistant placeholder are reused.
          console.warn('Chat conversation is unavailable; retrying as a new conversation', { conversationId: currentConvId })
        }
        const res = await api.chat.send({
          request_id: clientRequestId,
          message: text || `Uploaded ${attachmentCount} file(s)`,
          conversation_id: staleConversation ? undefined : currentConvId,
          agent_id: currentAgent,
          team_agents: teamMode ? teamAgents as AgentId[] : undefined,
          workspace_id: currentWorkspace,
          attachments: uploadedAttachments.length > 0 ? uploadedAttachments : undefined,
        }, googleAccessToken, googleRefreshToken)
        if (res.success && res.data) {
          locallyCreatedIds.current.add(res.data.conversation_id)
          loadedIdRef.current = res.data.conversation_id
          setConversationId(res.data.conversation_id)
          if (typeof window !== 'undefined') {
            const url = new URL(window.location.href)
            url.searchParams.set('id', res.data.conversation_id)
            window.history.replaceState(null, '', url.toString())
          }
          setMessages((prev) =>
            prev.map((msg) =>
              msg.id === assistantId
                ? {
                    ...msg,
                    content: res.data!.output,
                    error: false,
                    agentId: res.data!.agent_traces?.[0]?.agent_id,
                    citations: res.data!.citations || msg.citations,
                  }
                : msg,
            ),
          )
          return
        }
        throw new Error(res.error || 'The non-streaming chat request failed.')
        } catch (fallbackErr) {
          terminalError = fallbackErr
          console.error('Chat non-streaming fallback failed:', {
            requestId: streamRequestId || undefined,
            error: fallbackErr instanceof Error ? fallbackErr.message : fallbackErr,
          })
        }
      }

      const rawErrorMessage = terminalError instanceof Error ? terminalError.message : 'The chat request failed.'
      const errorMessage = /(?:HTTP\s*)?401|authentication required|not authenticated/i.test(rawErrorMessage)
        ? 'Your session expired. Please sign in again and retry.'
        : rawErrorMessage
      console.error('Chat request failed', {
        requestId: streamRequestId || undefined,
        error: errorMessage,
        streamOpened: streamingAttempted,
        streamServerError: streamServerError || undefined,
      })
      setChatDebug((current) => current ? { ...current, status: 'error', step: 'request_error', error: errorMessage } : current)

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === assistantId
            ? {
                ...msg,
                content: accumulatedContent || `Unable to generate a response. Please retry.${streamRequestId ? ` (Request ID: ${streamRequestId})` : ''}`,
                error: true,
                requestId: streamRequestId || undefined,
              }
            : msg,
        ),
      )
    } finally {
      sendingRef.current = false
      setSending(false)
      setOrchestration(null)
      abortControllerRef.current = null
      // Refresh side-panel document list and sidebar conversation history on send completion
      window.dispatchEvent(new Event('refresh-documents-list'))
      window.dispatchEvent(new Event('refresh-conversations-list'))
    }
  }, [input, attachments, uploadAttachment, conversationId, selectedAgent, teamMode, teamAgents, selectedWorkspace, googleAccessToken, googleRefreshToken, ensureBackendAuth])

  // Stop an in-flight streaming generation.
  const handleStop = useCallback(() => {
    abortControllerRef.current?.abort()
  }, [])

  // Regenerate the last assistant reply: drop it and re-send the prior user message.
  const handleRegenerate = useCallback(() => {
    if (sendingRef.current) return
    setMessages((prev) => {
      const lastUserIdx = [...prev].map((m) => m.role).lastIndexOf('user')
      if (lastUserIdx === -1) return prev
      const lastUser = prev[lastUserIdx]
      if (!lastUser) return prev
      // Drop everything after the last user message (i.e. the assistant reply).
      const trimmed = prev.slice(0, lastUserIdx + 1)
      // Kick off regeneration after state settles.
      setTimeout(() => handleSend(lastUser.content, lastUser.requestId, lastUser.attachments || []), 0)
      return trimmed
    })
  }, [handleSend])

  // Begin editing a user message.
  const startEdit = useCallback((id: string, content: string) => {
    setEditingId(id)
    setEditText(content)
  }, [])

  const cancelEdit = useCallback(() => {
    setEditingId(null)
    setEditText('')
  }, [])

  // Save an edited user message: replace its text, drop everything after it,
  // and resend so the assistant answers the revised message.
  const saveEdit = useCallback((id: string) => {
    if (sendingRef.current) return
    const newText = editText.trim()
    if (!newText) return
    setEditingId(null)
    setEditText('')
    setMessages((prev) => {
      const idx = prev.findIndex((m) => m.id === id)
      if (idx === -1) return prev
      // Keep messages up to and including the edited one, with updated content.
      const trimmed = prev.slice(0, idx + 1).map((m) =>
        m.id === id ? { ...m, content: newText } : m,
      )
      const edited = prev[idx]
      setTimeout(() => handleSend(newText, edited?.requestId, edited?.attachments || []), 0)
      return trimmed
    })
  }, [editText, handleSend])

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
    setAttachments((prev) => {
      const att = prev.find((a) => a.id === id)
      if (att?.previewUrl) URL.revokeObjectURL(att.previewUrl)
      return prev.filter((a) => a.id !== id)
    })
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

  useEffect(() => {
    if (!compactPreviewOpen) return
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setCompactPreviewOpen(false)
    }
    window.addEventListener('keydown', handleEscape)
    return () => window.removeEventListener('keydown', handleEscape)
  }, [compactPreviewOpen])

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
    <>
    <style>{typingKeyframes}</style>
    <div
      ref={containerRef}
      className={`relative flex h-full min-h-0 w-full min-w-0 gap-0 overflow-hidden bg-background animate-fade-in ${isResizing ? 'select-none cursor-col-resize' : ''}`}
    >
      {/* Explorer panel is merged into the main application sidebar */}

      {/* 2. CENTRAL PANEL: Agents Conversation Feed */}
      <div
        className={`relative flex h-full min-h-0 min-w-0 flex-col bg-background ${tabs.length > 0 ? 'w-full flex-1 xl:w-[var(--chat-left-width)] xl:flex-none' : 'w-full flex-1'}`}
        style={{ '--chat-left-width': `${leftWidthPercent}%` } as React.CSSProperties}
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

        {/* Top Header / Toolbar (Hidden per user request)
        <div className="flex items-center justify-between border-b border-border px-3 sm:px-6 py-2 sm:py-3 min-h-[48px] sm:min-h-[56px] shrink-0 bg-card select-none z-10 shadow-xs">
          <div className="min-w-0">
            <h2 className="text-sm font-semibold truncate text-[#26251e] flex items-center gap-2">
              <MessageSquare className="h-4 w-4 text-primary shrink-0" />
              <span>{chatTitle || 'New Conversation'}</span>
            </h2>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="icon" className="hidden sm:inline-flex h-8 w-8 hover:bg-secondary rounded-lg" onClick={exportConversation} disabled={messages.length === 0} title="Export as Markdown">
              <Download className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
            <Button variant="ghost" size="icon" className="hidden sm:inline-flex h-8 w-8 hover:bg-secondary rounded-lg" onClick={shareConversation} disabled={!conversationId} title="Share Link">
              <Share2 className="h-3.5 w-3.5 text-muted-foreground" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className={`h-8 w-8 hover:bg-secondary rounded-lg sm:hidden ${
                voiceMode ? 'bg-primary/10 text-primary border border-primary/20 shadow-xs' : 'text-muted-foreground'
              }`}
              onClick={toggleVoiceMode}
              title="Voice Mode"
            >
              <Volume2 className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 gap-1.5 hover:bg-secondary rounded-lg px-1.5 sm:px-2.5 ${
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
              className={`h-8 gap-1.5 hover:bg-secondary rounded-lg px-1.5 sm:px-2.5 ${
                teamMode ? 'bg-[#1f8a65]/10 text-[#1f8a65] border border-[#1f8a65]/20' : 'text-muted-foreground'
              }`}
              onClick={toggleTeamMode}
            >
              <Bot className="h-3.5 w-3.5" />
              <span className="text-xs hidden sm:inline">Teamwork</span>
              <span className="hidden sm:inline rounded bg-[#1f8a65]/10 px-1 py-0.5 text-[9px] font-bold text-[#1f8a65]">BETA</span>
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className={`h-8 gap-1.5 hover:bg-secondary rounded-lg px-1.5 sm:px-2.5 ${
                showDebugPanel ? 'bg-primary/10 text-primary border border-primary/20 shadow-xs' : 'text-muted-foreground'
              }`}
              onClick={() => setShowDebugPanel(!showDebugPanel)}
              title="Toggle Developer Debug Panel"
            >
              <Terminal className="h-3.5 w-3.5" />
              <span className="text-xs hidden sm:inline">Debug</span>
            </Button>

            {!teamMode && (
              <div className="relative flex items-center">
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="h-8 rounded-[8px] bg-card border border-border pl-2 sm:pl-3 pr-6 sm:pr-8 text-[10px] sm:text-xs font-semibold text-[#26251e] focus:outline-none hover:bg-secondary/60 transition-all cursor-pointer appearance-none shadow-2xs w-[120px] sm:w-[160px] font-sans"
                >
                  {agents.concat(customAgents).map((agent) => (
                    <option key={agent.id} value={agent.id}>
                      {agent.name}
                    </option>
                  ))}
                </select>
                <ChevronDown className="absolute right-1.5 sm:right-2.5 h-3 w-3 sm:h-3.5 sm:w-3.5 text-muted-foreground pointer-events-none stroke-[1.5]" />
              </div>
            )}
          </div>
        </div>

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

        {showDebugPanel && (
          <div className="mx-3 sm:mx-6 mt-3 rounded-xl border border-border bg-card p-3 shadow-xs text-xs font-mono">
            <div className="flex items-center justify-between border-b border-border pb-2 mb-2 font-sans">
              <span className="font-semibold text-foreground flex items-center gap-2">
                <Terminal className="h-4 w-4 text-primary" /> Developer Debug Panel & System State
              </span>
              <Badge variant="outline" className="text-[10px] uppercase font-mono">
                State: {chatDebug?.status === 'complete' ? 'SUCCESS' : chatDebug?.status === 'error' ? 'FAILED_WITH_REASON' : sending ? 'RUNNING' : 'IDLE'}
              </Badge>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px] text-muted-foreground">
              <div><span className="text-foreground font-medium">Status:</span> {chatDebug?.status || 'idle'}</div>
              <div><span className="text-foreground font-medium">Step:</span> {chatDebug?.step || 'idle'}</div>
              <div><span className="text-foreground font-medium">Active Agent:</span> {chatDebug?.agent || selectedAgent || 'orchestrator'}</div>
              <div><span className="text-foreground font-medium">Request ID:</span> {chatDebug?.requestId ? chatDebug.requestId.slice(0, 8) + '...' : '—'}</div>
              <div><span className="text-foreground font-medium">Domain:</span> {orchestration?.domain || 'general'}</div>
              <div><span className="text-foreground font-medium">Complexity:</span> {orchestration?.complexity || 'standard'}</div>
              <div><span className="text-foreground font-medium">Specialists:</span> {orchestration?.agents?.length || 0}</div>
              <div><span className="text-foreground font-medium">Elapsed:</span> {chatDebug?.startedAt ? `${Math.max(0, Date.now() - chatDebug.startedAt)}ms` : '0ms'}</div>
            </div>
            {chatDebug?.error && (
              <div className="mt-2 text-destructive bg-destructive/10 p-2 rounded-md font-sans text-xs">
                ⚠️ Error: {chatDebug.error}
              </div>
            )}
          </div>
        )}

        {/* Message Feeds Scroll Area */}
        <div className="flex-1 relative min-h-0 overflow-hidden">
          {loadingHistory && messages.length === 0 ? (
            <div className="flex h-full items-center justify-center bg-background">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : historyError ? (
            <div className="flex h-full flex-col items-center justify-center space-y-4 bg-background p-6 text-center select-none">
              <div className="rounded-full bg-destructive/10 p-3 text-destructive">
                <AlertCircle className="h-6 w-6" />
              </div>
              <div className="space-y-1">
                <h3 className="text-base font-semibold text-foreground">Unable to load this conversation</h3>
                <p className="text-xs text-muted-foreground max-w-sm">{historyError}</p>
              </div>
              <div className="flex items-center gap-3 pt-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => convParam && loadConversation(convParam)}
                  className="gap-2"
                >
                  <RefreshCw className="h-3.5 w-3.5" />
                  Retry
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => startNewConversation()}
                >
                  Go back to chats
                </Button>
              </div>
            </div>
          ) : messages.length === 0 ? (
            <div 
              onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
              onDrop={(e) => {
                e.preventDefault();
                e.stopPropagation();
                if (e.dataTransfer?.files?.length) {
                  handleFileSelect({ target: { files: e.dataTransfer.files } } as any);
                }
              }}
                className="flex h-full w-full min-w-0 flex-col items-center justify-center overflow-y-auto bg-background p-4 text-center scrollbar-thin select-none sm:p-8"
            >
              <div className="max-w-xl w-full flex flex-col items-center justify-center space-y-6 py-8">
                {/* Logo & Welcoming Header */}
                <div className="space-y-3">
                  <div className="flex justify-center">
                    <div className="h-16 w-16 flex items-center justify-center transition-transform hover:scale-105 duration-300">
                      <Image src="/developer-avatar.png" alt="Agents Logo" width={64} height={64} className="h-16 w-16 object-contain" />
                    </div>
                  </div>
                  <h1 className="text-2xl sm:text-4xl font-semibold tracking-tight text-[#26251e] font-sans">
                    What can I help you build or learn today?
                  </h1>
                  <p className="text-xs sm:text-sm text-muted-foreground/80 max-w-md mx-auto leading-relaxed font-sans">
                    Ask a question, analyze documents, write code, or run multi-agent research in a calm, distraction-free workspace.
                  </p>
                </div>

                {/* 5 Small Subtle Suggested Prompts */}
                <div className="flex flex-wrap items-center justify-center gap-2 pt-2 max-w-lg mx-auto">
                  {[
                    "Explain Operating Systems",
                    "Summarize my PDF",
                    "Generate Exam Notes",
                    "Create Flashcards",
                    "Research Quantum Computing",
                  ].map((promptText) => (
                    <button
                      key={promptText}
                      onClick={() => handleSuggestionClick(promptText)}
                      className="text-xs bg-secondary/70 hover:bg-secondary border border-border/80 text-foreground px-3.5 py-1.5 rounded-full transition-all duration-200 cursor-pointer font-medium hover:border-primary/40 shadow-2xs hover:scale-[1.02] active:scale-[0.98]"
                    >
                      {promptText}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <ScrollArea ref={scrollRef} className="h-full w-full min-w-0 px-2 py-3 sm:px-6 sm:py-6">
              <div className="mx-auto w-full min-w-0 max-w-none space-y-6">
                {messages.map((msg, idx) => (
                  <div key={msg.id} className={`flex min-w-0 gap-2 sm:gap-3.5 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                    {msg.role === 'assistant' && (
                      <div className="h-7 w-7 rounded-full border border-border shrink-0 mt-0.5 shadow-xs overflow-hidden bg-secondary flex items-center justify-center">
                        <Image src="/developer-avatar.png" alt="AI" width={28} height={28} className="h-full w-full object-contain" />
                      </div>
                    )}
                    <div className={`flex w-full min-w-0 max-w-[calc(100%_-_2.25rem)] flex-col sm:max-w-[92%] ${msg.role === 'user' ? 'items-end' : 'items-start'}`}>
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
                                <Image
                                  src={api.documents.downloadUrl(att.documentId)}
                                  alt={att.name}
                                  width={200}
                                  height={140}
                                  className="max-w-[200px] max-h-[140px] object-cover cursor-pointer hover:opacity-90 transition-opacity"
                                  onClick={() => handleDocumentClick({ id: att.documentId!, fileName: att.name, fileType: 'png' } as any)}
                                  unoptimized
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

                      <div className="group relative max-w-full min-w-0">
                        {msg.role === 'user' && editingId === msg.id ? (
                          <div className="w-full min-w-0 rounded-[12px] border border-border bg-card p-2 shadow-xs">
                            <textarea
                              value={editText}
                              onChange={(e) => setEditText(e.target.value)}
                              onKeyDown={(e) => {
                                if (e.key === 'Enter' && !e.shiftKey) {
                                  e.preventDefault()
                                  saveEdit(msg.id)
                                } else if (e.key === 'Escape') {
                                  e.preventDefault()
                                  cancelEdit()
                                }
                              }}
                              autoFocus
                              rows={3}
                              className="w-full min-w-0 resize-none bg-transparent px-1 py-0.5 text-base text-[#26251e] focus:outline-none sm:text-sm"
                            />
                            <div className="flex items-center justify-end gap-2 mt-1.5">
                              <button
                                type="button"
                                onClick={cancelEdit}
                                className="px-2.5 py-1 text-[11px] rounded-[6px] text-muted-foreground hover:bg-secondary/60 transition-colors"
                              >
                                Cancel
                              </button>
                              <button
                                type="button"
                                onClick={() => saveEdit(msg.id)}
                                disabled={!editText.trim()}
                                className="px-2.5 py-1 text-[11px] rounded-[6px] bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors"
                              >
                                Save &amp; resend
                              </button>
                            </div>
                          </div>
                        ) : (
                        <div
                          className={`max-w-full min-w-0 rounded-[12px] px-3 py-2.5 text-sm leading-relaxed sm:px-4 ${
                            msg.role === 'user'
                              ? 'bg-card text-[#26251e] border border-border shadow-xs font-sans'
                              : 'text-[#26251e] bg-transparent font-sans'
                          }`}
                        >
                          {msg.role === 'assistant' && !msg.content && sending ? (
                            orchestration && orchestration.agents.length > 0 ? (
                              <div className="w-full min-w-0 space-y-2 rounded-xl border border-border/80 bg-card/90 px-3.5 py-3 shadow-xs" role="status" aria-label="AI team working">
                                <div className="flex items-center gap-2 text-xs font-semibold text-foreground">
                                  <Loader2 className="h-3.5 w-3.5 animate-spin text-primary shrink-0" />
                                  <span>{orchestration.complexity === 'complex' ? 'Assembling specialist team…' : 'Understanding your request…'}</span>
                                </div>
                                <div className="space-y-1.5 pt-1">
                                  {orchestration.agents.map((agent) => (
                                    <div key={agent.agent_id} className="flex items-center justify-between gap-2 text-xs">
                                      <div className="flex items-center gap-2 min-w-0">
                                        {agent.status === 'complete' ? (
                                          <CheckCircle2 className="h-3.5 w-3.5 text-[#1f8a65] shrink-0" />
                                        ) : agent.status === 'failed' ? (
                                          <X className="h-3.5 w-3.5 text-destructive shrink-0" />
                                        ) : agent.status === 'working' ? (
                                          <Loader2 className="h-3.5 w-3.5 animate-spin text-primary shrink-0" />
                                        ) : (
                                          <span className="h-2 w-2 rounded-full bg-muted-foreground/30 shrink-0" />
                                        )}
                                        <span className={`truncate ${agent.status === 'working' ? 'font-medium text-foreground' : agent.status === 'complete' ? 'text-muted-foreground' : agent.status === 'failed' ? 'text-destructive/80 line-through' : 'text-muted-foreground/70'}`}>
                                          {agent.label}
                                        </span>
                                      </div>
                                      <span className="text-[10px] text-muted-foreground uppercase font-mono shrink-0">
                                        {agent.status === 'working' ? 'Running' : agent.status === 'complete' ? 'Done' : agent.status === 'failed' ? 'Skipped' : 'Queued'}
                                      </span>
                                    </div>
                                  ))}
                                </div>
                              </div>
                            ) : (
                              <span className="inline-flex items-center gap-1.5 h-6 text-xs text-muted-foreground" role="status" aria-label="Typing">
                                <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                                <span>Thinking…</span>
                              </span>
                            )
                          ) : (
                            <div className="w-full min-w-0 max-w-full break-words text-xs leading-relaxed [overflow-wrap:anywhere] sm:text-sm">
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm, [remarkMath, { singleDollar: true }]]}
                                rehypePlugins={[rehypeKatex]}
                                components={{
                                  a: ({ href, children }) => {
                                    const resolved = resolveApiUrl(href)
                                    const textContent = typeof children === 'string' ? children.toLowerCase() : ''
                                    const isDownload = resolved?.includes('/download') || textContent.includes('download')
                                    if (isDownload && resolved) {
                                      return (
                                        <button
                                          type="button"
                                          onClick={(e) => {
                                            e.preventDefault()
                                            e.stopPropagation()
                                            downloadSecureFile(resolved, 'generated-image.png')
                                          }}
                                          className="inline-flex max-w-full items-center gap-1 break-all font-medium text-primary underline underline-offset-2 hover:text-primary/80 cursor-pointer"
                                        >
                                          {children}
                                        </button>
                                      )
                                    }
                                    return (
                                      <a href={resolved} target="_blank" rel="noopener noreferrer" className="break-all text-primary underline underline-offset-2 hover:text-primary/80">{children}</a>
                                    )
                                  },
                                  img: ({ src, alt }) => typeof src === 'string' ? (
                                    <ImagePreviewCard src={resolveApiUrl(src) || src} alt={alt || 'Generated image'} />
                                  ) : null,
                                  code: ({ className, children, ...props }) => {
                                    const isInline = !className
                                    if (className?.includes('language-mermaid')) {
                                      const source = String(children).replace(/\n$/, '')
                                      return <MermaidWorkspace content={`\`\`\`mermaid\n${source}\n\`\`\``} title="Diagram" />
                                    }
                                    return isInline ? (
                                      <code className="max-w-full break-all rounded-md bg-muted/60 px-1.5 py-0.5 font-mono text-xs text-foreground/80" {...props}>{children}</code>
                                    ) : (
                                      <pre className="my-1 mb-3 max-w-full overflow-x-auto rounded-xl border border-border/40 bg-muted/40 p-3 scrollbar-thin sm:p-4">
                                        <code className={`${className || ''} text-xs font-mono leading-relaxed`} {...props}>{children}</code>
                                      </pre>
                                    )
                                  },
                                  pre: ({ children }) => <>{children}</>,
                                  p: ({ children }) => <p className="mb-2 last:mb-0 leading-relaxed">{children}</p>,
                                  ul: ({ children }) => <ul className="list-disc pl-5 mb-2 space-y-1">{children}</ul>,
                                  ol: ({ children }) => <ol className="list-decimal pl-5 mb-2 space-y-1">{children}</ol>,
                                  li: ({ children }) => <li className="leading-relaxed">{children}</li>,
                                  strong: ({ children }) => <strong className="font-semibold text-foreground">{children}</strong>,
                                  em: ({ children }) => <em className="italic">{children}</em>,
                                  h1: ({ children }) => <h1 className="text-lg font-bold mb-2 mt-3 text-foreground">{children}</h1>,
                                  h2: ({ children }) => <h2 className="text-base font-bold mb-1.5 mt-3 text-foreground">{children}</h2>,
                                  h3: ({ children }) => <h3 className="text-sm font-semibold mb-1 mt-2.5 text-foreground">{children}</h3>,
                                  blockquote: ({ children }) => <blockquote className="border-l-2 border-primary/30 pl-3 py-0.5 mb-2 text-muted-foreground italic">{children}</blockquote>,
                                  hr: () => <hr className="my-3 border-border" />,
                                  table: ({ children }) => (
                                    <div className="my-4 w-full overflow-x-auto rounded-xl border border-border/80 bg-card/60 shadow-sm backdrop-blur-sm scrollbar-thin">
                                      <table className="w-full text-left text-xs sm:text-sm border-collapse min-w-[480px]">{children}</table>
                                    </div>
                                  ),
                                  thead: ({ children }) => (
                                    <thead className="bg-muted/70 text-foreground font-semibold border-b border-border/80">{children}</thead>
                                  ),
                                  tbody: ({ children }) => (
                                    <tbody className="divide-y divide-border/40 text-foreground/90">{children}</tbody>
                                  ),
                                  tr: ({ children }) => (
                                    <tr className="hover:bg-muted/40 transition-colors duration-150">{children}</tr>
                                  ),
                                  th: ({ children }) => (
                                    <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/40 border-r border-border/30 last:border-r-0">{children}</th>
                                  ),
                                  td: ({ children }) => (
                                    <td className="px-4 py-3 align-top border-r border-border/20 last:border-r-0 leading-relaxed font-normal">{children}</td>
                                  ),
                                  div: ({ className, children, ...props }) => {
                                    if (className?.includes('math') || className?.includes('katex-display')) {
                                      return (
                                        <div className="math-display my-3 max-w-full overflow-x-auto scrollbar-thin text-center py-2 bg-muted/10 rounded-lg" {...props}>
                                          {children}
                                        </div>
                                      )
                                    }
                                    return <div className={className} {...props}>{children}</div>
                                  },
                                }}
                              >
                                {repairMermaidMarkdown(preprocessLaTeX(msg.content))}
                              </ReactMarkdown>
                              {msg.error && (
                                <button
                                  type="button"
                                  disabled={sending}
                                  onClick={() => {
                                    const previousUser = [...messages].slice(0, idx).reverse().find((candidate) => candidate.role === 'user')
                                    setMessages((prev) => prev.filter((m) => m.id !== msg.id))
                                    if (previousUser?.content) handleSend(previousUser.content, previousUser.requestId, previousUser.attachments || [])
                                  }}
                                  className="mt-2 inline-flex items-center gap-1.5 rounded-md border border-primary/30 px-2.5 py-1 text-[11px] font-medium text-primary hover:bg-primary/10 disabled:opacity-50"
                                >
                                  <RefreshCw className="h-3 w-3" /> Retry
                                </button>
                              )}
                            </div>
                          )}
                          {msg.role === 'assistant' && msg.citations && msg.citations.length > 0 && (
                            <div className="mt-3 border-t border-border/50 pt-2.5">
                              <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-wider mb-1.5">
                                Sources
                              </p>
                              <div className="flex flex-wrap gap-1.5">
                                {msg.citations.map((cit, ci) => (
                                  <button
                                    key={`${cit.document_id || cit.file_name || 'cit'}-${ci}`}
                                    type="button"
                                    onClick={() => {
                                      if (cit.document_id) window.open(`/documents?doc=${encodeURIComponent(cit.document_id)}`, '_blank', 'noopener,noreferrer')
                                    }}
                                    title={cit.text || undefined}
                                    className="inline-flex items-center gap-1.5 px-2 py-1 text-[11px] rounded-full bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-colors max-w-full"
                                  >
                                    <FileText className="h-3 w-3 shrink-0" />
                                    <span className="truncate">{cit.file_name || 'Document'}</span>
                                    {cit.page_number ? <span className="opacity-70 shrink-0">· p.{cit.page_number}</span> : null}
                                    {typeof cit.score === 'number' ? <span className="opacity-70 shrink-0">· {(cit.score * 100).toFixed(0)}%</span> : null}
                                  </button>
                                ))}
                              </div>
                            </div>
                          )}
                        </div>
                        )}
                        {msg.role === 'user' && msg.content && editingId !== msg.id && !sending && (
                          <div className="mt-1.5 flex items-center justify-end gap-3 px-1 opacity-100 transition-opacity select-none md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100">
                            <button
                              type="button"
                              onClick={() => startEdit(msg.id, msg.content)}
                              className="flex min-h-9 items-center gap-1 text-[10px] text-muted-foreground transition-colors hover:text-foreground"
                            >
                              <Pencil className="h-3 w-3" />
                              <span>Edit</span>
                            </button>
                          </div>
                        )}
                        {msg.role === 'assistant' && msg.content && (
                          <>
                          <button
                            type="button"
                            onClick={() => setOpenActionsId((current) => current === msg.id ? null : msg.id)}
                            className="mt-1 flex h-9 w-9 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground md:hidden"
                            aria-label="Show message actions"
                            aria-expanded={openActionsId === msg.id}
                          >
                            <MoreHorizontal className="h-4 w-4" />
                          </button>
                          <div className={`${openActionsId === msg.id ? 'flex' : 'hidden'} mt-1.5 max-w-full flex-wrap items-center gap-x-3 gap-y-1 px-1 opacity-100 transition-opacity select-none md:flex md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100`}>
                            <button
                              type="button"
                              onClick={() => speakMessage(msg.id, msg.content)}
                              className="flex min-h-9 items-center gap-1 text-[10px] text-muted-foreground transition-colors hover:text-foreground"
                            >
                              {speakingId === msg.id ? <Square className="h-2.5 w-2.5 fill-current text-red-600" /> : <Volume2 className="h-3 w-3" />}
                              <span>{speakingId === msg.id ? 'Stop' : 'Listen'}</span>
                            </button>
                            <button
                              type="button"
                              onClick={() => {
                                navigator.clipboard?.writeText(msg.content)
                                setCopiedId(msg.id)
                                setTimeout(() => setCopiedId((c) => (c === msg.id ? null : c)), 1500)
                              }}
                              className="flex min-h-9 items-center gap-1 text-[10px] text-muted-foreground transition-colors hover:text-foreground"
                            >
                              {copiedId === msg.id ? <CheckCircle2 className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                              <span>{copiedId === msg.id ? 'Copied' : 'Copy'}</span>
                            </button>
                            {idx === messages.length - 1 && !sending && (
                              <button
                                type="button"
                                onClick={handleRegenerate}
                                className="flex min-h-9 items-center gap-1 text-[10px] text-muted-foreground transition-colors hover:text-foreground"
                              >
                                <RefreshCw className="h-3 w-3" />
                                <span>Regenerate</span>
                              </button>
                            )}
                            <CodePreviewButton
                              content={msg.content}
                              onPreview={(sandboxProps) => {
                                const tabId = `code-preview-${msg.id}`
                                const existingTab = tabs.find(t => t.id === tabId)
                                if (existingTab) {
                                  setActiveTabId(tabId)
                                  setCompactPreviewOpen(true)
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
                                setCompactPreviewOpen(true)
                              }}
                            />
                            <button
                              type="button"
                              onClick={async () => {
                                try {
                                  const result = await api.study.exportDocument({
                                    title: 'AI Response',
                                    content: msg.content,
                                    format: 'pdf',
                                    scope: 'complete',
                                    subject: 'Academic Learning System',
                                  })
                                  if (result.success && result.blob) {
                                    const url = URL.createObjectURL(result.blob)
                                    const a = document.createElement('a')
                                    a.href = url
                                    a.download = result.fileName || `ai-response-${Date.now()}.pdf`
                                    document.body.appendChild(a)
                                    a.click()
                                    a.remove()
                                    setTimeout(() => URL.revokeObjectURL(url), 2000)
                                    return
                                  }
                                  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
                                  const token = getAccessToken()
                                  if (token) headers.Authorization = `Bearer ${token}`
                                  const fallback = await fetch(`${backendUrl}/api/reports`, {
                                    method: 'POST',
                                    headers,
                                    body: JSON.stringify({ title: 'AI Response', content: msg.content, polish: false }),
                                  })
                                  if (!fallback.ok) throw new Error(`PDF export failed (${fallback.status})`)
                                  const data = await fallback.json()
                                  const downloadUrl = data.data?.downloadUrl || data.downloadUrl
                                  if (!downloadUrl) throw new Error('PDF download URL was not returned')
                                  await downloadSecureFile(downloadUrl, `ai-response-${Date.now()}.pdf`)
                                } catch (err) {
                                  console.error('Failed to export PDF:', err)
                                  window.alert('PDF export failed. Please try again.')
                                }
                              }}
                              className="flex min-h-9 items-center gap-1 text-[10px] text-muted-foreground transition-colors hover:text-foreground"
                            >
                              <svg className="h-3 w-3" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                                <path d="M12 15V3m0 12-4-4m4 4 4-4"/><rect x="2" y="17" width="20" height="4" rx="1"/>
                              </svg>
                              <span>PDF</span>
                            </button>
                          </div>
                          </>
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
          {showScrollToBottom && messages.length > 0 && (
            <button
              type="button"
              onClick={() => scrollToBottom('smooth')}
              title="Scroll to bottom"
              className="absolute bottom-3 left-1/2 z-10 flex h-11 w-11 -translate-x-1/2 items-center justify-center rounded-full border border-border bg-card text-muted-foreground shadow-md transition-colors hover:bg-secondary/60 hover:text-foreground"
              aria-label="Scroll to bottom"
            >
              <ChevronDown className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Anchored bottom input block */}
        <div className="shrink-0 border-t border-border bg-background px-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))] pt-2.5 sm:px-6 sm:py-4">
          <div className="mx-auto w-full min-w-0 max-w-none space-y-1.5 sm:space-y-2">
            {attachments.length > 0 && (
              <div className="flex max-w-full flex-wrap gap-1.5 pb-1 sm:pb-2">
                {attachments.map((att) => (
                  <div
                    key={att.id}
                    className="flex max-w-full min-w-0 items-center gap-1.5 rounded-[8px] border border-border bg-card px-2.5 py-1 text-[11px] text-[#26251e] shadow-xs"
                  >
                    <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                    <span className="min-w-0 max-w-[min(9rem,50vw)] truncate">{att.file.name}</span>
                    {att.status === 'uploading' ? (
                      <Loader2 className="h-3 w-3 animate-spin text-primary shrink-0" />
                    ) : (
                      <button onClick={() => removeAttachment(att.id)} className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground hover:bg-secondary hover:text-foreground" aria-label={`Remove ${att.file.name}`}>
                        <X className="h-3 w-3" />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            <div className="relative flex min-h-[56px] w-full min-w-0 items-end rounded-[16px] border border-border bg-card p-1.5 shadow-xs transition-all duration-200 focus-within:border-primary/45 focus-within:ring-1 focus-within:ring-primary/10 sm:items-center sm:p-2">
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
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[10px] text-muted-foreground hover:bg-secondary hover:text-foreground"
                aria-label="Attach files"
                title="Attach files"
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
                className="min-h-[40px] min-w-0 flex-1 resize-none border-0 bg-transparent px-1.5 py-2.5 font-sans text-base leading-relaxed text-[#26251e] placeholder-muted-foreground focus:outline-none focus:ring-0 sm:max-h-[140px] sm:px-3 sm:text-sm"
              />
              <div className="flex shrink-0 items-center gap-0.5 sm:gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={toggleVoiceInput}
                  disabled={sending}
                  className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-[10px] text-muted-foreground transition-colors ${
                    isListening 
                      ? 'bg-red-50 text-red-500 animate-pulse hover:bg-red-100' 
                      : 'hover:bg-secondary hover:text-foreground'
                  }`}
                  aria-label={isListening ? 'Stop voice input' : 'Start voice input'}
                  title={isListening ? 'Stop voice input' : 'Start voice input'}
                >
                  {isListening ? <Square className="h-3 w-3 fill-current text-red-500" /> : <Mic className="h-4.5 w-4.5 stroke-[1.5]" />}
                </Button>
                <Button
                  onClick={sending ? handleStop : () => handleSend()}
                  disabled={!sending && ((!input.trim() && attachments.length === 0) || (teamMode && teamAgents.length === 0))}
                  className="flex h-11 w-11 shrink-0 items-center justify-center rounded-[10px] bg-primary text-primary-foreground shadow-xs transition-colors hover:bg-primary/90 cursor-pointer"
                  size="icon"
                  title={sending ? 'Stop generation' : 'Send message'}
                  aria-label={sending ? 'Stop generation' : 'Send message'}
                >
                  {sending ? <Square className="h-3.5 w-3.5 fill-current" /> : <Send className="h-4 w-4 stroke-[1.8]" />}
                </Button>
              </div>
            </div>
            <div className="flex min-w-0 items-center justify-end px-1 text-[10px] text-muted-foreground select-none sm:justify-between">
              <span className="hidden sm:inline">
                <kbd className="font-sans">Enter</kbd> to send · <kbd className="font-sans">Shift+Enter</kbd> for newline · <kbd className="font-sans">/</kbd> to focus
              </span>
              {input.trim() && (
                <span>{input.trim().split(/\s+/).length} words · {input.length} chars</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* 3. RIGHT PANEL CONTENT (shared between desktop + mobile) */}
      {tabs.length > 0 && (
        <>
          {/* Desktop: resizer */}
          <div
            onPointerDown={handlePointerDown}
            className="relative z-30 hidden h-full w-2 shrink-0 touch-none cursor-col-resize select-none transition-colors hover:bg-primary/5 xl:block"
            role="separator"
            aria-label="Resize chat and preview panels"
            aria-orientation="vertical"
          >
            <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-[1px] bg-border" />
          </div>

          {/* Desktop right panel (flex child, percentage width) */}
          <aside
            className="hidden h-full min-w-0 flex-col overflow-hidden border-l border-border bg-secondary xl:flex"
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
                    className="ml-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-md text-muted-foreground opacity-100 transition-opacity hover:bg-secondary hover:text-foreground 2xl:opacity-0 2xl:group-hover:opacity-100 2xl:group-focus-within:opacity-100"
                    aria-label={`Close ${tab.title}`}
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
              <div className="flex min-w-0 shrink-0 items-center justify-between gap-2 border-b border-border bg-secondary px-3 py-2 text-xs select-none 2xl:px-4">
                <span className="min-w-0 truncate font-mono text-[10px] text-muted-foreground">
                  {activeTab.title} {activeTab.fileType ? `(${activeTab.fileType.toUpperCase()})` : ''}
                </span>
                
                <div className="flex shrink-0 items-center gap-1.5">
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
                    onClick={async () => {
                      if (activeTab.driveWebViewLink) {
                        window.open(activeTab.driveWebViewLink, '_blank', 'noopener')
                      } else if (activeTab.docId) {
                        const btn = (document.activeElement as HTMLElement)
                        btn.textContent = 'Uploading...'
                        try {
                          const res = await api.documents.uploadToDrive(activeTab.docId, googleAccessToken)
                          if (res.success && res.data) {
                            setTabs(prev => prev.map(t => t.id === activeTab.id ? {
                              ...t, driveFileId: res.data!.driveFileId, driveWebViewLink: res.data!.driveWebViewLink,
                            } : t))
                            window.open(res.data.driveWebViewLink, '_blank', 'noopener')
                          }
                        } catch {
                          // ignore
                        }
                      }
                    }}
                    className="h-6 px-2.5 text-[10px] rounded-[6px] border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-secondary/40 transition-colors cursor-pointer"
                  >
                    {activeTab.driveWebViewLink ? 'Open in Drive' : 'Save to Drive'}
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
                      <Image
                        src={api.documents.downloadUrl(activeTab.docId!)}
                        alt={activeTab.title}
                        width={800}
                        height={600}
                        className="max-w-full max-h-full object-contain rounded-[12px] border border-border shadow-xs bg-card"
                        unoptimized
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

          {/* Compact preview for mobile and tablet; split panes remain desktop-only. */}
          <div className={`${compactPreviewOpen ? 'flex' : 'hidden'} fixed inset-0 z-40 h-screen h-[100svh] supports-[height:100dvh]:h-dvh w-full min-w-0 flex-col bg-secondary xl:hidden`} role="dialog" aria-modal="true" aria-label="Document and code preview">
            <div className="flex min-h-14 min-w-0 shrink-0 items-center gap-2 border-b border-border bg-card px-2 pb-2 pt-[max(0.5rem,env(safe-area-inset-top))] sm:px-3">
              <button
                type="button"
                onClick={() => setCompactPreviewOpen(false)}
                className="flex h-11 shrink-0 items-center gap-1.5 rounded-lg px-2 text-xs font-medium text-muted-foreground hover:bg-secondary hover:text-foreground cursor-pointer"
                aria-label="Back to chat"
                autoFocus
              >
                <ArrowLeft className="h-4 w-4" />
                <span>Chat</span>
              </button>
              <span className="min-w-0 flex-1 truncate text-xs font-semibold">{activeTab?.title || 'Document'}</span>
              {activeTab?.type === 'code' && activeTab.sandboxProps && (
                <button
                  type="button"
                  onClick={() => setShowCodeSource((current) => !current)}
                  className="flex h-11 shrink-0 items-center gap-1 rounded-lg px-2 text-xs text-muted-foreground hover:bg-secondary hover:text-foreground"
                >
                  {showCodeSource ? <Play className="h-4 w-4" /> : <CodeIcon className="h-4 w-4" />}
                  <span className="hidden min-[360px]:inline">{showCodeSource ? 'Preview' : 'Code'}</span>
                </button>
              )}
              <button
                type="button"
                onClick={() => activeTabId && handleCloseTab(activeTabId)}
                className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg text-muted-foreground hover:bg-secondary hover:text-foreground"
                aria-label={`Close ${activeTab?.title || 'preview'} tab`}
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden bg-card pb-[env(safe-area-inset-bottom)]">
              {activeTab?.type === 'code' && activeTab.sandboxProps ? (
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
              ) : activeTab?.type === 'document' ? (
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
                    <Image
                      src={api.documents.downloadUrl(activeTab.docId!)}
                      alt={activeTab.title}
                      width={800}
                      height={600}
                      className="max-w-full max-h-full object-contain rounded-[12px] border border-border shadow-xs bg-card"
                      unoptimized
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
      </>
    )}

      {codePreview && (
        <div className="fixed inset-0 z-30 bg-black/30 animate-fade-in" onClick={() => setCodePreview(null)}>
          <CodePreviewPanel preview={codePreview} onClose={() => setCodePreview(null)} />
        </div>
      )}
    </div>
    </>
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
