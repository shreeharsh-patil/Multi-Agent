'use client'

import { useState, useEffect, useCallback, useRef } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
import { useSession } from 'next-auth/react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { preprocessLaTeX } from '@/lib/latex'
import * as Y from 'yjs'
import { getAccessToken } from '@/lib/auth-store'
import {
  StickyNote,
  Plus,
  Sparkles,
  Loader2,
  Download,
  FileText,
  File,
  FileDown,
  Trash2,
  Edit3,
  X,
  Save,
  Search,
} from 'lucide-react'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'
import { MermaidWorkspace } from '@/components/mermaid-workspace'

interface Note {
  id: string
  title: string
  preview?: string
  content?: string
  tags: string[]
  workspaceId?: string
  createdAt: string
  updatedAt: string
}

function arrayBufferToBase64(buffer: ArrayBuffer | Uint8Array): string {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  bytes.forEach((b) => {
    binary += String.fromCharCode(b);
  });
  return window.btoa(binary);
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary_string = window.atob(base64);
  const len = binary_string.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binary_string.charCodeAt(i);
  }
  return bytes.buffer;
}

function applyTextDiff(ytext: Y.Text, prev: string, curr: string) {
  if (prev === curr) return;
  
  let start = 0;
  while (start < prev.length && start < curr.length && prev[start] === curr[start]) {
    start++;
  }
  
  let endPrev = prev.length;
  let endCurr = curr.length;
  while (endPrev > start && endCurr > start && prev[endPrev - 1] === curr[endCurr - 1]) {
    endPrev--;
    endCurr--;
  }
  
  if (endPrev > start) {
    ytext.delete(start, endPrev - start);
  }
  if (endCurr > start) {
    ytext.insert(start, curr.slice(start, endCurr));
  }
}

