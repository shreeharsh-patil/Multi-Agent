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

  drive: {
    listFiles: (accessToken: string) =>
      fetchApi<{ files: Array<{ id: string; name: string; mimeType: string; size: number; modifiedTime: string; webViewLink: string; isFolder: boolean }>; total: number }>(
        `/api/drive/files?access_token=${encodeURIComponent(accessToken)}`,
      ),
    uploadToDrive: (file: File, accessToken: string, folderId?: string) => {
      const formData = new FormData()
      formData.append('file', file)
      const params = new URLSearchParams({ access_token: accessToken })
      if (folderId) params.append('folder_id', folderId)
      return fetchApi<{ id: string; name: string }>(
        `/api/drive/upload?${params.toString()}`,
        { method: 'POST', body: formData },
      )
    },
    deleteFile: (fileId: string, accessToken: string) =>
      fetchApi<{ success: boolean }>(
        `/api/drive/files/${fileId}?access_token=${encodeURIComponent(accessToken)}`,
        { method: 'DELETE' },
      ),
    getStorage: (accessToken: string) =>
      fetchApi<{ limit: number; usage: number; usageInDrive: number; usageInDriveTrash: number }>(
        `/api/drive/storage?access_token=${encodeURIComponent(accessToken)}`,
      ),
    createFolder: (name: string, accessToken: string, parentId?: string) => {
      const params = new URLSearchParams({ name, access_token: accessToken })
      if (parentId) params.append('parent_id', parentId)
      return fetchApi<{ id: string; name: string }>(
        `/api/drive/folders?${params.toString()}`,
        { method: 'POST' },
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

  agents: {
    list: () =>
      fetchApi<Array<{ id: string; name: string; description: string }>>('/api/agents'),
  },
}
