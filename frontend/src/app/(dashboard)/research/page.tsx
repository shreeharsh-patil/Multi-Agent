'use client'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Search, Globe, FileText } from 'lucide-react'

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

      <Card>
        <CardContent className="py-12">
          <div className="text-center text-muted-foreground">
            <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p className="text-lg font-medium">No research reports yet</p>
            <p className="text-sm mt-1">Use the Research Agent to generate reports on any topic</p>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
