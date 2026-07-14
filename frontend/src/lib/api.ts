import type { ApiResponse, ChatRequest, ChatResponse, DocumentInfo, UserProfile } from '@shared/types'
import { getAccessToken } from '@/lib/auth-store'

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

    // Attach JWT access token if available
    const token = getAccessToken()
    if (token) {
      headers['Authorization'] = `Bearer ${token}`
    }

    const res = await fetch(`${BACKEND_URL}${endpoint}`, {
      ...options,
      headers: { ...headers, ...options?.headers },
    })
    return await res.json()
  } catch (error) {
    return {
      success: false,
      error: error instanceof Error ? error.message : 'Network error',
    }
  }
}

async function uploadApiWithProgress<T>(
  endpoint: string,
  formData: FormData,
  onProgress?: (progress: number) => void,
  headers: Record<string, string> = {},
): Promise<ApiResponse<T>> {
  return new Promise((resolve) => {
    const xhr = new XMLHttpRequest()
    xhr.open('POST', `${BACKEND_URL}${endpoint}`)

    // Attach JWT access token if available
    const token = getAccessToken()
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`)
    }

    // Attach other headers
    Object.entries(headers).forEach(([key, value]) => {
      xhr.setRequestHeader(key, value)
    })

    if (onProgress && xhr.upload) {
      xhr.upload.addEventListener('progress', (event) => {
        if (event.lengthComputable) {
          const percentComplete = Math.round((event.loaded / event.total) * 100)
          onProgress(percentComplete)
        }
      })
    }

    xhr.onload = () => {
      try {
        if (xhr.status >= 200 && xhr.status < 300) {
          const response = JSON.parse(xhr.responseText)
          resolve(response)
        } else {
          resolve({
            success: false,
            error: `Upload failed with status ${xhr.status}`,
          })
        }
      } catch (error) {
        resolve({
          success: false,
          error: error instanceof Error ? error.message : 'Invalid JSON response',
        })
      }
    }

    xhr.onerror = () => {
      resolve({
        success: false,
        error: 'Network error occurred during upload',
      })
    }

    xhr.send(formData)
  })
}

export const api = {
  auth: {
    login: (data: { email: string; name: string; image?: string; google_id?: string }) =>
      fetchApi<{ access_token: string; token_type: string; user: { id: string; email: string; name: string; avatar?: string } }>(
        '/api/auth/login',
        { method: 'POST', body: JSON.stringify(data) },
      ),
    getMe: () =>
      fetchApi<UserProfile>('/api/auth/me'),
    updateMe: (data: { name?: string; avatar?: string; preferences?: Record<string, unknown> }) =>
      fetchApi<UserProfile>('/api/auth/me', {
        method: 'PUT',
        body: JSON.stringify(data),
      }),
  },
  chat: {
    send: (data: ChatRequest) =>
      fetchApi<ChatResponse>('/api/chat', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    stream: (data: ChatRequest) => {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      const token = getAccessToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      return fetch(`${BACKEND_URL}/api/chat/stream`, {
        method: 'POST',
        headers,
        body: JSON.stringify(data),
      })
    },
    listConversations: (userId?: string) =>
      fetchApi<Array<{
        id: string
        title: string
        agentId?: string
        messageCount: number
        lastMessage: string
        createdAt: string
        updatedAt: string
      }>>(`/api/chat/conversations${userId ? `?user_id=${userId}` : ''}`),
    getConversation: (id: string) =>
      fetchApi<{
        id: string
        title: string
        agentId?: string
        messages: Array<{
          id: string
          role: string
          content: string
          agentId?: string
          metadata?: Record<string, unknown>
        }>
        createdAt: string
        updatedAt: string
      }>(`/api/chat/conversations/${id}`),
    deleteConversation: (id: string) =>
      fetchApi<{ success: boolean }>(`/api/chat/conversations/${id}`, { method: 'DELETE' }),
  },

  documents: {
    list: () => fetchApi<DocumentInfo[]>('/api/documents'),
    upload: (file: File, userId = 'default', onProgress?: (progress: number) => void) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_id', userId)
      return uploadApiWithProgress<DocumentInfo & { chunks?: number; imageUrl?: string }>(
        '/api/documents/upload',
        formData,
        onProgress,
      )
    },
    get: (id: string) =>
      fetchApi<DocumentInfo & { imageUrl?: string }>(`/api/documents/${id}`),
    downloadUrl: (id: string) => `${BACKEND_URL}/api/documents/${id}/download`,
    delete: (id: string) =>
      fetchApi<null>(`/api/documents/${id}`, { method: 'DELETE' }),
  },

  drive: {
    listFiles: (accessToken: string) =>
      fetchApi<{ files: Array<{ id: string; name: string; mimeType: string; size: number; modifiedTime: string; webViewLink: string; isFolder: boolean }>; total: number }>(
        '/api/drive/files',
        { headers: { 'X-Drive-Access-Token': accessToken } as Record<string, string> },
      ),
    uploadToDrive: (file: File, accessToken: string, folderId?: string, onProgress?: (progress: number) => void) => {
      const formData = new FormData()
      formData.append('file', file)
      const params = new URLSearchParams()
      if (folderId) params.append('folder_id', folderId)
      const query = params.toString()
      return uploadApiWithProgress<{ id: string; name: string }>(
        `/api/drive/upload${query ? `?${query}` : ''}`,
        formData,
        onProgress,
        { 'X-Drive-Access-Token': accessToken } as Record<string, string>,
      )
    },
    deleteFile: (fileId: string, accessToken: string) =>
      fetchApi<{ success: boolean }>(
        `/api/drive/files/${fileId}`,
        { method: 'DELETE', headers: { 'X-Drive-Access-Token': accessToken } as Record<string, string> },
      ),
    getStorage: (accessToken: string) =>
      fetchApi<{ limit: number; usage: number; usageInDrive: number; usageInDriveTrash: number }>(
        '/api/drive/storage',
        { headers: { 'X-Drive-Access-Token': accessToken } as Record<string, string> },
      ),
    createFolder: (name: string, accessToken: string, parentId?: string) => {
      const params = new URLSearchParams({ name })
      if (parentId) params.append('parent_id', parentId)
      return fetchApi<{ id: string; name: string }>(
        `/api/drive/folders?${params.toString()}`,
        { method: 'POST', headers: { 'X-Drive-Access-Token': accessToken } as Record<string, string> },
      )
    },
  },

  notes: {
    list: (userId?: string) =>
      fetchApi<Array<{ id: string; title: string; preview: string; tags: string[]; createdAt: string; updatedAt: string }>>(
        `/api/notes${userId ? `?user_id=${userId}` : ''}`,
      ),
    get: (id: string) =>
      fetchApi<{ id: string; title: string; content: string; tags: string[]; sourceDocumentId?: string; createdAt: string; updatedAt: string }>(
        `/api/notes/${id}`,
      ),
    create: (data: { title: string; content: string; tags?: string[]; user_id?: string }) =>
      fetchApi<{ id: string; title: string; content: string; tags: string[] }>(
        '/api/notes',
        { method: 'POST', body: JSON.stringify(data) },
      ),
    update: (id: string, data: { title?: string; content?: string; tags?: string[] }) =>
      fetchApi<{ id: string; title: string; content: string; tags: string[] }>(
        `/api/notes/${id}`,
        { method: 'PUT', body: JSON.stringify(data) },
      ),
    delete: (id: string) =>
      fetchApi<{ success: boolean }>(`/api/notes/${id}`, { method: 'DELETE' }),
    exportUrl: (id: string, format: 'pdf' | 'docx' | 'markdown') =>
      `${BACKEND_URL}/api/notes/${id}/export?format=${format}`,
  },

  knowledge: {
    query: (query: string, userId?: string, documentIds?: string[]) =>
      fetchApi<{
        results: Array<{ id: string; content: string; metadata: Record<string, unknown>; score: number }>
        citations: Array<{ file_name: string; page_number?: number; section?: string; text: string }>
        answer: string
      }>('/api/knowledge/query', {
        method: 'POST',
        body: JSON.stringify({ query, user_id: userId, document_ids: documentIds }),
      }),
  },

  research: {
    list: (userId?: string) =>
      fetchApi<Array<{ id: string; query: string; content: string; createdAt: string }>>(
        `/api/research${userId ? `?user_id=${userId}` : ''}`,
      ),
    get: (id: string) =>
      fetchApi<{ id: string; query: string; content: string; createdAt: string }>(
        `/api/research/${id}`,
      ),
    create: (data: { query: string; content: string; user_id?: string }) =>
      fetchApi<{ id: string; query: string; content: string; createdAt: string }>(
        '/api/research',
        { method: 'POST', body: JSON.stringify(data) },
      ),
    delete: (id: string) =>
      fetchApi<{ success: boolean }>(`/api/research/${id}`, { method: 'DELETE' }),
  },

  planner: {
    list: (userId?: string) =>
      fetchApi<Array<{ id: string; title: string; content: string; createdAt: string }>>(
        `/api/planner${userId ? `?user_id=${userId}` : ''}`,
      ),
    get: (id: string) =>
      fetchApi<{ id: string; title: string; content: string; createdAt: string }>(
        `/api/planner/${id}`,
      ),
    create: (data: { title: string; content: string; user_id?: string }) =>
      fetchApi<{ id: string; title: string; content: string; createdAt: string }>(
        '/api/planner',
        { method: 'POST', body: JSON.stringify(data) },
      ),
    delete: (id: string) =>
      fetchApi<{ success: boolean }>(`/api/planner/${id}`, { method: 'DELETE' }),
  },

  quiz: {
    generate: (data: { topic: string; difficulty: string; question_count: number }) =>
      fetchApi<{
        quiz_id: string
        topic: string
        difficulty: string
        questions: Array<{
          question: string
          options: Array<{ label: string; text: string }>
        }>
      }>('/api/quiz/generate', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    check: (data: { quiz_id: string; question_index: number; selected_answer: string }) =>
      fetchApi<{
        is_correct: boolean
        correct_answer: string
        explanation: string
      }>('/api/quiz/check', {
        method: 'POST',
        body: JSON.stringify(data),
      }),
    submit: (quiz_id: string) =>
      fetchApi<{
        quiz_id: string
        topic: string
        score: number
        total_questions: number
        percentage: number
        completed: boolean
        results: Array<{
          question_index: number
          question: string
          options: Array<{ label: string; text: string }>
          correct_answer: string
          explanation: string
          user_answer: string | null
          is_correct: boolean | null
        }>
      }>('/api/quiz/submit', {
        method: 'POST',
        body: JSON.stringify({ quiz_id }),
      }),
    history: () =>
      fetchApi<Array<{
        id: string
        topic: string
        difficulty: string
        score: number | null
        total_questions: number
        completed: boolean
        created_at: string
      }>>('/api/quiz/history'),
    get: (quiz_id: string) =>
      fetchApi<{
        id: string
        topic: string
        difficulty: string
        score: number | null
        total_questions: number
        completed: boolean
        questions: Array<{
          question: string
          options: Array<{ label: string; text: string }>
          correct_answer: string | null
          explanation: string | null
        }>
        answers: Array<{
          question_index: number
          selected_answer: string
          is_correct: boolean
        }>
        created_at: string
      }>(`/api/quiz/${quiz_id}`),
    delete: (quiz_id: string) =>
      fetchApi<{ success: boolean }>(`/api/quiz/${quiz_id}`, { method: 'DELETE' }),
  },

  agents: {
    list: () =>
      fetchApi<Array<{ id: string; name: string; description: string; icon: string }>>('/api/agents'),
  },
}