const getWsUrl = (noteId: string, token?: string) => {
  const baseUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
  const wsScheme = baseUrl.startsWith('https') ? 'wss' : 'ws'
  const rawBase = baseUrl.replace(/^https?:\/\//, '')
  return `${wsScheme}://${rawBase}/api/notes/${noteId}/ws${token ? `?token=${token}` : ''}`
}

export default function NotesPage() {
  const { data: session } = useSession()
  const [notes, setNotes] = useState<Note[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedNote, setSelectedNote] = useState<Note | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [deepLinkHandled, setDeepLinkHandled] = useState(false)

  // Workspaces state
  const [workspaces, setWorkspaces] = useState<Array<{ id: string; name: string; color: string }>>([])
  const [selectedWorkspace, setSelectedWorkspace] = useState<string>('personal')

  // Form state
  const [formTitle, setFormTitle] = useState('')
  const [formContent, setFormContent] = useState('')
  const [formTags, setFormTags] = useState('')

  // Collaboration State
  const [syncStatus, setSyncStatus] = useState<'connecting' | 'connected' | 'offline'>('offline')
  const [collaborators, setCollaborators] = useState<Array<{ userId: string; name: string; color: string }>>([])
  
  const ydocRef = useRef<Y.Doc | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const isSyncingRef = useRef<boolean>(false)

  // Keep references to values that should not re-run connection effect when they change
  const formContentRef = useRef(formContent)
  useEffect(() => {
    formContentRef.current = formContent
  }, [formContent])

  const sessionRef = useRef(session)
  useEffect(() => {
    sessionRef.current = session
  }, [session])

  // Load workspaces
  useEffect(() => {
    api.workspaces.list()
      .then((res) => {
        if (res.success && res.data) {
          setWorkspaces(res.data.map(w => ({ id: w.id, name: w.name, color: w.color })))
        }
      })
      .catch(err => console.error("Error loading workspaces", err))
  }, [])

  const fetchNotes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.notes.list(selectedWorkspace === 'personal' ? undefined : selectedWorkspace)
      if (res.success && res.data) {
        setNotes(res.data)
      } else {
        setError(res.error || 'Failed to load notes')
      }
    } catch (e) {
      setError('Failed to load notes')
    } finally {
      setLoading(false)
    }
  }, [selectedWorkspace])

  useEffect(() => {
    fetchNotes()
  }, [fetchNotes])

  // Real-time synchronization connection
  useEffect(() => {
    if (!selectedNote || isCreating) {
      setSyncStatus('offline')
      setCollaborators([])
      return
    }

    const noteId = selectedNote.id
    const token = getAccessToken()
    
    setSyncStatus('connecting')
    
    const ydoc = new Y.Doc()
    ydocRef.current = ydoc
    const ytext = ydoc.getText('content')
    
    const wsUrl = getWsUrl(noteId, token || undefined)
    const ws = new WebSocket(wsUrl)
    wsRef.current = ws
    
    const activePeers: Record<string, { name: string; color: string; lastSeen: number }> = {}
    let presenceInterval: NodeJS.Timeout
    
    ws.onopen = () => {
      setSyncStatus('connected')
      
      // Periodically announce our presence
      presenceInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          ws.send(JSON.stringify({
            type: 'awareness',
            data: {
              userId: sessionRef.current?.user?.id || 'anonymous-' + Math.random().toString(36).substring(2, 7),
              name: sessionRef.current?.user?.name || 'Collaborator',
              color: '#' + Math.floor(Math.random() * 16777215).toString(16)
            }
          }))
        }
      }, 5000)

      // Initialize doc content if server has no updates
      setTimeout(() => {
        if (ytext.toString() === '' && formContentRef.current !== '') {
          isSyncingRef.current = true
          ytext.insert(0, formContentRef.current)
          isSyncingRef.current = false
          
          const update = Y.encodeStateAsUpdate(ydoc)
          const encoded = arrayBufferToBase64(update)
          ws.send(JSON.stringify({
            type: 'sync',
            data: encoded
          }))
        }
      }, 300)
    }
    
    ws.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data)
        if (payload.type === 'sync' && payload.data) {
          const updateBytes = base64ToArrayBuffer(payload.data)
          isSyncingRef.current = true
          Y.applyUpdate(ydoc, new Uint8Array(updateBytes), 'websocket')
          
          // Sync Yjs text updates directly to the text content state and restore cursor if active
          const newText = ytext.toString()
          const textarea = document.getElementById('note-editor-textarea') as HTMLTextAreaElement
          if (textarea && document.activeElement === textarea) {
            const start = textarea.selectionStart
            const end = textarea.selectionEnd
            const prevLen = textarea.value.length
            
            setFormContent(newText)
            
            setTimeout(() => {
              const diff = newText.length - prevLen
              textarea.setSelectionRange(start + (diff > 0 ? diff : 0), end + (diff > 0 ? diff : 0))
            }, 0)
          } else {
            setFormContent(newText)
          }
          isSyncingRef.current = false
        } else if (payload.type === 'awareness' && payload.data) {
          const peer = payload.data
          const currentUserId = sessionRef.current?.user?.id || 'anonymous'
          if (peer.userId !== currentUserId) {
            activePeers[peer.userId] = {
              name: peer.name,
              color: peer.color,
              lastSeen: Date.now()
            }
            
            const now = Date.now()
            const currentCollaborators = Object.entries(activePeers)
              .filter(([_, data]) => now - data.lastSeen < 12000)
              .map(([id, data]) => ({
                userId: id,
                name: data.name,
                color: data.color
              }))
            setCollaborators(currentCollaborators)
          }
        }
      } catch (err) {
        console.error("Failed to process WebSocket message:", err)
      }
    }
    
    ws.onclose = () => {
      setSyncStatus('offline')
      setCollaborators([])
    }
    
    ws.onerror = () => {
      setSyncStatus('offline')
    }
    
    const handleLocalUpdate = (update: Uint8Array, origin: any) => {
      if (origin === 'websocket') return
      
      if (ws.readyState === WebSocket.OPEN) {
        const encoded = arrayBufferToBase64(update)
        ws.send(JSON.stringify({
          type: 'sync',
          data: encoded
        }))
      }
    }
    
    ydoc.on('update', handleLocalUpdate)
    
    const handleYjsTextChange = () => {
      if (isSyncingRef.current) return
      setFormContent(ytext.toString())
    }
    
    ytext.observe(handleYjsTextChange)
    
    return () => {
      clearInterval(presenceInterval)
      ydoc.off('update', handleLocalUpdate)
      ytext.unobserve(handleYjsTextChange)
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close()
      }
      ydoc.destroy()
      ydocRef.current = null
      wsRef.current = null
    }
  }, [selectedNote, isCreating])

  useEffect(() => {
    if (deepLinkHandled || notes.length === 0) return
    const noteId = new URLSearchParams(window.location.search).get('note')
    if (!noteId) {
      setDeepLinkHandled(true)
      return
    }
    const note = notes.find((item) => item.id === noteId)
    if (!note) {
      setDeepLinkHandled(true)
      return
    }
    setDeepLinkHandled(true)
    setSelectedNote(note)
    if (!note.content) {
      api.notes.get(note.id).then((res) => {
        if (res.success && res.data) setSelectedNote(res.data)
      })
    }
  }, [deepLinkHandled, notes])

  const filteredNotes = notes.filter(
    (n) =>
      n.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (n.preview || '').toLowerCase().includes(searchQuery.toLowerCase()),
  )

  const handleCreate = () => {
    setSelectedNote(null)
    setIsCreating(true)
    setIsEditing(true)
    setFormTitle('')
    setFormContent('')
    setFormTags('')
  }

  const handleSelect = async (note: Note) => {
    if (isCreating) return
    setSelectedNote(note)
    setIsEditing(false)
    try {
      const res = await api.notes.get(note.id)
      if (res.success && res.data) {
        setSelectedNote(res.data)
        setFormContent(res.data.content || '')
        setFormTitle(res.data.title || '')
        setFormTags(res.data.tags.join(', '))
      } else {
        setError(res.error || 'Failed to load the complete note')
        setSelectedNote(null)
      }
    } catch {
      setError('Failed to load the complete note')
      setSelectedNote(null)
    }
  }

  const handleSave = async () => {
    if (!formTitle.trim()) return
    setSaving(true)
    setError(null)
    try {
      const tags = formTags
        .split(',')
        .map((t) => t.trim())
        .filter(Boolean)
      const data = { 
        title: formTitle, 
        content: formContent, 
        tags,
        workspace_id: selectedWorkspace === 'personal' ? undefined : selectedWorkspace
      }

      let res
      if (selectedNote && !isCreating) {
        res = await api.notes.update(selectedNote.id, data)
      } else {
        res = await api.notes.create(data)
      }

      if (!res.success) {
        setError(res.error || 'Failed to save note')
        return
      }

      await fetchNotes()
      setIsCreating(false)
      setIsEditing(false)
      setSelectedNote(null)
    } catch (e) {
      setError('Failed to save note')
    } finally {
      setSaving(false)
    }
  }

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this note?')) return
    try {
      const res = await api.notes.delete(id)
      if (!res.success) {
        setError(res.error || 'Failed to delete note')
        return
      }
      setNotes((prev) => prev.filter((n) => n.id !== id))
      if (selectedNote?.id === id) {
        setSelectedNote(null)
        setIsCreating(false)
        setIsEditing(false)
      }
    } catch (e) {
      setError('Failed to delete note')
    }
  }

  const [exportScope, setExportScope] = useState<string>('complete')

  const handleExport = async (format: 'pdf' | 'docx' | 'markdown') => {
    if (!selectedNote) return
    setExportingFormat(format)
    setError(null)
    try {
      const result = await api.study.exportDocument({
        title: selectedNote.title,
        content: selectedNote.content || formContent || '',
        format,
        scope: exportScope,
        subject: 'Academic Learning System',
      })
      if (!result.success || !result.blob) {
        setError(result.error || 'Export failed')
        return
      }
      const url = URL.createObjectURL(result.blob)
      const link = document.createElement('a')
      link.href = url
      link.download = result.fileName || `${selectedNote.title}.${format}`
      document.body.appendChild(link)
      link.click()
      link.remove()
      URL.revokeObjectURL(url)
    } catch {
      setError('Export failed')
    } finally {
      setExportingFormat(null)
    }
  }

  const [aiStyle, setAiStyle] = useState<'beginner' | 'exam' | 'detailed' | 'revision' | 'cheatsheet'>('detailed')

  const handleGenerateWithAI = async () => {
    setSaving(true)
    setError(null)
    try {
      const topicToUse = formTitle.trim() || 'Core Study Subject'
      const res = await api.study.notes({
        topic: topicToUse,
        style: aiStyle,
        workspace_id: selectedWorkspace === 'personal' ? undefined : selectedWorkspace,
        save_as_note: false,
      })
      if (res.success && res.data) {
        const aiOutput = res.data.content
        const combined = formContent ? formContent + '\n\n---\n\n' + aiOutput : aiOutput
        setFormContent(combined)
        if (!formTitle) {
          setFormTitle(res.data.title)
        }
        
        // Sync to Yjs if active
        if (ydocRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
          const ytext = ydocRef.current.getText('content')
          isSyncingRef.current = true
          applyTextDiff(ytext, ytext.toString(), combined)
          isSyncingRef.current = false
        }
      } else {
        setError(res.error || 'AI generation failed')
      }
    } catch (e) {
      setError('AI generation failed')
    } finally {
      setSaving(false)
    }
  }

  const handleContentChange = (val: string) => {
    setFormContent(val)
    
    // Apply changes to Yjs if active
    if (ydocRef.current && wsRef.current?.readyState === WebSocket.OPEN) {
      const ytext = ydocRef.current.getText('content')
      isSyncingRef.current = true
      applyTextDiff(ytext, ytext.toString(), val)
      isSyncingRef.current = false
    }
  }

  const closePanel = () => {
    setSelectedNote(null)
    setIsCreating(false)
    setIsEditing(false)
  }

  return (
    <div className="mx-auto w-full min-w-0 max-w-7xl space-y-6 bg-background animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div className="flex flex-col sm:flex-row sm:items-baseline gap-4">
          <h1 className="font-sans text-2xl font-normal tracking-[-0.03em] text-[#26251e] sm:text-3xl">Notes</h1>
          <div className="flex items-center gap-2">
            <span className="text-xs text-muted-foreground">Workspace:</span>
            <select
              value={selectedWorkspace}
              onChange={(e) => setSelectedWorkspace(e.target.value)}
              className="text-xs bg-background border border-border rounded-[8px] px-3 py-1.5 focus:ring-1 focus:ring-primary focus:outline-none cursor-pointer font-medium hover:bg-secondary/40 transition-colors"
            >
              <option value="personal">👤 Personal Notes</option>
              {workspaces.map((w) => (
                <option key={w.id} value={w.id}>
                  📁 {w.name}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="flex gap-3">
          <Button onClick={handleCreate} className="gap-2 shadow-sm">
            <Plus className="h-4 w-4" />
            New Note
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-[8px]">
          {error}
          <Button variant="link" size="sm" className="ml-2 text-red-700 underline" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
        {/* Notes List */}
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 h-4 w-4 text-[#6c6a64]" />
            <Input
              placeholder="Search notes..."
              className="pl-10"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>

          {loading ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-primary" />
                <p>Loading notes...</p>
              </CardContent>
            </Card>
          ) : filteredNotes.length === 0 ? (
            <Card>
              <CardContent className="py-12">
                <div className="text-center text-muted-foreground">
                  <StickyNote className="h-12 w-12 mx-auto mb-3 opacity-40 text-primary" />
                  <p className="text-lg font-sans font-normal tracking-[-0.02em] text-foreground">
                    {notes.length === 0 ? 'No notes yet' : 'No matching notes'}
                  </p>
                  <p className="text-sm mt-1">
                    {notes.length === 0
                      ? 'Create your first note to get started'
                      : 'Try a different search query'}
                  </p>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filteredNotes.map((note) => (
                <Card
                  key={note.id}
                  className={`group cursor-pointer transition-all duration-200 border-border shadow-xs flex flex-col justify-between ${
                    selectedNote?.id === note.id 
                      ? 'ring-1 ring-primary bg-secondary/80' 
                      : 'bg-card hover:bg-secondary/40'
                  }`}
                  onClick={() => handleSelect(note)}
                >
                  <CardHeader className="pb-3 p-5">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-base font-medium text-foreground">{note.title}</CardTitle>
                      <Button
                        variant="ghost"
                        size="icon"
                        className="ml-2 h-10 w-10 shrink-0 rounded-[8px] text-[#c64545] opacity-100 hover:bg-[#c64545]/10 md:opacity-0 md:group-hover:opacity-100 md:group-focus-within:opacity-100"
                        aria-label={`Delete ${note.title}`}
                        onClick={(e) => {
                          e.stopPropagation()
                          handleDelete(note.id)
                        }}
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                    {note.preview && (
                      <p className="text-xs text-muted-foreground leading-normal line-clamp-2 mt-1">
                        {note.preview}
                      </p>
                    )}
                  </CardHeader>
                  <CardContent className="pt-0 p-5">
                    <div className="flex items-center gap-2">
                      {note.tags.slice(0, 3).map((tag) => (
                        <Badge key={tag} variant="secondary" className="bg-secondary border border-border text-muted-foreground text-[10px] px-2 py-0.5 shadow-none">
                          {tag}
                        </Badge>
                      ))}
                      <span className="text-[10px] text-muted-foreground ml-auto font-sans">
                        {formatDate(note.updatedAt)}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>

        {/* Note Detail / Editor */}
        <div className="space-y-4">
          {(selectedNote || isCreating) && (
            <>
              {/* Export buttons - only when viewing */}
              {!isEditing && !isCreating && selectedNote && (
                <Card className="shadow-xs">
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3 text-muted-foreground">
                      <h3 className="font-semibold text-xs flex items-center gap-2 uppercase tracking-wider">
                        <Download className="h-4 w-4 text-primary" />
                        Publication Document Export
                      </h3>
                      <div className="flex items-center gap-2 mt-2 sm:mt-0">
                        <span className="text-[11px] text-muted-foreground">Scope:</span>
                        <select
                          value={exportScope}
                          onChange={(e) => setExportScope(e.target.value)}
                          className="text-xs bg-background border border-border rounded-[6px] px-2 py-1 focus:ring-1 focus:ring-primary focus:outline-none cursor-pointer font-medium"
                        >
                          <option value="complete">Entire Document</option>
                          <option value="notes">Only Notes</option>
                          <option value="exam">Exam Notes (High-Yield)</option>
                          <option value="revision">1-Page Revision</option>
                          <option value="questions">Question Bank & Q&A</option>
                          <option value="formulas">Formula Handbook</option>
                          <option value="diagrams">Diagram & Flowchart Book</option>
                          <option value="tables">Comparison Tables Only</option>
                          <option value="references">Bibliography & References</option>
                        </select>
                      </div>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2 h-9 text-xs"
                        onClick={() => handleExport('pdf')}
                        disabled={exportingFormat === 'pdf'}
                      >
                        {exportingFormat === 'pdf' ? (
                          <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        ) : (
                          <FileText className="h-4 w-4 text-primary" />
                        )}
                        PDF
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2 h-9 text-xs"
                        onClick={() => handleExport('docx')}
                        disabled={exportingFormat === 'docx'}
                      >
                        {exportingFormat === 'docx' ? (
                          <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        ) : (
                          <File className="h-4 w-4 text-primary" />
                        )}
                        DOCX
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2 h-9 text-xs"
                        onClick={() => handleExport('markdown')}
                        disabled={exportingFormat === 'markdown'}
                      >
                        {exportingFormat === 'markdown' ? (
                          <Loader2 className="h-4 w-4 animate-spin text-primary" />
                        ) : (
                          <FileDown className="h-4 w-4 text-primary" />
                        )}
                        MD
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Note Editor / Viewer */}
              <Card className="shadow-xs">
                <CardHeader className="pb-3 p-5">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center flex-wrap gap-2">
                      <CardTitle className="text-base font-sans font-normal tracking-[-0.02em] text-foreground">
                        {isCreating ? 'New Note' : isEditing ? 'Edit Note' : selectedNote?.title}
                      </CardTitle>
                      
                      {/* Presence Indicator */}
                      {syncStatus === 'connected' && (
                        <div className="flex items-center gap-1.5 ml-2">
                          <span className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse" title="Connected to collaboration room" />
                          <span className="text-[10px] text-muted-foreground mr-1 font-mono">Syncing</span>
                          {collaborators.map((c) => (
                            <Badge 
                              key={c.userId} 
                              variant="outline" 
                              className="text-[9px] px-1.5 py-0.5 rounded-[4px] font-sans"
                              style={{ borderColor: c.color, color: c.color }}
                            >
                              {c.name}
                            </Badge>
                          ))}
                        </div>
                      )}
                    </div>
                    
                    <div className="flex gap-2">
                      {!isCreating && !isEditing && (
                        <Button
                          variant="outline"
                          size="sm"
                          className="gap-2 h-9 text-xs rounded-[8px]"
                          onClick={() => {
                            setIsEditing(true)
                            if (selectedNote) {
                              setFormTitle(selectedNote.title)
                              setFormContent(selectedNote.content || '')
                              setFormTags(selectedNote.tags.join(', '))
                            }
                          }}
                        >
                          <Edit3 className="h-4 w-4" />
                          Edit
                        </Button>
                      )}
                      {(isCreating || isEditing) && (
                        <Button variant="ghost" size="icon" onClick={closePanel} className="h-8 w-8 rounded-[8px] hover:bg-secondary">
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="p-5 pt-0">
                  {isEditing ? (
                    <div className="space-y-4">
                      <Input
                        placeholder="Note title..."
                        value={formTitle}
                        onChange={(e) => setFormTitle(e.target.value)}
                      />
                      <Textarea
                        id="note-editor-textarea"
                        placeholder="Write your note content here. You can use Markdown formatting..."
                        className="min-h-[300px] font-mono text-xs text-foreground"
                        value={formContent}
                        onChange={(e) => handleContentChange(e.target.value)}
                      />
                      <Input
                        placeholder="Tags (comma-separated)..."
                        value={formTags}
                        onChange={(e) => setFormTags(e.target.value)}
                      />
                      <div className="flex flex-wrap items-center gap-2 pt-2">
                        <Button onClick={handleSave} className="gap-2 shadow-sm rounded-[8px]" disabled={saving || !formTitle.trim()}>
                          {saving ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Save className="h-4 w-4" />
                          )}
                          Save
                        </Button>
                        <div className="flex items-center gap-1.5 bg-secondary/50 p-1 rounded-[8px] border border-border/60">
                          <select
                            value={aiStyle}
                            onChange={(e) => setAiStyle(e.target.value as any)}
                            className="text-xs bg-background border border-border rounded-[6px] px-2 py-1 focus:ring-1 focus:ring-primary focus:outline-none cursor-pointer font-medium"
                          >
                            <option value="detailed">Exhaustive Notes</option>
                            <option value="beginner">Beginner Notes</option>
                            <option value="exam">Exam Notes (High-Yield)</option>
                            <option value="revision">1-Page Revision</option>
                            <option value="cheatsheet">Cheat Sheet</option>
                          </select>
                          <Button
                            variant="default"
                            size="sm"
                            className="gap-1.5 shadow-sm text-xs rounded-[6px]"
                            onClick={handleGenerateWithAI}
                            disabled={saving}
                          >
                            <Sparkles className="h-3.5 w-3.5" />
                            Generate AI Notes
                          </Button>
                        </div>
                      </div>
                    </div>
                  ) : selectedNote ? (
                    <div className="space-y-5">
                      <div className="flex flex-wrap gap-1 mb-4">
                        {selectedNote.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="bg-secondary border border-border text-muted-foreground text-[10px] px-2 py-0.5 shadow-none">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                      <ScrollArea className="h-[400px]">
                        <div className="prose prose-sm max-w-none pr-2 text-foreground prose-headings:font-semibold prose-headings:tracking-normal prose-strong:font-bold prose-em:italic">
                          {formContent ? <ReactMarkdown remarkPlugins={[remarkGfm, [remarkMath, { singleDollar: true }]]} rehypePlugins={[rehypeKatex]}>{preprocessLaTeX(formContent)}</ReactMarkdown> : 'No content'}
                        </div>
                      </ScrollArea>
                      <div className="flex items-center gap-2 mt-6 pt-4 border-t border-border text-[10px] text-muted-foreground font-sans">
                        <span>Created: {formatDate(selectedNote.createdAt)}</span>
                        <span>·</span>
                        <span>Updated: {formatDate(selectedNote.updatedAt)}</span>
                      </div>
                      <MermaidWorkspace content={selectedNote.content} title="Study note concept map" />
                    </div>
                  ) : null}
                </CardContent>
              </Card>
            </>
          )}

          {!selectedNote && !isCreating && (
            <Card>
              <CardContent className="py-16 text-center text-muted-foreground">
                <StickyNote className="h-12 w-12 mx-auto mb-3 opacity-40 text-primary" />
                <p className="text-lg font-sans font-normal tracking-[-0.02em] text-foreground">Select a note</p>
                <p className="text-sm mt-1">
                  Choose a note from the list or create a new one
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  )
}
