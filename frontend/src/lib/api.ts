import type { ApiResponse, ChatRequest, ChatResponse, DocumentInfo, UserProfile } from '@shared/types'
import { getAccessToken } from '@/lib/auth-store'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

/** Retry configuration for network-level failures (cold starts, QUIC errors, etc.). */
const RETRY_LIMIT = 3
const RETRY_BASE_MS = 1000
const RETRY_MAX_MS = 8000

/** Compute the delay before the next retry using capped exponential backoff. */
function retryDelay(attempt: number): number {
  const delay = Math.min(RETRY_BASE_MS * 2 ** attempt, RETRY_MAX_MS)
  return delay + Math.random() * 500  // jitter to avoid thundering herd
}

/**
 * True for network-level failures that are safe to retry (cold starts,
 * QUIC protocol errors, DNS failures, intermittent disconnects).
 * HTTP 4xx/5xx responses are NOT retried — those are application errors.
 */
function isRetryableNetworkError(error: unknown): boolean {
  if (!(error instanceof TypeError)) return false
  const msg = error.message.toLowerCase()
  return (
    msg.includes('networkerror') ||
    msg.includes('failed to fetch') ||
    msg.includes('network') ||
    msg.includes('internet disconnected') ||
    msg.includes('quic') ||
    msg.includes('load failed') ||
    msg.includes('abort') ||
    msg.includes('timeout')
  )
}

async function fetchWithTimeout(
  url: string,
  options: RequestInit,
  timeoutMs = 60_000,
): Promise<Response> {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const res = await fetch(url, {
      ...options,
      signal: controller.signal,
    })
    return res
  } finally {
    clearTimeout(timer)
  }
}

async function fetchApi<T>(
  endpoint: string,
  options?: RequestInit,
): Promise<ApiResponse<T>> {
  let lastError: unknown

  for (let attempt = 0; attempt < RETRY_LIMIT; attempt++) {
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

      const res = await fetchWithTimeout(`${BACKEND_URL}${endpoint}`, {
        ...options,
        headers: { ...headers, ...options?.headers },
      })
      return await res.json()
    } catch (error) {
      lastError = error

      // Only retry network-level failures (cold starts, QUIC, etc.).
      // HTTP errors (4xx, 5xx) are caught inside the try and don't throw.
      if (!isRetryableNetworkError(error)) {
        break
      }

      // Don't delay on the last attempt
      if (attempt < RETRY_LIMIT - 1) {
        await new Promise((resolve) => setTimeout(resolve, retryDelay(attempt)))
      }
    }
  }

  return {
    success: false,
    error:
      lastError instanceof Error ? lastError.message : 'Network error',
  }
}

/**
 * Perform an XHR upload with progress tracking and automatic retry
 * on network-level failures (cold starts, QUIC errors, etc.).
 */
