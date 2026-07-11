'use client'

import { useState, useRef, useEffect } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Calendar, Plus, CheckCircle2, Clock, AlertCircle, Loader2, Sparkles, ListTodo } from 'lucide-react'
import { api } from '@/lib/api'

interface Task {
  id: string
  title: string
  status: 'pending' | 'in_progress' | 'completed'
  priority: string
  dueDate?: string
}

export default function PlannerPage() {
  const [taskInput, setTaskInput] = useState('')
  const [planning, setPlanning] = useState(false)
  const [tasks, setTasks] = useState<Task[]>([])
  const [planContent, setPlanContent] = useState<string>('')
  const [error, setError] = useState<string | null>(null)
  const [view, setView] = useState<'tasks' | 'plan'>('tasks')

  const handleAddTask = async () => {
    if (!taskInput.trim() || planning) return
    setPlanning(true)
    setError(null)

    try {
      const res = await api.chat.send({
        message: `I need to plan and manage the following task/request: ${taskInput}

Please respond with:
1. A clear breakdown of tasks needed
2. Suggested priority (High/Medium/Low) for each task
3. Estimated timeline
4. Any dependencies or prerequisites

Format the response with clear sections and bullet points.`,
        agent_id: 'planner',
      })

      if (res.success && res.data) {
        const content = res.data.output
        setPlanContent(content)
        setView('plan')
      } else {
        setError(res.error || 'Planning failed')
      }
    } catch (e) {
      setError('Failed to connect to planner. Ensure the backend is running.')
    } finally {
      setPlanning(false)
    }
  }

  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Planner</h1>
          <p className="text-muted-foreground mt-1">
            Study planning, task management, and schedule tracking
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={view === 'tasks' ? 'default' : 'outline'}
            size="sm"
            className="gap-2"
            onClick={() => setView('tasks')}
          >
            <ListTodo className="h-4 w-4" />
            Tasks
          </Button>
          <Button
            variant={view === 'plan' ? 'default' : 'outline'}
            size="sm"
            className="gap-2"
            onClick={() => setView('plan')}
          >
            <Calendar className="h-4 w-4" />
            Plan
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

      {/* Input */}
      <Card>
        <CardContent className="p-4">
          <div className="flex gap-3">
            <Input
              placeholder="Describe a task or goal to plan..."
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddTask()}
              disabled={planning}
              className="flex-1"
            />
            <Button onClick={handleAddTask} disabled={planning || !taskInput.trim()} className="gap-2">
              {planning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : view === 'plan' ? (
                <Sparkles className="h-4 w-4" />
              ) : (
                <Plus className="h-4 w-4" />
              )}
              {view === 'plan' ? 'Plan' : 'Add'}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Loading */}
      {planning && (
        <Card>
          <CardContent className="py-8 text-center text-muted-foreground">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3" />
            <p className="font-medium">Creating your plan...</p>
            <p className="text-sm mt-1">Breaking down tasks and organizing priorities</p>
          </CardContent>
        </Card>
      )}

      {/* Plan View */}
      {view === 'plan' && planContent && !planning && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              AI-Generated Plan
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="max-h-[500px]">
              <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                {planContent}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Task Stats View */}
      {view === 'tasks' && (
        <>
          <div className="grid gap-6 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <AlertCircle className="h-4 w-4 text-destructive" />
                  Pending
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">
                  {tasks.filter((t) => t.status === 'pending').length}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Clock className="h-4 w-4 text-amber-500" />
                  In Progress
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">
                  {tasks.filter((t) => t.status === 'in_progress').length}
                </p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                  Completed
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">
                  {tasks.filter((t) => t.status === 'completed').length}
                </p>
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Calendar className="h-5 w-5" />
                My Plans
              </CardTitle>
            </CardHeader>
            <CardContent>
              {planContent ? (
                <div className="space-y-3">
                  <div className="flex items-center justify-between p-3 rounded-lg border hover:bg-secondary/50 transition-colors">
                    <div className="flex-1 min-w-0">
                      <p className="font-medium truncate">
                        {taskInput || 'Recent plan'}
                      </p>
                      <p className="text-xs text-muted-foreground mt-1">
                        Click "Plan" tab to view details
                      </p>
                    </div>
                    <Badge variant="secondary" className="shrink-0">Ready</Badge>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground">
                  <Calendar className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p className="text-lg font-medium">No plans yet</p>
                  <p className="text-sm mt-1">
                    Describe a task or goal above to create an AI-generated plan
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
