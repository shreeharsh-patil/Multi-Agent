'use client'

import { useState, useRef, useEffect } from 'react'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { ScrollArea } from '@/components/ui/scroll-area'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Badge } from '@/components/ui/badge'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Send, Bot, User, Sparkles, Plus } from 'lucide-react'

const agents = [
  { id: 'auto', name: 'Auto (Orchestrator)' },
  { id: 'knowledge', name: 'Knowledge Agent' },
  { id: 'drive', name: 'Drive Agent' },
  { id: 'notes', name: 'Notes Agent' },
  { id: 'quiz', name: 'Quiz Agent' },
  { id: 'planner', name: 'Planner Agent' },
  { id: 'research', name: 'Research Agent' },
  { id: 'coding', name: 'Coding Agent' },
  { id: 'memory', name: 'Memory Agent' },
  { id: 'tool', name: 'Tool Agent' },
]

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  agentId?: string
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      role: 'assistant',
      content: 'Hello! I\'m your Multi-Agent AI Platform. I have 9 specialized agents to help you. What would you like to do today?',
    },
  ])
  const [input, setInput] = useState('')
  const [selectedAgent, setSelectedAgent] = useState('auto')
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return

    const userMsg: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content: input,
    }

    const assistantMsg: Message = {
      id: crypto.randomUUID(),
      role: 'assistant',
      content: `Received: "${input}"\n\nAgent: ${selectedAgent}\n\nBackend integration coming in Module 6.`,
      agentId: selectedAgent === 'auto' ? undefined : selectedAgent,
    }

    setMessages((prev) => [...prev, userMsg, assistantMsg])
    setInput('')
  }

  return (
    <div className="flex h-full gap-6 animate-fade-in">
      <div className="flex-1 flex flex-col">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Chat</h1>
            <p className="text-muted-foreground mt-1">
              Interact with your AI agents
            </p>
          </div>
          <Select value={selectedAgent} onValueChange={setSelectedAgent}>
            <SelectTrigger className="w-[200px]">
              <SelectValue placeholder="Select agent" />
            </SelectTrigger>
            <SelectContent>
              {agents.map((agent) => (
                <SelectItem key={agent.id} value={agent.id}>
                  {agent.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <Card className="flex-1 flex flex-col">
          <ScrollArea ref={scrollRef} className="flex-1 p-6">
            <div className="space-y-6">
              {messages.map((msg) => (
                <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}>
                  {msg.role === 'assistant' && (
                    <Avatar className="h-8 w-8 shrink-0">
                      <AvatarFallback className="bg-primary text-primary-foreground">
                        <Bot className="h-4 w-4" />
                      </AvatarFallback>
                    </Avatar>
                  )}
                  <div className={`max-w-[80%] ${msg.role === 'user' ? 'order-1' : ''}`}>
                    {msg.agentId && (
                      <Badge variant="outline" className="mb-1 text-xs">
                        {agents.find((a) => a.id === msg.agentId)?.name}
                      </Badge>
                    )}
                    <div
                      className={`rounded-lg px-4 py-3 text-sm ${
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-secondary text-secondary-foreground'
                      }`}
                    >
                      <pre className="whitespace-pre-wrap font-sans">{msg.content}</pre>
                    </div>
                  </div>
                  {msg.role === 'user' && (
                    <Avatar className="h-8 w-8 shrink-0">
                      <AvatarFallback className="bg-muted">
                        <User className="h-4 w-4" />
                      </AvatarFallback>
                    </Avatar>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>

          <div className="p-4 border-t">
            <div className="flex gap-3">
              <Input
                placeholder="Type your message..."
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && handleSend()}
                className="flex-1"
              />
              <Button onClick={handleSend} className="gap-2">
                <Send className="h-4 w-4" />
                Send
              </Button>
            </div>
          </div>
        </Card>
      </div>

      <div className="hidden lg:block w-80 space-y-4">
        <Card className="p-4">
          <h3 className="font-semibold flex items-center gap-2 mb-3">
            <Sparkles className="h-4 w-4" />
            Quick Actions
          </h3>
          <div className="space-y-2">
            <Button variant="outline" className="w-full justify-start gap-2" size="sm">
              <Plus className="h-4 w-4" />
              New Conversation
            </Button>
          </div>
        </Card>

        <Card className="p-4">
          <h3 className="font-semibold mb-3">Suggestions</h3>
          <div className="space-y-2">
            {[
              'Summarize a document',
              'Research a topic',
              'Help me study',
              'Write some code',
              'Plan my schedule',
            ].map((suggestion) => (
              <Button
                key={suggestion}
                variant="ghost"
                className="w-full justify-start text-sm h-auto py-2"
                onClick={() => setInput(suggestion)}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        </Card>
      </div>
    </div>
  )
}