function xhrUploadWithRetry<T>(
  url: string,
  formData: FormData,
  onProgress?: (progress: number) => void,
  headers: Record<string, string> = {},
): Promise<ApiResponse<T>> {
  return new Promise((resolve) => {
    let attempt = 0

    const tryUpload = () => {
      const xhr = new XMLHttpRequest()
      xhr.open('POST', url)

      // Attach JWT access token if available
      const token = getAccessToken()
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`)
      }

      // Attach other headers
      Object.entries(headers).forEach(([key, value]) => {
        xhr.setRequestHeader(key, value)
      })

      // Timeout for cold starts (Render free tier can take 30-60s)
      xhr.timeout = 120_000

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
            // HTTP errors are not retried
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
        // Network error — retry with backoff
        if (attempt < RETRY_LIMIT - 1) {
          attempt++
          setTimeout(tryUpload, retryDelay(attempt))
        } else {
          resolve({
            success: false,
            error: 'Network error occurred during upload',
          })
        }
      }

      xhr.ontimeout = () => {
        // Timeout — retry with backoff (Render cold starts can be slow)
        if (attempt < RETRY_LIMIT - 1) {
          attempt++
          setTimeout(tryUpload, retryDelay(attempt))
        } else {
          resolve({
            success: false,
            error: 'Upload timed out after multiple retries',
          })
        }
      }

      xhr.send(formData)
    }

    tryUpload()
  })
}



export function mkheaders(accessToken: string, refreshToken?: string): Record<string, string> {
  const h: Record<string, string> = { 'X-Drive-Access-Token': accessToken }
  if (refreshToken) h['X-Drive-Refresh-Token'] = refreshToken
  return h
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
    send: (data: ChatRequest, googleAccessToken?: string) =>
      fetchApi<ChatResponse>('/api/chat', {
        method: 'POST',
        body: JSON.stringify(data),
        headers: googleAccessToken ? { 'X-Google-Access-Token': googleAccessToken } : undefined,
      }),
    stream: (data: ChatRequest, googleAccessToken?: string) => {
      const headers: Record<string, string> = { 'Content-Type': 'application/json' }
      const token = getAccessToken()
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      }
      if (googleAccessToken) headers['X-Google-Access-Token'] = googleAccessToken
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
    createShare: (id: string) => fetchApi<{ token: string; conversationId: string }>(`/api/shares/chat/${id}`, { method: 'POST' }),
    revokeShare: (id: string) => fetchApi<{ success: boolean }>(`/api/shares/chat/${id}`, { method: 'DELETE' }),
  },

  documents: {
    list: (workspaceId?: string) => fetchApi<DocumentInfo[]>(`/api/documents${workspaceId ? `?workspace_id=${workspaceId === 'unfiled' ? '__unfiled__' : workspaceId}` : ''}`),
    storage: () => fetchApi<{ used: number }>('/api/documents/storage'),
    upload: (file: File, userId = 'default', onProgress?: (progress: number) => void, workspaceId?: string, driveAccessToken?: string) => {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('user_id', userId)
      if (workspaceId) formData.append('workspace_id', workspaceId)
      const headers: Record<string, string> = {}
      if (driveAccessToken) {
        headers['X-Drive-Access-Token'] = driveAccessToken
      }
      return xhrUploadWithRetry<DocumentInfo & { chunks?: number; imageUrl?: string; driveFileId?: string; driveWebViewLink?: string }>(
        `${BACKEND_URL}/api/documents/upload`,
        formData,
        onProgress,
        headers,
      )
    },
    get: (id: string) =>
      fetchApi<DocumentInfo & { imageUrl?: string }>(`/api/documents/${id}`),
    downloadUrl: (id: string) => `${BACKEND_URL}/api/documents/${id}/download`,
    delete: (id: string) =>
      fetchApi<null>(`/api/documents/${id}`, { method: 'DELETE' }),
    moveToWorkspace: (id: string, workspaceId?: string) =>
      fetchApi<{ id: string; workspaceId?: string }>(`/api/documents/${id}/workspace${workspaceId ? `?workspace_id=${workspaceId}` : ''}`, { method: 'PATCH' }),
    uploadToDrive: (id: string, googleAccessToken?: string) => {
      const headers: Record<string, string> = {}
      const token = getAccessToken()
      if (token) headers['Authorization'] = `Bearer ${token}`
      if (googleAccessToken) headers['X-Drive-Access-Token'] = googleAccessToken
      return fetchApi<{ driveFileId: string; driveWebViewLink: string }>(
        `/api/documents/${id}/drive-upload`,
        { method: 'POST', headers, body: '{}' },
      )
    },
  },

  workspaces: {
    list: () => fetchApi<Array<{ id: string; name: string; description?: string; color: string; documentCount: number; createdAt: string; updatedAt: string }>>('/api/workspaces'),
    create: (data: { name: string; description?: string; color?: string }) =>
      fetchApi<{ id: string; name: string; description?: string; color: string; documentCount: number }>('/api/workspaces', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: { name: string; description?: string; color?: string }) =>
      fetchApi<{ id: string; name: string; description?: string; color: string }>(`/api/workspaces/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => fetchApi<{ success: boolean }>(`/api/workspaces/${id}`, { method: 'DELETE' }),
    join: (id: string) => fetchApi<{ id: string; name: string; member: boolean }>(`/api/shares/workspace/${id}/join`, { method: 'POST' }),
    members: (id: string) => fetchApi<{ ownerId: string; memberIds: string[] }>(`/api/workspaces/${id}/members`),
  },

  shares: {
    chat: (token: string) => fetchApi<{ id: string; title: string; ownerId: string; messages: Array<{ role: string; content: string; agentId?: string }>; createdAt: string; updatedAt: string }>(`/api/shares/chat/${token}`),
  },

  drive: {
    listFiles: (accessToken: string, refreshToken?: string) =>
      fetchApi<{ files: Array<{ id: string; name: string; mimeType: string; size: number; modifiedTime: string; webViewLink: string; isFolder: boolean }>; total: number }>(
        '/api/drive/files',
        { headers: mkheaders(accessToken, refreshToken) },
      ),
    uploadToDrive: (file: File, accessToken: string, refreshToken?: string, folderId?: string, onProgress?: (progress: number) => void) => {
      const formData = new FormData()
      formData.append('file', file)
      const params = new URLSearchParams()
      if (folderId) params.append('folder_id', folderId)
      const query = params.toString()
      return xhrUploadWithRetry<{ id: string; name: string }>(
        `${BACKEND_URL}/api/drive/upload${query ? `?${query}` : ''}`,
        formData,
        onProgress,
        mkheaders(accessToken, refreshToken),
      )
    },
    deleteFile: (fileId: string, accessToken: string, refreshToken?: string) =>
      fetchApi<{ success: boolean }>(
        `/api/drive/files/${fileId}`,
        { method: 'DELETE', headers: mkheaders(accessToken, refreshToken) },
      ),
    getStorage: (accessToken: string, refreshToken?: string) =>
      fetchApi<{ limit: number; usage: number; usageInDrive: number; usageInDriveTrash: number }>(
        '/api/drive/storage',
        { headers: mkheaders(accessToken, refreshToken) },
      ),
    createFolder: (name: string, accessToken: string, refreshToken?: string, parentId?: string) => {
      const params = new URLSearchParams({ name })
      if (parentId) params.append('parent_id', parentId)
      return fetchApi<{ id: string; name: string }>(
        `/api/drive/folders?${params.toString()}`,
        { method: 'POST', headers: mkheaders(accessToken, refreshToken) },
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
    query: (query: string, userId?: string, documentIds?: string[], workspaceId?: string) =>
      fetchApi<{
        results: Array<{ id: string; content: string; metadata: Record<string, unknown>; score: number }>
        citations: Array<{ file_name: string; page_number?: number; section?: string; text: string }>
        answer: string
      }>('/api/knowledge/query', {
        method: 'POST',
        body: JSON.stringify({ query, user_id: userId, document_ids: documentIds, workspace_id: workspaceId }),
      }),
    history: () =>
      fetchApi<Array<{ id: string; query: string; answer: string; createdAt: string }>>('/api/knowledge/history'),
    deleteHistory: (id: string) =>
      fetchApi<{ success: boolean }>(`/api/knowledge/history/${id}`, { method: 'DELETE' }),
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
    deep: (query: string) =>
      fetchApi<{ id: string; query: string; content: string; createdAt: string; stages: Array<{ id: string; label: string; detail: string }>; sources: string[] }>(
        '/api/research/deep', { method: 'POST', body: JSON.stringify({ query }) },
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
      fetchApi<Array<{ id: string; name: string; description: string; icon: string; capabilities?: string[]; tools?: string[]; systemInstruction?: string; custom?: boolean }>>('/api/agents'),
    create: (data: { name: string; description: string; icon: string; system_instruction: string; tools: string[] }) =>
      fetchApi<{ id: string; name: string; description: string; icon: string; tools: string[]; custom: boolean }>('/api/agents', { method: 'POST', body: JSON.stringify(data) }),
    update: (id: string, data: { name: string; description: string; icon: string; system_instruction: string; tools: string[] }) =>
      fetchApi<{ id: string; name: string; description: string; icon: string; tools: string[]; custom: boolean }>(`/api/agents/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
    delete: (id: string) => fetchApi<{ success: boolean }>(`/api/agents/${id}`, { method: 'DELETE' }),
  },
}
