'use client'

import { useState, useEffect } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button, buttonVariants } from '@/components/ui/button'
import {
  Bot,
  BookOpen,
  Brain,
  Search,
  FileCode,
  StickyNote,
  GraduationCap,
  Calendar,
  Puzzle,
  Loader2,
} from 'lucide-react'
import { api } from '@/lib/api'
import Link from 'next/link'

const iconMap: Record<string, import('lucide-react').LucideIcon> = {
  BookOpen: BookOpen,
  Brain: Brain,
  StickyNote: StickyNote,
  GraduationCap: GraduationCap,
  Calendar: Calendar,
  Search: Search,
  FileCode: FileCode,
  Puzzle: Puzzle,
}

const colorMap: Record<string, string> = {
  knowledge: 'text-blue-500',
  drive: 'text-green-500',
  notes: 'text-purple-500',
  quiz: 'text-amber-500',
  planner: 'text-pink-500',
  research: 'text-indigo-500',
  coding: 'text-cyan-500',
  memory: 'text-rose-500',
  tool: 'text-orange-500',
}

const tagMap: Record<string, string[]> = {
  knowledge: ['RAG', 'Search', 'Citations'],
  drive: ['Drive', 'Files', 'Sync'],
  notes: ['Notes', 'Flashcards'],
  quiz: ['Quiz', 'MCQ', 'Exam'],
  planner: ['Planning', 'Schedule'],
  research: ['Search', 'Reports'],
  coding: ['Code', 'Debug'],
  memory: ['Memory', 'History'],
  tool: ['Tools', 'APIs'],
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Array<{ id: string; name: string; description: string; icon: string }>>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    const fetchAgents = async () => {
      setLoading(true)
      try {
        const res = await api.agents.list()
        if (mounted && res.success && res.data) {
          setAgents(res.data)
        } else if (mounted) {
          setError(res.error || 'Failed to load agents')
        }
      } catch (e) {
        if (mounted) setError('Failed to connect to backend')
      } finally {
        if (mounted) setLoading(false)
      }
    }
    fetchAgents()
    return () => { mounted = false }
  }, [])

  const renderAgentList = () => {
    return agents.map((agent) => {
      const Icon = iconMap[agent.icon] || Bot
      const color = colorMap[agent.id] || 'text-muted-foreground'
      const tags = tagMap[agent.id] || []
      return (
        <Card key={agent.id} className="group hover:shadow-md transition-shadow">
          <CardHeader>
            <div className="flex items-start justify-between">
              <div className={`p-3 rounded-lg bg-secondary ${color}`}>
                <Icon className="h-6 w-6" />
              </div>
              <Link href="/chat" className={`${buttonVariants({ variant: 'ghost', size: 'sm' })} gap-2 opacity-0 group-hover:opacity-100 transition-opacity`}>
                Chat
              </Link>
            </div>
            <CardTitle className="mt-4">{agent.name}</CardTitle>
            <CardDescription>{agent.description}</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2 mb-4">
              {tags.map((tag) => (
                <Badge key={tag} variant="secondary">{tag}</Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )
    })
  }

  if (loading) {
    return (
      <div className="space-y-6 animate-fade-in">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
          <p className="text-muted-foreground mt-1">
            Manage your specialized AI agents
          </p>
        </div>
        <Card>
          <CardContent className="py-16 text-center text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3" />
            <p>Loading agents...</p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Agents</h1>
        <p className="text-muted-foreground mt-1">
          {agents.length} specialized AI agents available
        </p>
      </div>

      {error && (
        <div className="bg-destructive/10 text-destructive text-sm px-4 py-3 rounded-lg">
          {error}
          <Button variant="link" size="sm" className="ml-2" onClick={() => setError(null)}>
            Dismiss
          </Button>
        </div>
      )}

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {renderAgentList()}
      </div>
    </div>
  )
}
