export type AgentId =
  | 'knowledge'
  | 'drive'
  | 'notes'
  | 'quiz'
  | 'planner'
  | 'research'
  | 'coding'
  | 'memory'
  | 'tool'
  | 'calendar'

export interface AgentManifest {
  id: AgentId
  name: string
  description: string
  icon: string
  enabled: boolean
  capabilities: string[]
  version: string
}

export interface UserProfile {
  id: string
  email: string
  name: string
  avatar?: string
  createdAt: string
  preferences: UserPreferences
}

export interface UserPreferences {
  theme: 'light' | 'dark' | 'system'
  defaultModel: string
  notifications: boolean
  language: string
  useOpendocumentsRag?: boolean
}

export interface Conversation {
  id: string
  userId: string
  title: string
  agentId?: AgentId
  messages: Message[]
  createdAt: string
  updatedAt: string
  metadata?: Record<string, unknown>
}

export interface Message {
  id: string
  role: 'user' | 'assistant' | 'system' | 'tool'
  content: string
  agentId?: AgentId
  citations?: Citation[]
  toolCalls?: ToolCall[]
  toolResults?: ToolResult[]
  timestamp: string
  metadata?: Record<string, unknown>
}

export interface Citation {
  fileName: string
  pageNumber?: number
  section?: string
  text: string
  score?: number
}

export interface ToolCall {
  id: string
  name: string
  arguments: Record<string, unknown>
}

export interface ToolResult {
  id: string
  name: string
  result: unknown
  error?: string
}

export interface DocumentInfo {
  id: string
  userId: string
  fileName: string
  fileType: string
  fileSize: number
  status: 'uploading' | 'processing' | 'ready' | 'error'
  chunks: number
  createdAt: string
  updatedAt: string
  workspaceId?: string
}

export interface KnowledgeBaseItem {
  id: string
  userId: string
  documentId: string
  content: string
  embedding?: number[]
  metadata: Record<string, unknown>
  createdAt: string
}

export interface MemoryItem {
  id: string
  userId: string
  type: 'conversation' | 'preference' | 'fact' | 'semantic'
  content: string
  key: string
  value: unknown
  score?: number
  createdAt: string
  updatedAt: string
}

export interface AgentTask {
  id: string
  agentId: AgentId
  userId: string
  input: string
  output?: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  error?: string
  startedAt?: string
  completedAt?: string
  createdAt: string
}

export interface ActivityEvent {
  id: string
  userId: string
  type: string
  description: string
  agentId?: AgentId
  metadata?: Record<string, unknown>
  timestamp: string
}

export interface ApiResponse<T = unknown> {
  success: boolean
  data?: T
  error?: string
  message?: string
}

export interface PaginatedResponse<T> extends ApiResponse<T[]> {
  total: number
  page: number
  limit: number
  totalPages: number
}

export interface ChatRequest {
  conversation_id?: string
  message: string
  agent_id?: AgentId
  user_id?: string
  attachments?: Array<{
    name: string
    size: number
    documentId?: string
  }>
  team_agents?: AgentId[]
  workspace_id?: string
}

export interface ChatResponse {
  conversation_id: string
  output: string
  citations: Citation[]
  agent_traces: AgentTrace[]
  events_count: number
  success: boolean
  error?: string
}

export interface AgentTrace {
  agent_id: string
  event_type: string
  has_content: boolean
}
