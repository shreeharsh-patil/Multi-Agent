import { renderToStaticMarkup } from 'react-dom/server'
import { describe, it, expect } from 'vitest'
import { MarkdownRenderer } from '@/components/markdown-renderer'

describe('MarkdownRenderer (XSS regression)', () => {
  it('does not emit executable attributes from raw HTML in AI output', () => {
    const payload = '<img src=x onerror="alert(1)"> hello <svg onload="evil()"></svg>'
    const html = renderToStaticMarkup(
      <MarkdownRenderer content={'before ' + payload + ' after'} />,
    )
    expect(html).not.toContain('onerror')
    expect(html).not.toContain('onload')
    expect(html).not.toContain('<script')
  })

  it('renders plain markdown still (table/headings survive)', () => {
    const html = renderToStaticMarkup(
      <MarkdownRenderer content={'## Title\n\n**bold** and *italic*\n\n|a|b|\n|-|-|\n|1|2|'} />,
    )
    expect(html).toContain('Title')
    expect(html).toContain('<table')
  })
})