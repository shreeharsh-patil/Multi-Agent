'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Calendar, Plus, CheckCircle2, Clock, AlertCircle } from 'lucide-react'

const tasks = [
  { id: '1', title: 'Review AI notes', due: '2026-07-12', priority: 'high', status: 'pending' },
  { id: '2', title: 'Complete quiz on ML', due: '2026-07-14', priority: 'medium', status: 'in_progress' },
  { id: '3', title: 'Research paper summary', due: '2026-07-16', priority: 'low', status: 'pending' },
  { id: '4', title: 'Study neural networks', due: '2026-07-11', priority: 'high', status: 'completed' },
]

export default function PlannerPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Planner</h1>
          <p className="text-muted-foreground mt-1">
            Study planning, task management, and schedule tracking
          </p>
        </div>
        <Button className="gap-2">
          <Plus className="h-4 w-4" />
          Add Task
        </Button>
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-lg flex items-center gap-2">
              <AlertCircle className="h-4 w-4 text-destructive" />
              Pending
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-3xl font-bold">2</p>
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
            <p className="text-3xl font-bold">1</p>
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
            <p className="text-3xl font-bold">1</p>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Calendar className="h-5 w-5" />
            Tasks
          </CardTitle>
          <CardDescription>4 tasks · 2 due this week</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {tasks.map((task) => (
              <div key={task.id} className="flex items-center gap-4 p-3 rounded-lg border hover:bg-secondary/50 transition-colors">
                <div className={`p-2 rounded-full ${
                  task.status === 'completed' ? 'bg-emerald-500/10 text-emerald-500' :
                  task.status === 'in_progress' ? 'bg-amber-500/10 text-amber-500' :
                  'bg-secondary'
                }`}>
                  {task.status === 'completed' ? <CheckCircle2 className="h-4 w-4" /> :
                   task.status === 'in_progress' ? <Clock className="h-4 w-4" /> :
                   <AlertCircle className="h-4 w-4" />}
                </div>
                <div className="flex-1">
                  <p className={`font-medium ${task.status === 'completed' ? 'line-through text-muted-foreground' : ''}`}>
                    {task.title}
                  </p>
                  <p className="text-sm text-muted-foreground">Due: {task.due}</p>
                </div>
                <Badge variant={task.priority === 'high' ? 'destructive' : task.priority === 'medium' ? 'warning' : 'secondary'}>
                  {task.priority}
                </Badge>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
