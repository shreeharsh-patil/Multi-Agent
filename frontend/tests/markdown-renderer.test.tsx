import { renderToStaticMarkup } from 'react-dom/server'
import { describe, it, expect } from 'vitest'
import { MarkdownRenderer } from '@/components/markdown-renderer'

describe('MarkdownRenderer (XSS regression)', () => {
  it('does not emit executable raw html from AI output', () => {
    const payload = '<img src=x onerror="alert(1)"> <svg onload="evil()"></svg><script>alert(1)</script>'
    const html = renderToStaticMarkup(
      <MarkdownRenderer content={'before ' + payload + ' after'} />,
    )
    // Raw HTML must be escaped into inert text, never created as real elements.
    expect(html).not.toMatch(/<img/i)
    expect(html).not.toMatch(/<svg/i)
    expect(html).not.toMatch(/<script/i)
    // The payload appears only as HTML-escaped text (no executable tag/attr).
    expect(html).toContain('&lt;img')
    // No real attribute with a JS handler is produced on any element.
    expect(html).not.toMatch(/<[a-z:\-]+\s[^>]*onerror\s*=/i)
    expect(html).not.toMatch(/<[a-z:\-]+\s[^>]*onload\s*=/i)
  })

  it('renders plain markdown still (table/headings survive)', () => {
    const html = renderToStaticMarkup(
      <MarkdownRenderer content={'## Title\n\n**bold** and *italic*\n\n|a|b|\n|-|-|\n|1|2|'} />,
    )
    expect(html).toContain('Title')
    expect(html).toContain('<table')
  })
})