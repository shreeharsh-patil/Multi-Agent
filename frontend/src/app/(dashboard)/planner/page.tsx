'use client'

import { useState, useEffect, useCallback } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Badge } from '@/components/ui/badge'
import { Calendar, Loader2, Sparkles, ListTodo, Trash2 } from 'lucide-react'
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
    setError(null)
    try {
      const res = await api.planner.list()
      if (res.success && res.data) {
        setPlans(res.data)
      } else {
        setError(res.error || 'Failed to load plans')
      }
    } catch {
      setError('Failed to load plans. Ensure the backend is running.')
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
      const res = await api.planner.delete(id)
      if (!res.success) {
        setError(res.error || 'Failed to delete plan')
        return
      }
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
    <div className="space-y-6 animate-fade-in bg-[#faf9f5]">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-[#26251e]">Planner</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Study planning, task management, and schedule tracking
          </p>
        </div>
        <div className="flex gap-2">
          <Button
            variant={view === 'list' ? 'secondary' : 'outline'}
            size="sm"
            className="gap-2 h-9 rounded-[8px]"
            onClick={() => { setView('list'); setCurrentPlan(null) }}
          >
            <ListTodo className="h-4 w-4 text-primary" />
            Plans
          </Button>
          <Button
            variant={view === 'plan' ? 'secondary' : 'outline'}
            size="sm"
            className="gap-2 h-9 rounded-[8px]"
            onClick={() => setView('plan')}
            disabled={!currentPlan}
          >
            <Calendar className="h-4 w-4 text-primary" />
            Plan
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

      {/* Input */}
      <Card className="shadow-xs">
        <CardContent className="p-4">
          <div className="flex gap-3">
            <Input
              placeholder="Describe a task or goal to plan..."
              value={taskInput}
              onChange={(e) => setTaskInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleCreatePlan()}
              disabled={planning}
              className="flex-1 shadow-sm"
            />
            <Button onClick={handleCreatePlan} disabled={planning || !taskInput.trim()} className="gap-2 shadow-sm">
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
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-primary" />
            <p className="font-sans font-normal tracking-[-0.02em] text-lg text-foreground">Creating your plan...</p>
            <p className="text-xs mt-1">Breaking down tasks and organizing priorities</p>
          </CardContent>
        </Card>
      )}

      {/* Plan View */}
      {view === 'plan' && currentPlan && !planning && (
        <Card className="shadow-xs">
          <CardHeader className="p-5 pb-3">
            <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-lg text-foreground">
              <Sparkles className="h-4.5 w-4.5 text-primary" />
              {currentPlan.title}
            </CardTitle>
          </CardHeader>
          <CardContent className="p-5 pt-0">
            <ScrollArea className="max-h-[500px]">
              <div className="max-w-none whitespace-pre-wrap text-sm text-foreground leading-relaxed font-sans pr-2">
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
            <Card className="shadow-xs">
              <CardHeader className="pb-2 p-5">
                <CardTitle className="text-base font-sans font-normal tracking-[-0.02em] text-foreground flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-primary" />
                  Total Plans
                </CardTitle>
              </CardHeader>
              <CardContent className="p-5 pt-0">
                <p className="text-4.5xl font-sans font-normal text-foreground">{plans.length}</p>
              </CardContent>
            </Card>
          </div>

          {loading ? (
            <Card>
              <CardContent className="py-8 text-center text-muted-foreground">
                <Loader2 className="h-8 w-8 animate-spin mx-auto mb-3 text-primary" />
                <p>Loading plans...</p>
              </CardContent>
            </Card>
          ) : plans.length > 0 ? (
            <Card className="shadow-xs">
              <CardHeader className="p-5">
                <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-lg text-foreground">
                  <Calendar className="h-4.5 w-4.5 text-primary" />
                  My Plans
                </CardTitle>
              </CardHeader>
              <CardContent className="p-5 pt-0">
                <div className="space-y-2">
                  {plans.map((plan) => (
                    <div
                      key={plan.id}
                      className="group flex items-center justify-between p-3 rounded-[8px] border border-border bg-secondary hover:bg-secondary/70 transition-colors cursor-pointer shadow-xs"
                      onClick={() => { setCurrentPlan(plan); setView('plan') }}
                    >
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-sm text-foreground truncate">{plan.title}</p>
                        <p className="text-[10px] text-muted-foreground mt-0.5 font-sans">
                          {formatDate(plan.createdAt)}
                        </p>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        <Badge variant="secondary" className="bg-card text-muted-foreground border border-border text-[10px] px-2 py-0.5 shadow-none">Plan</Badge>
                        <Button
                          variant="ghost"
                          size="icon"
                          className="h-8 w-8 opacity-0 group-hover:opacity-100 transition-opacity rounded-[8px] text-[#c64545] hover:bg-[#c64545]/10"
                          onClick={(e) => handleDelete(plan.id, e)}
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardHeader className="p-5">
                <CardTitle className="flex items-center gap-2 font-sans font-normal tracking-[-0.02em] text-lg text-foreground">
                  <Calendar className="h-4.5 w-4.5 text-primary" />
                  My Plans
                </CardTitle>
              </CardHeader>
              <CardContent className="p-5 pt-0">
                <div className="text-center py-12 text-muted-foreground">
                  <Calendar className="h-12 w-12 mx-auto mb-3 opacity-40 text-primary" />
                  <p className="font-sans font-normal tracking-[-0.02em] text-lg text-foreground">No plans yet</p>
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
