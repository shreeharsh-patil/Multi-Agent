'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Textarea } from '@/components/ui/textarea'
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

interface Note {
  id: string
  title: string
  preview?: string
  content?: string
  tags: string[]
  createdAt: string
  updatedAt: string
}

export default function NotesPage() {
  const [notes, setNotes] = useState<Note[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [selectedNote, setSelectedNote] = useState<Note | null>(null)
  const [isCreating, setIsCreating] = useState(false)
  const [isEditing, setIsEditing] = useState(false)
  const [saving, setSaving] = useState(false)
  const [exportingFormat, setExportingFormat] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  // Form state
  const [formTitle, setFormTitle] = useState('')
  const [formContent, setFormContent] = useState('')
  const [formTags, setFormTags] = useState('')

  const fetchNotes = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await api.notes.list()
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
  }, [])

  useEffect(() => {
    fetchNotes()
  }, [fetchNotes])

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
    // Fetch full content if we only have preview
    if (!note.content) {
      try {
        const res = await api.notes.get(note.id)
        if (res.success && res.data) {
          setSelectedNote(res.data)
        } else {
          console.warn('Failed to load full note content:', res.error)
        }
      } catch (e) {
        console.error('Failed to load note content:', e)
      }
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
      const data = { title: formTitle, content: formContent, tags }

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

  const handleExport = async (format: 'pdf' | 'docx' | 'markdown') => {
    if (!selectedNote) return
    setExportingFormat(format)
    try {
      const url = api.notes.exportUrl(selectedNote.id, format)
      // Open in new tab to download
      window.open(url, '_blank')
    } catch (e) {
      setError('Export failed')
    } finally {
      setExportingFormat(null)
    }
  }

  const handleGenerateWithAI = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await api.chat.send({
        message: `Create structured notes on the following topic. Include sections, bullet points, key concepts, definitions, and examples: ${formTitle || 'General notes'}`,
      })
      if (res.success && res.data) {
        setFormContent((prev) => prev + '\n\n---\n\n' + res.data!.output)
      } else {
        setError(res.error || 'AI generation failed')
      }
    } catch (e) {
      setError('AI generation failed')
    } finally {
      setSaving(false)
    }
  }

  const closePanel = () => {
    setSelectedNote(null)
    setIsCreating(false)
    setIsEditing(false)
  }

  return (
    <div className="space-y-6 animate-fade-in bg-background">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-[#26251e]">Notes</h1>
          <p className="text-sm text-muted-foreground mt-1">
            {notes.length} note{notes.length !== 1 ? 's' : ''}
          </p>
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
                        className="h-8 w-8 opacity-0 group-hover:opacity-100 rounded-[8px] text-[#c64545] hover:bg-[#c64545]/10 shrink-0 ml-2"
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
                        Export Note
                      </h3>
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
                    <CardTitle className="text-base font-sans font-normal tracking-[-0.02em] text-foreground">
                      {isCreating ? 'New Note' : isEditing ? 'Edit Note' : selectedNote?.title}
                    </CardTitle>
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
                        placeholder="Write your note content here. You can use Markdown formatting..."
                        className="min-h-[300px] font-mono text-xs text-foreground"
                        value={formContent}
                        onChange={(e) => setFormContent(e.target.value)}
                      />
                      <Input
                        placeholder="Tags (comma-separated)..."
                        value={formTags}
                        onChange={(e) => setFormTags(e.target.value)}
                      />
                      <div className="flex gap-2 pt-2">
                        <Button onClick={handleSave} className="gap-2 shadow-sm" disabled={saving || !formTitle.trim()}>
                          {saving ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Save className="h-4 w-4" />
                          )}
                          Save
                        </Button>
                        <Button
                          variant="outline"
                          className="gap-2 shadow-sm"
                          onClick={handleGenerateWithAI}
                          disabled={saving}
                        >
                          <Sparkles className="h-4 w-4 text-primary" />
                          Generate with AI
                        </Button>
                      </div>
                    </div>
                  ) : selectedNote ? (
                    <div>
                      <div className="flex flex-wrap gap-1 mb-4">
                        {selectedNote.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="bg-secondary border border-border text-muted-foreground text-[10px] px-2 py-0.5 shadow-none">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                      <ScrollArea className="h-[400px]">
                        <div className="max-w-none whitespace-pre-wrap text-sm text-foreground leading-relaxed font-sans pr-2">
                          {selectedNote.content || selectedNote.preview || 'No content'}
                        </div>
                      </ScrollArea>
                      <div className="flex items-center gap-2 mt-6 pt-4 border-t border-border text-[10px] text-muted-foreground font-sans">
                        <span>Created: {formatDate(selectedNote.createdAt)}</span>
                        <span>·</span>
                        <span>Updated: {formatDate(selectedNote.updatedAt)}</span>
                      </div>
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
