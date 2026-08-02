// @ts-nocheck
/* eslint-disable */
'use client'

import { useState, useRef, useEffect, useCallback, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { useSession } from 'next-auth/react'
import Image from 'next/image'
import { Button } from '@/components/ui/button'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import { api } from '@/lib/api'
import { Send, Bot, User, Paperclip, FileText, ImageIcon, X, Loader2, Upload, Mic, Volume2, Square, Sparkles, CheckCircle2, Share2, ChevronDown, Copy, RefreshCw, Pencil } from 'lucide-react'
import type { AgentId, DocumentInfo } from '@shared/types'
import { CodePreviewButton, CodeSandbox, type CodeSandboxProps } from '@/components/code-sandbox'
import { CodePreviewPanel } from '@/components/code-preview-panel'
import { FileCode, Globe, Play, Code as CodeIcon, GraduationCap } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import rehypeRaw from 'rehype-raw'
import { preprocessLaTeX } from '@/lib/latex'
import { ImagePreviewCard } from '@/components/image-preview-card'

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
  { id: 'auto', name: 'Auto (Orchestrator)' },
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
  driveFileId?: string
  driveWebViewLink?: string
}

const isImageExt = (name: string) => /\.(png|jpg|jpeg|webp|gif|svg|bmp)$/i.test(name)
const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

