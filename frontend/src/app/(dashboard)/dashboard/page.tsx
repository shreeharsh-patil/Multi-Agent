'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Bot, MessageSquare, FileText, BookOpen, Activity, Sparkles } from 'lucide-react'

const stats = [
  { label: 'Active Agents', value: '9', icon: Bot, color: 'text-blue-500' },
  { label: 'Conversations', value: '0', icon: MessageSquare, color: 'text-green-500' },
  { label: 'Documents', value: '0', icon: FileText, color: 'text-purple-500' },
  { label: 'Knowledge Items', value: '0', icon: BookOpen, color: 'text-amber-500' },
]

const agents = [
  { name: 'Knowledge Agent', description: 'RAG & document search', color: 'bg-blue-500/10 text-blue-500' },
  { name: 'Drive Agent', description: 'Google Drive integration', color: 'bg-green-500/10 text-green-500' },
  { name: 'Notes Agent', description: 'Structured notes & summaries', color: 'bg-purple-500/10 text-purple-500' },
  { name: 'Quiz Agent', description: 'MCQs & practice questions', color: 'bg-amber-500/10 text-amber-500' },
  { name: 'Planner Agent', description: 'Study & task planning', color: 'bg-pink-500/10 text-pink-500' },
  { name: 'Research Agent', description: 'Internet search & reports', color: 'bg-indigo-500/10 text-indigo-500' },
  { name: 'Coding Agent', description: 'Code writing & debugging', color: 'bg-cyan-500/10 text-cyan-500' },
  { name: 'Memory Agent', description: 'Long-term memory', color: 'bg-rose-500/10 text-rose-500' },
  { name: 'Tool Agent', description: 'APIs & external tools', color: 'bg-orange-500/10 text-orange-500' },
]

export default function DashboardPage() {
  return (
    <div className="space-y-8 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
        <p className="text-muted-foreground mt-1">
          Welcome to your Multi-Agent AI Platform
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        {stats.map((stat) => (
          <Card key={stat.label}>
            <CardContent className="p-6">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{stat.label}</p>
                  <p className="text-3xl font-bold mt-1">{stat.value}</p>
                </div>
                <div className={`p-3 rounded-full bg-secondary ${stat.color}`}>
                  <stat.icon className="h-6 w-6" />
                </div>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5" />
            Available Agents
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {agents.map((agent) => (
              <Card key={agent.name} className="border-0 bg-secondary/50">
                <CardContent className="p-4">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg ${agent.color}`}>
                      <Bot className="h-5 w-5" />
                    </div>
                    <div>
                      <h3 className="font-medium">{agent.name}</h3>
                      <p className="text-sm text-muted-foreground">{agent.description}</p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            Recent Activity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Activity className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No recent activity</p>
            <p className="text-sm">Start a conversation to see activity here</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
