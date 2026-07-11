import type { ApiResponse, ChatRequest, ChatResponse, DocumentInfo, AgentManifest } from '@shared/types'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  try {
    const res = await fetch(`${BACKEND_URL}${endpoint}`, {
      headers: {
        'Content-Type': 'application/json',
        ...options?.headers,
      },
      ...options,
    })
    return await res.json()
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Network error',
    }
  }
}

export const api = {
  chat: {
    send: (data: ChatRequest) =>
      fetchApi<ChatResponse>('/api/chat', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    stream: (data: ChatRequest) =>
      `${BACKEND_URL}/api/chat/stream?${new URLSearchParams({
        message: data.message,
        ...(data.conversationId && { conversationId: data.conversationId }),
        ...(data.agentId && { agentId: data.agentId }),
      })}`,
  },

  documents: {
    list: () => fetchApi<DocumentInfo[]>('/api/documents'),
    upload: (formData: FormData) =>
      fetchApi<DocumentInfo>('/api/documents/upload', {
        method: 'POST',
        body: formData,
      }),
    delete: (id: string) =>
      fetchApi<null>(`/api/documents/${id}`, { method: 'DELETE' }),
  },

  agents: {
    list: () => fetchApi<AgentManifest[]>('/api/agents'),
    get: (id: string) => fetchApi<AgentManifest>(`/api/agents/${id}`),
  },

  knowledge: {
    query: (query: string, documentIds?: string[]) =>
      fetchApi<{ results: unknown[]; citations: unknown[] }>(
        '/api/knowledge/query',
        {
          method: 'POST',
          body: JSON.stringify({ query, documentIds }),
        },
      ),
  },
}
