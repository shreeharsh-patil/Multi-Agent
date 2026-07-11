import type { ApiResponse, ChatRequest, ChatResponse, DocumentInfo } from '@shared/types'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  try {
    const headers: Record<string, string> = {}
    const isFormData = options?.body instanceof FormData
    if (!isFormData) {
      headers['Content-Type'] = 'application/json'
    }
    const res = await fetch(`${BACKEND_URL}${endpoint}`, {
      headers,
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
  },

  documents: {
    list: () => fetchApi<DocumentInfo[]>('/api/documents'),
    upload: (file: File, userId = 'default') => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_id', userId)
      return fetchApi<DocumentInfo & { chunks?: number }>('/api/documents/upload', {
        method: 'POST',
        body: formData,
      })
    },
    delete: (id: string) =>
      fetchApi<null>(`/api/documents/${id}`, { method: 'DELETE' }),
  },

  agents: {
    list: () =>
      fetchApi<Array<{ id: string; name: string; description: string }>>('/api/agents'),
  },
}
