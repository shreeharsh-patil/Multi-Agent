'use client'

import { useState, useRef, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Calendar, Plus, CheckCircle2, Clock, AlertCircle, Loader2, Sparkles, ListTodo, Trash2 } from 'lucide-react'
import { api } from '@/lib/api'
import { formatDate } from '@/lib/utils'

interface Plan {
  id: string
  title: string
  content: string
  createdAt: string
}

export default function PlannerPage() {
  const [taskInput, setTaskInput] = useState('')
  const [planning, setPlanning] = useState(false)
  const [plans, setPlans] = useState<Plan[]>([])
  const [currentPlan, setCurrentPlan] = useState<Plan | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [view, setView] = useState<'list' | 'plan'>('list')

  // Fetch existing plans from backend on mount
  const fetchPlans = useCallback(async () => {
    setLoading(true)
    try {
      const res = await api.planner.list()
      if (res.success && res.data) {
        setPlans(res.data)
      }
    } catch {
      // Silently fail
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchPlans()
  }, [fetchPlans])

  const handleCreatePlan = async () => {
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

        // Persist to backend
        const createRes = await api.planner.create({ title: taskInput, content })
        if (createRes.success && createRes.data) {
          setCurrentPlan(createRes.data)
          setPlans((prev) => [createRes.data!, ...prev])
        } else {
          // Save locally even if persistence fails
          const localPlan: Plan = {
            id: crypto.randomUUID(),
            title: taskInput,
            content,
            createdAt: new Date().toISOString(),
          }
          setCurrentPlan(localPlan)
          setPlans((prev) => [localPlan, ...prev])
        }
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

  const handleDelete = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation()
    if (!window.confirm('Delete this plan?')) return

    try {
      await api.planner.delete(id)
      setPlans((prev) => prev.filter((p) => p.id !== id))
      if (currentPlan?.id === id) {
        setCurrentPlan(null)
        setView('list')
      }
    } catch {
      setError('Failed to delete plan')
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
            variant={view === 'list' ? 'default' : 'outline'}
            size="sm"
            className="gap-2"
            onClick={() => { setView('list'); setCurrentPlan(null) }}
          >
            <ListTodo className="h-4 w-4" />
            Plans
          </Button>
          <Button
            variant={view === 'plan' ? 'default' : 'outline'}
            size="sm"
            className="gap-2"
            onClick={() => setView('plan')}
            disabled={!currentPlan}
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
              onKeyDown={(e) => e.key === 'Enter' && handleCreatePlan()}
              disabled={planning}
              className="flex-1"
            />
            <Button onClick={handleCreatePlan} disabled={planning || !taskInput.trim()} className="gap-2">
              {planning ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Sparkles className="h-4 w-4" />
              )}
              Generate Plan
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
      {view === 'plan' && currentPlan && !planning && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              {currentPlan.title}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="max-h-[500px]">
              <div className="prose prose-sm dark:prose-invert max-w-none whitespace-pre-wrap">
                {currentPlan.content}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      )}

      {/* Plans List View */}
      {view === 'list' && (
        <>
          <div className="grid gap-6 md:grid-cols-1">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-lg flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  Total Plans
                </CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-3xl font-bold">{plans.length}</p>
              </CardContent>
            </Card>
          </div>

          {loading ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3" />
                <p className="font-medium">Loading plans...</p>
              </CardContent>
            </Card>
          ) : plans.length > 0 ? (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  My Plans
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {plans.map((plan) => (
                    <div
                      key={plan.id}
                      className="group flex items-center justify-between p-3 rounded-lg border hover:bg-secondary/50 transition-colors cursor-pointer"
                      onClick={() => { setCurrentPlan(plan); setView('plan') }}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium truncate">{plan.title}</p>
                        <p className="text-xs text-muted-foreground mt-1">
                          {formatDate(plan.createdAt)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant="secondary">Plan</Badge>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-7 w-7 opacity-0 group-hover:opacity-100 transition-opacity"
                          onClick={(e) => handleDelete(plan.id, e)}
                        >
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Calendar className="h-5 w-5" />
                  My Plans
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-center py-12 text-muted-foreground">
                  <Calendar className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p className="text-lg font-medium">No plans yet</p>
                  <p className="text-sm mt-1">
                    Describe a task or goal above to create an AI-generated plan
                  </p>
                </div>
              </CardContent>
            </Card>
          )}
        </>
      )}
    </div>
  )
}
