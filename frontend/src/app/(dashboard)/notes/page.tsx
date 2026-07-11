'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { StickyNote, Plus, FileText, Sparkles } from 'lucide-react'

const notes = [
  { id: '1', title: 'AI Concepts Summary', preview: 'Key concepts from the AI introduction document...', tags: ['AI', 'Summary'], date: '2026-07-10' },
  { id: '2', title: 'ML Algorithms Flashcards', preview: 'Supervised vs unsupervised learning...', tags: ['ML', 'Flashcards'], date: '2026-07-09' },
  { id: '3', title: 'Neural Network Study Guide', preview: 'Architecture, activation functions, backpropagation...', tags: ['Neural', 'Study'], date: '2026-07-08' },
]

export default function NotesPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Notes</h1>
          <p className="text-muted-foreground mt-1">
            AI-generated notes, summaries, and flashcards
          </p>
        </div>
        <div className="flex gap-3">
          <Button variant="outline" className="gap-2">
            <Sparkles className="h-4 w-4" />
            Generate Summary
          </Button>
          <Button className="gap-2">
            <Plus className="h-4 w-4" />
            New Note
          </Button>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {notes.map((note) => (
          <Card key={note.id} className="group hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader>
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-lg bg-purple-500/10 text-purple-500">
                  <StickyNote className="h-5 w-5" />
                </div>
                <div className="flex-1">
                  <CardTitle className="text-lg">{note.title}</CardTitle>
                  <CardDescription className="mt-1">{note.preview}</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2 mb-3">
                {note.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">{tag}</Badge>
                ))}
              </div>
              <p className="text-xs text-muted-foreground">{note.date}</p>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
