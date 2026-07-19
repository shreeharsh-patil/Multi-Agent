'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { Clock3, Copy, FilePlus2, History, Play, RotateCcw, Save, Search, Trash2 } from 'lucide-react'
import { api, type PromptTemplateInfo } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'

const emptyDraft = { name: '', description: '', category: 'General', tags: '', content: '', changeNote: '' }

export default function TemplatesPage() {
  const router = useRouter()
  const [templates, setTemplates] = useState<PromptTemplateInfo[]>([])
  const [selected, setSelected] = useState<PromptTemplateInfo | null>(null)
  const [draft, setDraft] = useState(emptyDraft)
  const [query, setQuery] = useState('')
  const [variableValues, setVariableValues] = useState<Record<string, string>>({})
  const [showVersions, setShowVersions] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    const response = await api.templates.list()
    if (response.success && response.data) setTemplates(response.data)
    else setError(response.error || 'Could not load templates')
  }, [])

  useEffect(() => { refresh() }, [refresh])

  const selectTemplate = async (template: PromptTemplateInfo) => {
    const response = await api.templates.get(template.id)
    if (!response.success || !response.data) return setError(response.error || 'Could not load template')
    const value = response.data
    setSelected(value)
    setDraft({ name: value.name, description: value.description, category: value.category, tags: value.tags.join(', '), content: value.content, changeNote: '' })
    setVariableValues(Object.fromEntries(value.variables.map((variable) => [variable, ''])))
    setShowVersions(false)
  }

  const createNew = () => {
    setSelected(null)
    setDraft(emptyDraft)
    setVariableValues({})
    setShowVersions(false)
  }

  const save = async () => {
    if (!draft.name.trim() || !draft.content.trim()) return
    setBusy(true)
    const data = {
      name: draft.name, description: draft.description, category: draft.category,
      tags: draft.tags.split(',').map((tag) => tag.trim()).filter(Boolean), content: draft.content,
      change_note: draft.changeNote || (selected ? 'Updated prompt' : 'Initial version'),
    }
    const response = selected ? await api.templates.update(selected.id, data) : await api.templates.create(data)
    if (response.success && response.data) {
      await refresh()
      await selectTemplate(response.data)
    } else setError(response.error || 'Could not save template')
    setBusy(false)
  }

  const restore = async (version: number) => {
    if (!selected) return
    setBusy(true)
    const response = await api.templates.restore(selected.id, version)
    if (response.success && response.data) {
      await refresh()
      await selectTemplate(response.data)
      setShowVersions(true)
    } else setError(response.error || 'Could not restore version')
    setBusy(false)
  }

  const useInChat = async () => {
    if (!selected) return
    const response = await api.templates.render(selected.id, variableValues)
    if (!response.success || !response.data) return setError(response.error || 'Complete every template variable')
    sessionStorage.setItem('chat-template-draft', response.data.content)
    router.push('/chat')
  }

  const visibleTemplates = templates.filter((template) => `${template.name} ${template.description} ${template.category} ${template.tags.join(' ')}`.toLowerCase().includes(query.toLowerCase()))

  return (
    <div className="mx-auto flex h-full max-w-[1400px] flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
        <div><h1 className="text-2xl font-normal text-foreground">Prompt library</h1><p className="mt-1 text-sm text-muted-foreground">Reusable prompts with variables and an immutable edit history.</p></div>
        <Button onClick={createNew}><FilePlus2 className="mr-2 h-4 w-4" />New template</Button>
      </header>
      {error ? <div className="flex items-center justify-between border-l-2 border-red-500 bg-red-50 px-3 py-2 text-sm text-red-700"><span>{error}</span><button onClick={() => setError(null)}>Dismiss</button></div> : null}
      <div className="grid min-h-0 flex-1 overflow-hidden border border-border bg-card lg:grid-cols-[280px_minmax(0,1fr)_300px]">
        <aside className="flex min-h-0 flex-col border-b border-border bg-secondary/40 lg:border-b-0 lg:border-r">
          <div className="relative border-b border-border p-3"><Search className="absolute left-5 top-5 h-3.5 w-3.5 text-muted-foreground" /><Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Find a template" className="h-8 pl-8 text-xs" /></div>
          <div className="min-h-0 flex-1 overflow-y-auto p-2">{visibleTemplates.length === 0 ? <p className="p-3 text-xs text-muted-foreground">No matching templates.</p> : visibleTemplates.map((template) => <button key={template.id} onClick={() => selectTemplate(template)} className={`mb-1 w-full rounded-[6px] px-3 py-2.5 text-left ${selected?.id === template.id ? 'bg-card shadow-xs' : 'hover:bg-card/60'}`}><span className="block truncate text-sm font-medium">{template.name}</span><span className="mt-1 flex items-center justify-between text-[10px] text-muted-foreground"><span>{template.category}</span><span>v{template.currentVersion}</span></span></button>)}</div>
        </aside>

        <main className="min-h-0 overflow-y-auto p-4 sm:p-6">
          <div className="mx-auto max-w-3xl">
            <div className="grid gap-3 sm:grid-cols-[1fr_180px]"><label className="text-xs font-medium text-muted-foreground">Name<Input value={draft.name} onChange={(event) => setDraft((current) => ({ ...current, name: event.target.value }))} className="mt-1.5 text-foreground" placeholder="Research brief" /></label><label className="text-xs font-medium text-muted-foreground">Category<Input value={draft.category} onChange={(event) => setDraft((current) => ({ ...current, category: event.target.value }))} className="mt-1.5 text-foreground" /></label></div>
            <label className="mt-3 block text-xs font-medium text-muted-foreground">Description<Input value={draft.description} onChange={(event) => setDraft((current) => ({ ...current, description: event.target.value }))} className="mt-1.5 text-foreground" placeholder="When should this prompt be used?" /></label>
            <label className="mt-3 block text-xs font-medium text-muted-foreground">Prompt<Textarea value={draft.content} onChange={(event) => setDraft((current) => ({ ...current, content: event.target.value }))} className="mt-1.5 min-h-[300px] resize-y font-mono text-[13px] leading-relaxed text-foreground" placeholder={'Analyze {{topic}} for {{audience}}.\n\nReturn...'} /></label>
            <p className="mt-2 text-[11px] text-muted-foreground">Variables use double braces, for example {'{{topic}}'}.</p>
            <div className="mt-3 grid gap-3 sm:grid-cols-2"><label className="text-xs font-medium text-muted-foreground">Tags<Input value={draft.tags} onChange={(event) => setDraft((current) => ({ ...current, tags: event.target.value }))} className="mt-1.5 text-foreground" placeholder="research, reports" /></label><label className="text-xs font-medium text-muted-foreground">Version note<Input value={draft.changeNote} onChange={(event) => setDraft((current) => ({ ...current, changeNote: event.target.value }))} className="mt-1.5 text-foreground" placeholder="What changed?" /></label></div>
            <div className="mt-5 flex flex-wrap justify-between gap-2"><div className="flex gap-2">{selected ? <Button variant="outline" onClick={() => setShowVersions((current) => !current)}><History className="mr-2 h-4 w-4" />{selected.currentVersion} versions</Button> : null}{selected ? <Button variant="ghost" size="icon" title="Delete template" onClick={async () => { if (confirm('Delete this template?')) { await api.templates.delete(selected.id); createNew(); await refresh() } }}><Trash2 className="h-4 w-4 text-red-600" /></Button> : null}</div><Button onClick={save} disabled={busy || !draft.name.trim() || !draft.content.trim()}><Save className="mr-2 h-4 w-4" />{busy ? 'Saving...' : selected ? 'Save new version' : 'Create template'}</Button></div>

            {showVersions && selected?.versions ? <div className="mt-6 border-t border-border pt-5"><h2 className="text-sm font-medium">Version history</h2><div className="mt-3 space-y-0">{selected.versions.map((version) => <div key={version.version} className="flex gap-3 border-l border-border pb-5 pl-4 last:pb-0"><div className="min-w-0 flex-1"><div className="flex items-center gap-2"><Badge variant="outline" className="rounded-[4px]">v{version.version}</Badge>{version.version === selected.currentVersion ? <span className="text-[10px] text-[#1f8a65]">Current</span> : null}</div><p className="mt-2 text-xs">{version.changeNote || 'No change note'}</p><p className="mt-1 text-[10px] text-muted-foreground">{new Date(version.createdAt).toLocaleString()}</p></div>{version.version !== selected.currentVersion ? <Button variant="ghost" size="sm" onClick={() => restore(version.version)}><RotateCcw className="mr-1.5 h-3.5 w-3.5" />Restore</Button> : null}</div>)}</div></div> : null}
          </div>
        </main>

        <aside className="min-h-0 overflow-y-auto border-t border-border bg-secondary/20 p-4 lg:border-l lg:border-t-0">
          <div className="flex items-center gap-2"><Play className="h-4 w-4 text-[#1f8a65]" /><h2 className="text-sm font-medium">Run template</h2></div>
          {!selected ? <p className="mt-4 text-xs leading-relaxed text-muted-foreground">Save or select a template to fill its variables and open it in chat.</p> : <><div className="mt-4 space-y-3">{selected.variables.length ? selected.variables.map((variable) => <label key={variable} className="block text-xs font-medium text-muted-foreground">{variable}<Input value={variableValues[variable] || ''} onChange={(event) => setVariableValues((current) => ({ ...current, [variable]: event.target.value }))} className="mt-1.5 bg-card text-foreground" /></label>) : <p className="text-xs text-muted-foreground">This template has no variables.</p>}</div><Button className="mt-5 w-full" onClick={useInChat}><Play className="mr-2 h-4 w-4" />Use in chat</Button><Button variant="outline" className="mt-2 w-full" onClick={() => navigator.clipboard.writeText(selected.content)}><Copy className="mr-2 h-4 w-4" />Copy prompt</Button><div className="mt-6 border-t border-border pt-4 text-[10px] leading-relaxed text-muted-foreground"><p className="flex items-center gap-1.5"><Clock3 className="h-3 w-3" />Updated {new Date(selected.updatedAt).toLocaleDateString()}</p><p className="mt-2">Every save creates a new version. Restoring never removes later history.</p></div></>}
        </aside>
      </div>
    </div>
  )
}