const resolveApiUrl = (url?: string) => url?.startsWith('/api/') ? `${backendUrl}${url}` : url

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
  const { data: session } = useSession()
  const googleAccessToken = (session as any)?.accessToken as string | undefined
  const googleRefreshToken = (session as any)?.refreshToken as string | undefined
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
  const toggleTeamMode = useCallback(() => {
    setTeamMode((current) => !current)
  }, [])
  const [teamAgents, setTeamAgents] = useState<string[]>(['research', 'coding', 'planner'])

  // Hybrid layout UI states
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
    const convParam = searchParams?.get('id') || searchParams?.get('c') || searchParams?.get('conversation_id') || searchParams?.get('conversation')
    if (convParam) {
      setConversationId(convParam)
    }
  }, [searchParams, customAgents])
  const [, setWorkspaces] = useState<Array<{ id: string; name: string; color: string; documentCount: number }>>([])
  const [selectedWorkspace, setSelectedWorkspace] = useState('all')
  const [voiceMode, setVoiceMode] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [speakingId, setSpeakingId] = useState<string | null>(null)
  const [shareUrl, setShareUrl] = useState<string | null>(null)
  const [attachments, setAttachments] = useState<Attachment[]>([])
  const [sending, setSending] = useState(false)
  const [copiedId, setCopiedId] = useState<string | null>(null)
  const [editingId, setEditingId] = useState<string | null>(null)
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
      }, uploadWorkspace, googleAccessToken)
      if (res.success && res.data) {
        final = { ...att, status: 'done', documentId: res.data.id, imageUrl: res.data.imageUrl, progress: 100 }
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
  }, [selectedWorkspace, googleAccessToken])

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
  const [, setConversations] = useState<Array<{
    id: string
    title: string
    agentId?: string
    messageCount: number
    lastMessage: string
    updatedAt: string
  }>>([])
  const [, setLoadingConversations] = useState(true)
  const [chatTitle, setChatTitle] = useState('')
  const [, setLoadingHistory] = useState(false)

  // Sync conversationId to the URL so refresh/back-nav restores the chat
  useEffect(() => {
    if (typeof window === 'undefined') return
    if (conversationId) {
      const url = new URL(window.location.href)
      url.searchParams.set('id', conversationId)
      window.history.replaceState(null, '', url.toString())
    } else {
      window.history.replaceState(null, '', '/chat')
    }
  }, [conversationId])

  // Fetch conversation messages when conversationId is set/changed,
  // but skip if we just created this id locally (already have the messages)
  useEffect(() => {
    if (!conversationId) return
    // Don't re-fetch a conversation we just created — messages are already in state
    if (locallyCreatedIds.current.has(conversationId)) return
    let isCancelled = false
    setLoadingHistory(true)
    api.chat.getConversation(conversationId)
      .then((res) => {
        if (isCancelled) return
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
              }))
            )
          }
        }
      })
      .catch((err) => console.error('Failed to load chat history:', err))
      .finally(() => {
        if (!isCancelled) setLoadingHistory(false)
      })

    return () => { isCancelled = true }
  }, [conversationId])

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

  const shareTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => () => {
    if (shareTimerRef.current) clearTimeout(shareTimerRef.current)
  }, [])

  const shareConversation = useCallback(async () => {
    if (!conversationId) {
      setShareUrl('error')
      return
    }
    // Clear any existing dismiss timer
    if (shareTimerRef.current) clearTimeout(shareTimerRef.current)
    try {
      const res = await api.chat.createShare(conversationId)
      if (res.success && res.data) {
        const url = `${window.location.origin}/shared/chat/${res.data.token}`
        setShareUrl(url)
        await navigator.clipboard?.writeText(url)
        // Auto-dismiss after 8 seconds
        shareTimerRef.current = setTimeout(() => setShareUrl(null), 8000)
      } else {
        setShareUrl('error')
        console.error('Share failed:', res.error || 'Unknown error')
      }
    } catch (e) {
      setShareUrl('error')
      console.error('Share failed:', e)
    }
  }, [conversationId])

  // Export the current conversation as a downloadable Markdown file.
  const exportConversation = useCallback(() => {
    if (messages.length === 0) return
    const title = chatTitle || 'Conversation'
    const lines = [`# ${title}`, '']
    for (const m of messages) {
      if (!m.content) continue
      lines.push(m.role === 'user' ? '## You' : '## Assistant')
      lines.push('', m.content, '')
    }
    const blob = new Blob([lines.join('\n')], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${title.replace(/[^a-z0-9]+/gi, '-').replace(/^-+|-+$/g, '').toLowerCase() || 'conversation'}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }, [messages, chatTitle])

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
    })
    api.agents.list().then((res) => {
      if (res.success && res.data) {
        setCustomAgents(res.data.filter((agent) => agent.custom).map((agent) => ({ id: agent.id, name: agent.name })))
      } else {
        console.warn('Failed to load agents:', res.error)
      }
    })
  }, [fetchConversations])

  // Ref to prevent stale resets when searchParams changes during navigation
  const loadedIdRef = useRef<string | null>(null)
  const isLoadingRef = useRef(false)

  // Load a conversation's messages
  const loadConversation = useCallback(async (id: string) => {
    if (isLoadingRef.current) return
    isLoadingRef.current = true
    loadedIdRef.current = id
    try {
      const res = await api.chat.getConversation(id)
      // Only apply if we're still on the same conversation (not superseded by newer navigation)
      if (loadedIdRef.current !== id) return
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
      if (loadedIdRef.current === id) {
        console.error('Failed to load conversation:', e)
      }
    } finally {
      if (loadedIdRef.current === id) {
        isLoadingRef.current = false
      }
    }
  }, [])

  // Start a new conversation
  const startNewConversation = useCallback(() => {
    abortControllerRef.current?.abort()
    abortControllerRef.current = null
    sendingRef.current = false
    setSending(false)
    loadedIdRef.current = null
    isLoadingRef.current = false
    setConversationId(undefined)
    setChatTitle('')
    setMessages([])
    setAttachments([])
    setShareUrl(null)
    if (typeof window !== 'undefined') window.history.replaceState(null, '', '/chat')
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

  // Load conversation from search param
  const idParam = searchParams?.get('id')
  useEffect(() => {
    if (idParam) {
      loadConversation(idParam)
    } else {
      startNewConversation()
    }
  }, [idParam, loadConversation, startNewConversation])

  const handleSend = useCallback(async (overrideText?: string) => {
    // Synchronous ref guard prevents double-submits even when state hasn't updated yet
    if (sendingRef.current) return
    const isRegenerate = typeof overrideText === 'string'
    if (!isRegenerate && ((!input.trim() && attachments.length === 0) || (teamMode && teamAgents.length === 0))) return

    const text = isRegenerate ? overrideText!.trim() : input.trim()
    const attachmentCount = attachments.length
    const currentConvId = conversationId
    const currentAgent = teamMode || selectedAgent === 'auto' ? undefined : selectedAgent
    const currentWorkspace = selectedWorkspace === 'all' ? undefined : selectedWorkspace === 'unfiled' ? '__unfiled__' : selectedWorkspace

    sendingRef.current = true
    setSending(true)

    // Attachments already began uploading on select. Await any in-flight
    // upload; only kick off a fresh upload for ones that never started
    // (e.g. added programmatically) or previously errored.
    // On regenerate there are no new attachments to process.
    const uploadedAttachments: Array<{ name: string; size: number; documentId?: string }> = []
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
        })
      }
      attachments.forEach((att) => { if (att.previewUrl) URL.revokeObjectURL(att.previewUrl) })
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
    }

    // Add placeholder assistant message (will be updated incrementally via SSE)
    const assistantId = crypto.randomUUID()
    setMessages((prev) => [...prev, { id: assistantId, role: 'assistant', content: '' }])

    // Fresh AbortController for this request so Stop can cancel it.
    const abortController = new AbortController()
    abortControllerRef.current = abortController

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
      }, googleAccessToken, abortController.signal, googleRefreshToken)

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

      // Accumulate content in a ref and flush to React state at ~60 fps
      // to avoid hundreds of re-renders per second during streaming.
      const pendingContentRef = { current: '' }
      let frameId: number | null = null
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
        const { done, value } = await reader.read()
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

            if (currentEvent === 'chunk' && data.text) {
                accumulatedContent += data.text
                // Schedule a single visual update per frame
                if (frameId === null) {
                  frameId = requestAnimationFrame(flushState)
                }
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
                // Mark this id as locally created so we don't refetch it
                locallyCreatedIds.current.add(data.conversation_id)
                if (frameId !== null) cancelAnimationFrame(frameId)
                accumulatedContent = data.output || accumulatedContent
                setConversationId(data.conversation_id)
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, content: data.output || accumulatedContent }
                      : msg,
                  ),
                )
            } else if (currentEvent === 'error' && data.error) {
                if (frameId !== null) cancelAnimationFrame(frameId)
                setMessages((prev) =>
                  prev.map((msg) =>
                    msg.id === assistantId
                      ? { ...msg, content: `Error: ${data.error}` }
                      : msg,
                  ),
                )
            }
          } catch {
            // Ignore a malformed event without interrupting the stream.
          }
        }
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
        setConversationId(newConvId)
      }
    } catch (err) {
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
          }, googleAccessToken, googleRefreshToken)
          if (res.success && res.data) {
            // Mark as locally created to prevent refetch overriding messages
            locallyCreatedIds.current.add(res.data.conversation_id)
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
      sendingRef.current = false
      setSending(false)
      abortControllerRef.current = null
      // Refresh side-panel document list and sidebar conversation history on send completion
      window.dispatchEvent(new Event('refresh-documents-list'))
      window.dispatchEvent(new Event('refresh-conversations-list'))
    }
  }, [input, attachments, uploadAttachment, conversationId, selectedAgent, teamMode, teamAgents, selectedWorkspace, googleAccessToken, googleRefreshToken])

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
      setTimeout(() => handleSend(lastUser.content), 0)
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
      setTimeout(() => handleSend(newText), 0)
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
      className={`flex h-full w-full gap-0 overflow-hidden bg-background animate-fade-in relative ${isResizing ? 'select-none cursor-col-resize' : ''}`}
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
        */}

        {shareUrl && shareUrl !== 'error' && (
          <div className="mx-6 mt-4 flex items-center gap-2 rounded-[8px] border border-[#1f8a65]/20 bg-[#1f8a65]/5 px-3 py-2 text-xs">
            <Share2 className="h-3.5 w-3.5 text-[#1f8a65]" />
            <span className="font-medium text-[#1f8a65]">Conversation link copied:</span>
            <Input readOnly value={shareUrl} className="ml-auto h-7 max-w-sm text-[10px] bg-card border-border text-[#26251e]" />
          </div>
        )}
        {shareUrl === 'error' && (
          <div className="mx-6 mt-4 flex items-center gap-2 rounded-[8px] border border-red-200 bg-red-50 px-3 py-2 text-xs">
            <X className="h-3.5 w-3.5 text-red-500" />
            <span className="font-medium text-red-600">Failed to create share link.</span>
            <Button
              variant="ghost"
              size="sm"
              className="ml-auto h-6 text-[10px] text-red-600 hover:text-red-700 hover:bg-red-100"
              onClick={() => setShareUrl(null)}
            >
              Dismiss
            </Button>
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
            <div className="absolute inset-0 flex flex-col items-center justify-center p-4 sm:p-6 text-center select-none bg-background overflow-y-auto scrollbar-thin">
              <div className="max-w-2xl w-full flex flex-col items-center justify-center space-y-6 sm:space-y-8 py-4">
                <div className="space-y-3">
                  <div className="flex justify-center">
                    <div className="h-12 w-12 rounded-xl border border-border/80 bg-card flex items-center justify-center shadow-xs transition-transform hover:scale-105 duration-300">
                      <Image src="/logo.png" alt="Agents Logo" width={26} height={26} className="h-6.5 w-6.5 object-contain" />
                    </div>
                  </div>
                  <h1 className="text-2xl sm:text-3xl font-semibold tracking-tight text-[#26251e] font-sans">
                    How can I help you today?
                  </h1>
                  <p className="text-xs sm:text-sm text-muted-foreground/80 max-w-md mx-auto leading-relaxed font-sans">
                    Ask anything, analyze documents, or delegate tasks to specialized AI agents in this collaborative workspace.
                  </p>
                </div>

                {/* AI Study Learning Modes Bar */}
                <div className="w-full px-2 space-y-2">
                  <div className="flex items-center justify-center gap-1.5 text-xs text-muted-foreground font-medium mb-1">
                    <GraduationCap className="h-4 w-4 text-primary" />
                    <span>AI Study Learning Modes:</span>
                  </div>
                  <div className="flex flex-wrap items-center justify-center gap-2">
                    {[
                      { name: 'Teach Me', prefix: 'Teach me step-by-step with examples and diagrams: ' },
                      { name: 'ELI10', prefix: 'Explain like I am 10 years old with simple analogies: ' },
                      { name: 'Professor Mode', prefix: 'Provide a rigorous academic explanation with KaTeX formulas, proofs, and definitions: ' },
                      { name: 'Research Mode', prefix: 'Provide a research-grade analysis with citations, trade-offs, and open problems: ' },
                      { name: 'Exam Mode', prefix: 'Format as high-scoring exam points (2/5/10 mark pattern) with formulas and common traps: ' },
                      { name: 'Revision Mode', prefix: 'Create a 1-page rapid revision guide with bullet points and mnemonics: ' },
                      { name: 'Interview Mode', prefix: 'Format as technical interview questions with complexity analysis and code dry-runs: ' },
                    ].map((mode) => (
                      <button
                        key={mode.name}
                        onClick={() => {
                          setInput(mode.prefix)
                        }}
                        className="text-xs bg-secondary/80 hover:bg-primary/10 hover:border-primary/40 border border-border text-foreground px-3 py-1.5 rounded-full transition-all duration-200 cursor-pointer font-medium shadow-2xs hover:scale-[1.02] active:scale-[0.98]"
                      >
                        {mode.name}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Central quick suggestion buttons as premium cards */}
                <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3 w-full px-2">
                  {[
                    { text: 'Research a topic', desc: 'Perform deep search across the web', icon: Globe },
                    { text: 'Analyze a file', desc: 'Upload documents or spreadsheets', icon: FileText },
                    { text: 'Generate code', desc: 'Write, debug or refactor code', icon: CodeIcon },
                    { text: 'Create an image', desc: 'Generate high-fidelity visual assets', icon: ImageIcon },
                    { text: 'Write something', desc: 'Draft articles, copy, or summaries', icon: FileCode },
                    { text: 'Plan & organize', desc: 'Create study plans and schedule tasks', icon: Sparkles },
                  ].map((card) => (
                    <button
                      key={card.text}
                      onClick={() => handleSuggestionClick(card.text)}
                      className="group flex flex-col items-start p-4 rounded-xl border border-border/70 bg-card text-left transition-all duration-200 hover:-translate-y-0.5 hover:shadow-sm hover:border-primary/40 active:translate-y-0 shadow-2xs cursor-pointer"
                    >
                      <div className="h-8 w-8 rounded-lg border border-border/60 bg-secondary flex items-center justify-center mb-2.5 group-hover:border-primary/30 group-hover:bg-primary/5 transition-colors">
                        <card.icon className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors stroke-[1.8]" />
                      </div>
                      <span className="text-xs font-semibold text-[#26251e] mb-1 font-sans group-hover:text-primary transition-colors">{card.text}</span>
                      <span className="text-[11px] text-muted-foreground/80 leading-relaxed font-sans line-clamp-2">{card.desc}</span>
                    </button>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <ScrollArea ref={scrollRef} className="h-full px-3 sm:px-6 py-3 sm:py-6">
              <div className="space-y-6 max-w-3xl mx-auto">
                {messages.map((msg, idx) => (
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

                      <div className="group relative">
                        {msg.role === 'user' && editingId === msg.id ? (
                          <div className="w-full min-w-[280px] rounded-[12px] border border-border bg-card p-2 shadow-xs">
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
                              className="w-full resize-none bg-transparent text-sm text-[#26251e] focus:outline-none px-1 py-0.5"
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
                          className={`rounded-[12px] px-4 py-2.5 text-sm leading-relaxed ${
                            msg.role === 'user'
                              ? 'bg-card text-[#26251e] border border-border shadow-xs font-sans'
                              : 'text-[#26251e] bg-transparent font-sans'
                          }`}
                        >
                          {msg.role === 'assistant' && !msg.content && sending ? (
                            <span className="inline-flex items-center gap-1 h-5" role="status" aria-label="Typing">
                              <span className="typing-dot w-1.5 h-1.5 rounded-full bg-muted-foreground/60" style={{ animationDelay: '0ms' }} />
                              <span className="typing-dot w-1.5 h-1.5 rounded-full bg-muted-foreground/60" style={{ animationDelay: '200ms' }} />
                              <span className="typing-dot w-1.5 h-1.5 rounded-full bg-muted-foreground/60" style={{ animationDelay: '400ms' }} />
                            </span>
                          ) : (
                            <div className="text-xs sm:text-sm leading-relaxed [&_*]:break-words">
                              <ReactMarkdown
                                remarkPlugins={[remarkGfm, [remarkMath, { singleDollar: true }]]}
                                rehypePlugins={[rehypeKatex, rehypeRaw]}
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
                                          className="text-primary underline underline-offset-2 hover:text-primary/80 cursor-pointer inline-flex items-center gap-1 font-medium"
                                        >
                                          {children}
                                        </button>
                                      )
                                    }
                                    return (
                                      <a href={resolved} target="_blank" rel="noopener noreferrer" className="text-primary underline underline-offset-2 hover:text-primary/80">{children}</a>
                                    )
                                  },
                                  img: ({ src, alt }) => typeof src === 'string' ? (
                                    <ImagePreviewCard src={resolveApiUrl(src) || src} alt={alt || 'Generated image'} />
                                  ) : null,
                                  code: ({ className, children, ...props }) => {
                                    const isInline = !className
                                    return isInline ? (
                                      <code className="bg-muted/60 px-1.5 py-0.5 rounded-md text-xs font-mono text-foreground/80" {...props}>{children}</code>
                                    ) : (
                                      <pre className="overflow-x-auto rounded-xl bg-muted/40 p-4 mb-3 mt-1 border border-border/40">
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
                                    <div className="table-responsive my-3 border border-border rounded-lg overflow-x-auto max-w-full">
                                      <table className="w-full text-left border-collapse text-xs sm:text-sm">{children}</table>
                                    </div>
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
                                {preprocessLaTeX(msg.content)}
                              </ReactMarkdown>
                            </div>
                          )}
                        </div>
                        )}
                        {msg.role === 'user' && msg.content && editingId !== msg.id && !sending && (
                          <div className="flex items-center justify-end gap-3 mt-1.5 px-1 opacity-0 group-hover:opacity-100 transition-opacity select-none">
                            <button
                              type="button"
                              onClick={() => startEdit(msg.id, msg.content)}
                              className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                            >
                              <Pencil className="h-3 w-3" />
                              <span>Edit</span>
                            </button>
                          </div>
                        )}
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
                            <button
                              type="button"
                              onClick={() => {
                                navigator.clipboard?.writeText(msg.content)
                                setCopiedId(msg.id)
                                setTimeout(() => setCopiedId((c) => (c === msg.id ? null : c)), 1500)
                              }}
                              className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
                            >
                              {copiedId === msg.id ? <CheckCircle2 className="h-3 w-3 text-emerald-600" /> : <Copy className="h-3 w-3" />}
                              <span>{copiedId === msg.id ? 'Copied' : 'Copy'}</span>
                            </button>
                            {idx === messages.length - 1 && !sending && (
                              <button
                                type="button"
                                onClick={handleRegenerate}
                                className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors"
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
          {showScrollToBottom && messages.length > 0 && (
            <button
              type="button"
              onClick={() => scrollToBottom('smooth')}
              title="Scroll to bottom"
              className="absolute bottom-4 left-1/2 -translate-x-1/2 z-10 h-9 w-9 rounded-full bg-card border border-border shadow-md flex items-center justify-center text-muted-foreground hover:text-foreground hover:bg-secondary/60 transition-colors"
            >
              <ChevronDown className="h-4 w-4" />
            </button>
          )}
        </div>

        {/* Anchored bottom input block */}
        <div className="px-3 sm:px-6 py-3 sm:py-4 border-t border-border bg-background shrink-0">
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
                  onClick={sending ? handleStop : () => handleSend()}
                  disabled={!sending && ((!input.trim() && attachments.length === 0) || (teamMode && teamAgents.length === 0))}
                  className="rounded-[10px] h-9 w-9 hover:scale-[1.02] transition-all bg-primary hover:bg-primary/90 text-primary-foreground shadow-xs shrink-0 flex items-center justify-center cursor-pointer"
                  size="icon"
                  title={sending ? 'Stop' : 'Send'}
                >
                  {sending ? <Square className="h-3.5 w-3.5 fill-current" /> : <Send className="h-4 w-4 stroke-[1.8]" />}
                </Button>
              </div>
            </div>
            <div className="flex items-center justify-between px-1 text-[10px] text-muted-foreground select-none">
              <span>
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
            onMouseDown={handleMouseDown}
            className="hidden sm:block w-1 hover:w-1.5 active:w-1.5 h-full cursor-col-resize select-none shrink-0 transition-all duration-150 z-30 relative"
            style={{ display: isResizing ? undefined : undefined }}
          >
            <div className="absolute inset-y-0 left-1/2 -translate-x-1/2 w-[1px] bg-border" />
          </div>

          {/* Desktop right panel (flex child, percentage width) */}
          <aside
            className="hidden sm:flex flex-col h-full bg-secondary border-l border-border overflow-hidden min-w-0"
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

          {/* Mobile right panel (fixed overlay) */}
          <div className="sm:hidden fixed inset-0 z-40 flex flex-col bg-secondary">
            <div className="flex items-center justify-between px-3 py-2 border-b border-border bg-card shrink-0">
              <span className="text-xs font-semibold truncate">{activeTab?.title || 'Document'}</span>
              <button
                type="button"
                onClick={() => handleCloseTab(activeTabId!)}
                className="h-8 w-8 flex items-center justify-center rounded-lg text-muted-foreground hover:text-foreground hover:bg-secondary cursor-pointer"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
            <div className="flex-1 flex flex-col overflow-hidden min-h-0 bg-card">
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
