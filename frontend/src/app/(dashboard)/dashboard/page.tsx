'use client'

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Bot, MessageSquare, FileText, BookOpen, Activity, Sparkles } from 'lucide-react'

const stats = [
  { label: 'Active Agents', value: '9', icon: Bot, color: 'text-blue-500' },
  { label: 'Conversations', value: '0', icon: MessageSquare, color: 'text-green-500' },
  { label: 'Documents', value: '0', icon: FileText, color: 'text-purple-500' },
  { label: 'Knowledge Items', value: '0', icon: BookOpen, color: 'text-amber-500' },
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
