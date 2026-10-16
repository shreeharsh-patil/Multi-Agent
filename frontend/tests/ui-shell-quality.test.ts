import fs from 'node:fs'
import path from 'node:path'
import { describe, expect, it } from 'vitest'

const root = process.cwd()
const source = (relative: string) => fs.readFileSync(path.join(root, relative), 'utf8')

describe('shared UI shell regressions', () => {
  it('keeps mobile zoom enabled for accessibility', () => {
    const layout = source('src/app/layout.tsx')
    expect(layout).not.toContain('userScalable: false')
    expect(layout).not.toContain('maximumScale: 1')
  })

  it('uses shadcn Sheet instead of a hand-rolled mobile dialog', () => {
    const sidebar = source('src/components/sidebar.tsx')
    expect(sidebar).toContain('<Sheet open={mobileMenuOpen}')
    expect(sidebar).not.toContain('mobileDrawerRef')
    expect(sidebar).not.toContain("if (confirm('Delete this conversation?'))")
  })

  it('provides segment error and loading UI', () => {
    expect(source('src/app/error.tsx')).toContain('<Alert variant="destructive">')
    expect(source('src/app/(dashboard)/loading.tsx')).toContain('<Skeleton')
  })

  it('uses a focus-managed dialog for generated image previews', () => {
    const preview = source('src/components/image-preview-card.tsx')
    expect(preview).toContain('<Dialog open={isOpen}')
    expect(preview).not.toContain('fixed inset-0 z-50 flex h-screen')
  })
})
