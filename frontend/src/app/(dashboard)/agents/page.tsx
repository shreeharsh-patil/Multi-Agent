'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Bot, Settings, Play, Brain, BookOpen, Search, FileCode, StickyNote, GraduationCap, Calendar, Puzzle } from 'lucide-react'

const agents = [
  { id: 'knowledge', name: 'Knowledge Agent', description: 'RAG, document search, citations, knowledge graph, and summaries', icon: BookOpen, color: 'text-blue-500', tags: ['RAG', 'Search', 'Citations'] },
  { id: 'drive', name: 'Drive Agent', description: 'Google Drive uploads, downloads, sync, and folder management', icon: Brain, color: 'text-green-500', tags: ['Drive', 'Files', 'Sync'] },
  { id: 'notes', name: 'Notes Agent', description: 'Structured notes, summaries, flashcards, and revision notes', icon: StickyNote, color: 'text-purple-500', tags: ['Notes', 'Flashcards'] },
  { id: 'quiz', name: 'Quiz Agent', description: 'MCQs, exams, and practice questions generation', icon: GraduationCap, color: 'text-amber-500', tags: ['Quiz', 'MCQ', 'Exam'] },
  { id: 'planner', name: 'Planner Agent', description: 'Study planning, task management, schedules, and deadlines', icon: Calendar, color: 'text-pink-500', tags: ['Planning', 'Schedule'] },
  { id: 'research', name: 'Research Agent', description: 'Internet search, source comparison, report generation', icon: Search, color: 'text-indigo-500', tags: ['Search', 'Reports'] },
  { id: 'coding', name: 'Coding Agent', description: 'Code writing, explanation, debugging, and documentation', icon: FileCode, color: 'text-cyan-500', tags: ['Code', 'Debug'] },
  { id: 'memory', name: 'Memory Agent', description: 'Long-term memory, conversation history, user preferences', icon: Brain, color: 'text-rose-500', tags: ['Memory', 'History'] },
  { id: 'tool', name: 'Tool Agent', description: 'Calculator, Calendar, Gmail, Drive, APIs, databases', icon: Puzzle, color: 'text-orange-500', tags: ['Tools', 'APIs'] },
]

export default function AgentsPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
        <p className="text-muted-foreground mt-1">
          Manage your specialized AI agents
        </p>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {agents.map((agent) => (
          <Card key={agent.id} className="group hover:shadow-md transition-shadow">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className={`p-3 rounded-lg bg-secondary ${agent.color}`}>
                  <agent.icon className="h-6 w-6" />
                </div>
                <Button variant="ghost" size="icon">
                  <Settings className="h-4 w-4" />
                </Button>
              </div>
              <CardTitle className="mt-4">{agent.name}</CardTitle>
              <CardDescription>{agent.description}</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2 mb-4">
                {agent.tags.map((tag) => (
                  <Badge key={tag} variant="secondary">{tag}</Badge>
                ))}
              </div>
              <Button className="w-full gap-2">
                <Play className="h-4 w-4" />
                Open Chat
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
