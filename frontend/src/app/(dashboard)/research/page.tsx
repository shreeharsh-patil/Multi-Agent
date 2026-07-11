'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Search, Globe, FileText, ExternalLink } from 'lucide-react'

const reports = [
  { id: '1', title: 'Latest AI Research Trends', sources: 8, date: '2026-07-10', status: 'completed' },
  { id: '2', title: 'Machine Learning in Healthcare', sources: 12, date: '2026-07-09', status: 'completed' },
  { id: '3', title: 'Quantum Computing Advances', sources: 5, date: '2026-07-07', status: 'draft' },
]

export default function ResearchPage() {
  return (
    <div className="space-y-6 animate-fade-in">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Research</h1>
        <p className="text-muted-foreground mt-1">
          Internet research, source comparison, and report generation
        </p>
      </div>

      <Card>
        <CardContent className="p-6">
          <div className="flex gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Research a topic..." className="pl-10" />
            </div>
            <Button className="gap-2">
              <Globe className="h-4 w-4" />
              Research
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {reports.map((report) => (
          <Card key={report.id} className="group hover:shadow-md transition-shadow cursor-pointer">
            <CardHeader>
              <div className="flex items-start justify-between">
                <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-500">
                  <FileText className="h-5 w-5" />
                </div>
                <span className={`text-xs px-2 py-1 rounded-full ${
                  report.status === 'completed' ? 'bg-emerald-500/10 text-emerald-500' : 'bg-amber-500/10 text-amber-500'
                }`}>
                  {report.status}
                </span>
              </div>
              <CardTitle className="text-lg mt-3">{report.title}</CardTitle>
              <CardDescription>
                {report.sources} sources · {report.date}
              </CardDescription>
            </CardHeader>
            <CardContent>
              <Button variant="outline" size="sm" className="w-full gap-2">
                <ExternalLink className="h-4 w-4" />
                View Report
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
