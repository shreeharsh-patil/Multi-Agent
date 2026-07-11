'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StickyNote, Plus, Sparkles } from 'lucide-react'

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

      <Card>
        <CardContent className="py-12">
          <div className="text-center text-muted-foreground">
            <StickyNote className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-lg font-medium">No notes yet</p>
            <p className="text-sm mt-1">Ask the Notes Agent to create notes, summaries, or flashcards</p>
            <Button variant="outline" className="mt-4 gap-2">
              <Sparkles className="h-4 w-4" />
              Generate from chat
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
