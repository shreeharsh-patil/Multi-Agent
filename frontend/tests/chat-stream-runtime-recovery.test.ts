import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const source = fs.readFileSync(
  path.join(process.cwd(), 'src/app/(dashboard)/chat/page.tsx'),
  'utf8',
)

describe('chat stream runtime recovery', () => {
  it('does not overwrite the assistant bubble immediately on an SSE error marker', () => {
    const errorBranch = source.split("currentEvent === 'error'")[1]?.split('}\n          } catch')[0] || ''
    expect(errorBranch).toContain('streamServerError = String(data.error)')
    expect(errorBranch).not.toContain('content: `Error: ${data.error}`')
  })

  it('lets a completed non-empty fallback clear a prior stream error', () => {
    expect(source).toContain("if (accumulatedContent.trim()) streamServerError = ''")
    expect(source).toContain("throw new Error(streamServerError || 'The model returned an empty response.')")
  })

  it('shows the server-friendly error with the request id when recovery is impossible', () => {
    expect(source).toContain("content: accumulatedContent || `${errorMessage || 'Unable to generate a response. Please retry.'}")
  })
})
