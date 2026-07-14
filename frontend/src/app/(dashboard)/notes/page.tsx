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
        }
      } catch (e) {
        // Keep what we have
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

      if (selectedNote && !isCreating) {
        await api.notes.update(selectedNote.id, data)
      } else {
        await api.notes.create(data)
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
      await api.notes.delete(id)
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
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Notes</h1>
          <p className="text-muted-foreground mt-1">
            {notes.length} note{notes.length !== 1 ? 's' : ''}
          </p>
        </div>
        <div className="flex gap-3">
          <Button onClick={handleCreate} className="gap-2">
            <Plus className="h-4 w-4" />
            New Note
          </Button>
        </div>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-lg">
          {error}
          <Button variant="link" size="sm" className="ml-2" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      <div className="grid gap-6 lg:grid-cols-[1fr_400px]">
        {/* Notes List */}
        <div className="space-y-4">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
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
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3" />
                <p>Loading notes...</p>
              </CardContent>
            </Card>
          ) : filteredNotes.length === 0 ? (
            <Card>
              <CardContent className="py-12">
                <div className="text-center text-muted-foreground">
                  <StickyNote className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p className="text-lg font-medium">
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
                  className={`group cursor-pointer transition-all hover:shadow-md ${
                    selectedNote?.id === note.id ? 'ring-2 ring-primary' : ''
                  }`}
                  onClick={() => handleSelect(note)}
                >
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-lg">{note.title}</CardTitle>
                      <div className="flex gap-1">
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 group-hover:opacity-100"
                          onClick={(e) => {
                            e.stopPropagation()
                            handleDelete(note.id)
                          }}
                        >
                          <Trash2 className="h-4 w-4 text-destructive" />
                        </Button>
                      </div>
                    </div>
                    {note.preview && (
                      <p className="text-sm text-muted-foreground line-clamp-2">
                        {note.preview}
                      </p>
                    )}
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="flex items-center gap-2">
                      {note.tags.slice(0, 3).map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-xs">
                          {tag}
                        </Badge>
                      ))}
                      <span className="text-xs text-muted-foreground ml-auto">
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
                <Card>
                  <CardContent className="p-4">
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="font-semibold text-sm flex items-center gap-2">
                        <Download className="h-4 w-4" />
                        Export
                      </h3>
                    </div>
                    <div className="grid grid-cols-3 gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2"
                        onClick={() => handleExport('pdf')}
                        disabled={exportingFormat === 'pdf'}
                      >
                        {exportingFormat === 'pdf' ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <FileText className="h-4 w-4" />
                        )}
                        PDF
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2"
                        onClick={() => handleExport('docx')}
                        disabled={exportingFormat === 'docx'}
                      >
                        {exportingFormat === 'docx' ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <File className="h-4 w-4" />
                        )}
                        DOCX
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        className="gap-2"
                        onClick={() => handleExport('markdown')}
                        disabled={exportingFormat === 'markdown'}
                      >
                        {exportingFormat === 'markdown' ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <FileDown className="h-4 w-4" />
                        )}
                        MD
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Note Editor / Viewer */}
              <Card>
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg">
                      {isCreating ? 'New Note' : isEditing ? 'Edit Note' : selectedNote?.title}
                    </CardTitle>
                    <div className="flex gap-2">
                      {!isCreating && !isEditing && (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            className="gap-2"
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
                        </>
                      )}
                      {(isCreating || isEditing) && (
                        <Button variant="ghost" size="icon" onClick={closePanel}>
                          <X className="h-4 w-4" />
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {isEditing ? (
                    <div className="space-y-4">
                      <Input
                        placeholder="Note title..."
                        value={formTitle}
                        onChange={(e) => setFormTitle(e.target.value)}
                      />
                      <Textarea
                        placeholder="Write your note content here. You can use Markdown formatting..."
                        className="min-h-[300px] font-mono text-sm"
                        value={formContent}
                        onChange={(e) => setFormContent(e.target.value)}
                      />
                      <Input
                        placeholder="Tags (comma-separated)..."
                        value={formTags}
                        onChange={(e) => setFormTags(e.target.value)}
                      />
                      <div className="flex gap-2">
                        <Button onClick={handleSave} className="gap-2" disabled={saving || !formTitle.trim()}>
                          {saving ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Save className="h-4 w-4" />
                          )}
                          Save
                        </Button>
                        <Button
                          variant="outline"
                          className="gap-2"
                          onClick={handleGenerateWithAI}
                          disabled={saving}
                        >
                          <Sparkles className="h-4 w-4" />
                          Generate with AI
                        </Button>
                      </div>
                    </div>
                  ) : selectedNote ? (
                    <div>
                      <div className="flex flex-wrap gap-1 mb-4">
                        {selectedNote.tags.map((tag) => (
                          <Badge key={tag} variant="secondary" className="text-xs">
                            {tag}
                          </Badge>
                        ))}
                      </div>
                      <ScrollArea className="h-[400px]">
                        <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap text-sm">
                          {selectedNote.content || selectedNote.preview || 'No content'}
                        </div>
                      </ScrollArea>
                      <div className="flex items-center gap-2 mt-4 text-xs text-muted-foreground">
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
              <CardContent className="py-12 text-center text-muted-foreground">
                <StickyNote className="h-12 w-12 mx-auto mb-3 opacity-50" />
                <p className="text-lg font-medium">Select a note</p>
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
