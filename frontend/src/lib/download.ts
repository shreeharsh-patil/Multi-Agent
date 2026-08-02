import { getAccessToken } from '@/lib/auth-store';

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000';

/**
 * Downloads a file securely via fetch blob without exposing the backend URL
 * or redirecting the browser away from the application.
 */
export async function downloadSecureFile(url: string, fileName?: string): Promise<void> {
  let targetUrl = url.startsWith('/api/') ? `${BACKEND_URL}${url}` : url;
  if (targetUrl.includes('/api/documents/') && targetUrl.includes('/download') && !targetUrl.includes('download=true')) {
    targetUrl += targetUrl.includes('?') ? '&download=true' : '?download=true';
  }

  try {
    const token = getAccessToken();
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const res = await fetch(targetUrl, { headers });
    if (!res.ok) {
      throw new Error(`Download failed with status ${res.status}`);
    }

    const blob = await res.blob();
    const blobUrl = window.URL.createObjectURL(blob);

    // Extract filename from response headers or fallback
    let suggestedName = fileName;
    const disposition = res.headers.get('Content-Disposition');
    if (!suggestedName && disposition && disposition.includes('filename=')) {
      const match = disposition.match(/filename="?([^";]+)"?/);
      if (match && match[1]) {
        suggestedName = match[1];
      }
    }
    if (!suggestedName) {
      suggestedName = `document-${Date.now()}`;
    }

    const a = document.createElement('a');
    a.href = blobUrl;
    a.download = suggestedName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    setTimeout(() => {
      window.URL.revokeObjectURL(blobUrl);
    }, 1000);
  } catch (err) {
    console.error('Secure download failed:', err);
    const a = document.createElement('a');
    a.href = targetUrl;
    if (fileName) a.download = fileName;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  }
}
