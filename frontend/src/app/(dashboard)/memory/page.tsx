'use client'

import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  BrainCircuit,
  Check,
  ChevronRight,
  CircleGauge,
  Edit3,
  Loader2,
  Pin,
  Plus,
  Search,
  Sparkles,
  Trash2,
  X,
  Shrink,
} from 'lucide-react'
import { toast } from 'sonner'

import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { api, type MemoryDashboard, type MemoryItem } from '@/lib/api'
import { cn } from '@/lib/utils'

const LABELS: Record<string, string> = {
  all: 'All memories',
  communication: 'Communication',
  work_style: 'Work style',
  interests: 'Interests',
  goals: 'Goals',
  constraints: 'Constraints',
  personal: 'Personal',
  general: 'General',
}

const CATEGORY_COLOR: Record<string, string> = {
  communication: 'bg-[#dff3ed] text-[#176d55]',
  work_style: 'bg-[#e8eef9] text-[#355b90]',
  interests: 'bg-[#f2e9f7] text-[#765187]',
  goals: 'bg-[#fff0d6] text-[#8a5b12]',
  constraints: 'bg-[#f9e5e5] text-[#934242]',
  personal: 'bg-[#e8f0e2] text-[#55713f]',
  general: 'bg-[#ecebe7] text-[#5a5852]',
}

function relativeDate(value: string) {
  const timestamp = new Date(value).getTime()
  if (Number.isNaN(timestamp)) return 'Unknown date'
  const days = Math.floor((Date.now() - timestamp) / 86_400_000)
  if (days <= 0) return 'Today'
  if (days === 1) return 'Yesterday'
  if (days < 30) return `${days} days ago`
  return new Intl.DateTimeFormat('en', { month: 'short', day: 'numeric' }).format(new Date(value))
}

export default function MemoryPage() {
  const [data, setData] = useState<MemoryDashboard | null>(null)
  const [loading, setLoading] = useState(true)
  const [category, setCategory] = useState('all')
  const [query, setQuery] = useState('')
  const [editing, setEditing] = useState<MemoryItem | null>(null)
  const [draft, setDraft] = useState('')
  const [addOpen, setAddOpen] = useState(false)
  const [newContent, setNewContent] = useState('')
  const [newCategory, setNewCategory] = useState('general')
  const [saving, setSaving] = useState(false)
  const [clearConfirm, setClearConfirm] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    const response = await api.memory.dashboard(category, query.trim())
    if (response.success && response.data) setData(response.data)
    else toast.error(response.error || 'Could not load memory')
    setLoading(false)
  }, [category, query])

  useEffect(() => {
    const timeout = window.setTimeout(load, query ? 250 : 0)
    return () => window.clearTimeout(timeout)
  }, [load, query])

  const categories = useMemo(() => ['all', ...(data?.categories ?? Object.keys(LABELS).slice(1))], [data])

  async function setPreference(key: 'enabled' | 'autoExtract', value: boolean) {
    if (!data) return
    const previous = data.settings
    const settings = { ...previous, [key]: value }
    setData({ ...data, settings })
    const response = await api.memory.settings({ [key]: value })
    if (!response.success) {
      setData({ ...data, settings: previous })
      toast.error(response.error || 'Could not save memory settings')
    }
  }

  async function updateItem(id: string, changes: Parameters<typeof api.memory.update>[1]) {
    const response = await api.memory.update(id, changes)
    if (!response.success) {
      toast.error(response.error || 'Could not update memory')
      return false
    }
    await load()
    return true
  }

  async function saveEdit() {
    if (!editing || draft.trim().length < 2) return
    setSaving(true)
    if (await updateItem(editing.id, { content: draft.trim() })) setEditing(null)
    setSaving(false)
  }

  async function addMemory() {
    if (newContent.trim().length < 2) return
    setSaving(true)
    const response = await api.memory.create({ content: newContent.trim(), category: newCategory })
    if (response.success) {
      setNewContent('')
      setNewCategory('general')
      setAddOpen(false)
      toast.success('Memory added')
      await load()
    } else toast.error(response.error || 'Could not add memory')
    setSaving(false)
  }

  async function removeItem(item: MemoryItem) {
    const response = await api.memory.delete(item.id)
    if (response.success) {
      toast.success('Memory deleted')
      await load()
    } else toast.error(response.error || 'Could not delete memory')
  }

  async function clearAll() {
    setSaving(true)
    const response = await api.memory.clear()
    if (response.success) {
      toast.success(`${response.data?.deleted ?? 0} memories deleted`)
      setClearConfirm(false)
      await load()
    } else toast.error(response.error || 'Could not clear memory')
    setSaving(false)
  }

  async function consolidate() {
    setSaving(true)
    const response = await api.memory.consolidate()
    if (response.success) {
      if (response.data?.archived) {
        toast.success(response.data.message || `Archived ${response.data.archived} memories`)
      } else {
        toast.info(response.data?.message || 'Nothing to consolidate yet')
      }
      await load()
    } else toast.error(response.error || 'Could not consolidate memory')
    setSaving(false)
  }

  return (
    <div className="mx-auto w-full min-w-0 max-w-6xl pb-14 animate-fade-in">
      <header className="flex flex-col gap-4 border-b border-border pb-6 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="mb-2 flex items-center gap-2 text-xs font-semibold uppercase text-primary">
            <BrainCircuit className="h-4 w-4" /> Semantic memory
          </div>
          <h1 className="text-2xl text-foreground sm:text-3xl">What your agents know about you</h1>
          <p className="mt-2 max-w-2xl text-sm text-muted-foreground">
            Review the durable preferences and context used to personalize future conversations.
          </p>
        </div>
        <div className="flex w-full flex-wrap items-center gap-2 self-start sm:w-auto sm:self-auto">
          <Button variant="outline" onClick={consolidate} disabled={saving} className="gap-2">
            <Shrink className="h-4 w-4" /> Consolidate
          </Button>
          <Button onClick={() => setAddOpen(true)} className="gap-2">
            <Plus className="h-4 w-4" /> Add memory
          </Button>
        </div>
      </header>

      <div className="grid gap-8 pt-7 lg:grid-cols-[240px_minmax(0,1fr)]">
        <aside className="space-y-7 lg:sticky lg:top-0 lg:self-start">
          <section>
            <p className="mb-3 text-[11px] font-semibold uppercase text-muted-foreground">Profile signal</p>
            <div className="flex items-center gap-4">
              <div
                className="grid h-16 w-16 shrink-0 place-items-center rounded-full"
                style={{ background: `conic-gradient(#f54e00 ${data?.profile.completeness ?? 0}%, #e6e5e0 0)` }}
              >
                <div className="grid h-12 w-12 place-items-center rounded-full bg-background">
                  <span className="text-sm font-semibold">{data?.profile.completeness ?? 0}%</span>
                </div>
              </div>
              <div>
                <p className="text-2xl font-medium">{data?.profile.memoryCount ?? 0}</p>
                <p className="text-xs text-muted-foreground">active memories</p>
              </div>
            </div>
          </section>

          <nav aria-label="Memory categories" className="space-y-1">
            {categories.map((item) => {
              const count = item === 'all'
                ? data?.profile.memoryCount
                : data?.profile.categories[item]?.length
              return (
                <button
                  key={item}
                  onClick={() => setCategory(item)}
                  className={cn(
                    'flex h-9 w-full items-center justify-between rounded-[6px] px-2.5 text-left text-xs transition-colors',
                    category === item ? 'bg-card font-semibold text-foreground shadow-xs' : 'text-muted-foreground hover:bg-card/60',
                  )}
                >
                  <span>{LABELS[item] ?? item}</span>
                  <span className="tabular-nums">{count ?? 0}</span>
                </button>
              )
            })}
          </nav>

          <section className="space-y-4 border-t border-border pt-5">
            <div className="flex items-center justify-between gap-3">
              <div>
                <Label htmlFor="memory-enabled" className="text-xs">Use memory</Label>
                <p className="mt-0.5 text-[11px] text-muted-foreground">Personalize agent replies</p>
              </div>
              <Switch id="memory-enabled" checked={data?.settings.enabled ?? false} onCheckedChange={(v) => setPreference('enabled', v)} />
            </div>
            <div className="flex items-center justify-between gap-3">
              <div>
                <Label htmlFor="auto-extract" className="text-xs">Learn automatically</Label>
                <p className="mt-0.5 text-[11px] text-muted-foreground">Extract durable context</p>
              </div>
              <Switch id="auto-extract" disabled={!data?.settings.enabled} checked={data?.settings.autoExtract ?? false} onCheckedChange={(v) => setPreference('autoExtract', v)} />
            </div>
          </section>
        </aside>

        <main className="min-w-0">
          {data?.profile.summary.length ? (
            <section className="mb-8 border-l-2 border-primary pl-5">
              <div className="mb-3 flex items-center gap-2 text-xs font-semibold text-foreground">
                <Sparkles className="h-4 w-4 text-primary" /> Persona snapshot
              </div>
              <p className="max-w-3xl text-base leading-7 text-foreground">
                {data.profile.summary.slice(0, 3).join(' ')}
              </p>
            </section>
          ) : null}

          <div className="mb-4 flex items-center gap-3">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search what your agents remember" className="pl-9" />
            </div>
            {query ? <Button variant="ghost" size="icon" title="Clear search" onClick={() => setQuery('')}><X className="h-4 w-4" /></Button> : null}
          </div>

          {loading ? (
            <div className="grid h-56 place-items-center"><Loader2 className="h-6 w-6 animate-spin text-primary" /></div>
          ) : data?.items.length ? (
            <div className="divide-y divide-border border-y border-border">
              {data.items.map((item) => (
                <article key={item.id} className="group py-5">
                  <div className="flex items-start gap-4">
                    <div className="mt-1 h-2 w-2 shrink-0 rounded-full bg-primary" />
                    <div className="min-w-0 flex-1">
                      <div className="mb-2 flex flex-wrap items-center gap-2">
                        <span className={cn('rounded-[4px] px-2 py-0.5 text-[10px] font-semibold', CATEGORY_COLOR[item.category] ?? CATEGORY_COLOR.general)}>
                          {LABELS[item.category] ?? item.category}
                        </span>
                        <span className="flex items-center gap-1 text-[10px] text-muted-foreground">
                          <CircleGauge className="h-3 w-3" /> {Math.round(item.confidence * 100)}% confidence
                        </span>
                        <span className="text-[10px] text-muted-foreground">{relativeDate(item.updatedAt)}</span>
                      </div>
                      {editing?.id === item.id ? (
                        <div className="space-y-3">
                          <Textarea value={draft} onChange={(event) => setDraft(event.target.value)} className="min-h-20" autoFocus />
                          <div className="flex gap-2">
                            <Button size="sm" onClick={saveEdit} disabled={saving || draft.trim().length < 2}><Check className="mr-1.5 h-3.5 w-3.5" /> Save</Button>
                            <Button size="sm" variant="ghost" onClick={() => setEditing(null)}>Cancel</Button>
                          </div>
                        </div>
                      ) : (
                        <>
                          <p className="text-sm leading-6 text-foreground">{item.content}</p>
                          {item.evidence ? <p className="mt-2 truncate text-xs text-muted-foreground">Evidence: “{item.evidence}”</p> : null}
                        </>
                      )}
                    </div>
                    <div className="flex shrink-0 items-center opacity-60 transition-opacity group-hover:opacity-100 group-focus-within:opacity-100">
                      <Button variant="ghost" size="icon" title={item.pinned ? 'Unpin memory' : 'Pin memory'} onClick={() => updateItem(item.id, { pinned: !item.pinned })}>
                        <Pin className={cn('h-4 w-4', item.pinned && 'fill-primary text-primary')} />
                      </Button>
                      <Button variant="ghost" size="icon" title="Edit memory" onClick={() => { setEditing(item); setDraft(item.content) }}><Edit3 className="h-4 w-4" /></Button>
                      <Button variant="ghost" size="icon" title="Delete memory" className="text-destructive hover:text-destructive" onClick={() => removeItem(item)}><Trash2 className="h-4 w-4" /></Button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="border-y border-border py-16 text-center">
              <BrainCircuit className="mx-auto mb-4 h-8 w-8 text-muted-foreground" />
              <h2 className="text-base">No memories here yet</h2>
              <p className="mx-auto mt-2 max-w-sm text-sm text-muted-foreground">
                Add a durable preference now, or keep chatting with automatic learning enabled.
              </p>
              <Button variant="outline" className="mt-5 gap-2" onClick={() => setAddOpen(true)}><Plus className="h-4 w-4" /> Add the first memory</Button>
            </div>
          )}

          {data?.profile.memoryCount ? (
            <div className="mt-8 flex items-center justify-between border-t border-border pt-5">
              <p className="text-xs text-muted-foreground">Deleting memory is permanent and removes its vector index.</p>
              {clearConfirm ? (
                <div className="flex items-center gap-2">
                  <Button size="sm" variant="destructive" onClick={clearAll} disabled={saving}>Delete all</Button>
                  <Button size="sm" variant="ghost" onClick={() => setClearConfirm(false)}>Cancel</Button>
                </div>
              ) : <Button size="sm" variant="ghost" className="text-destructive hover:text-destructive" onClick={() => setClearConfirm(true)}>Clear memory</Button>}
            </div>
          ) : null}
        </main>
      </div>

      {addOpen ? (
        <div className="fixed inset-0 z-50 grid place-items-center bg-black/30 p-3 sm:p-4" role="dialog" aria-modal="true" aria-labelledby="add-memory-title" onMouseDown={(event) => { if (event.target === event.currentTarget) setAddOpen(false) }}>
          <div className="max-h-[calc(100dvh-1.5rem)] w-full max-w-lg overflow-y-auto rounded-[8px] border border-border bg-card p-4 shadow-xl sm:p-6">
            <div className="mb-5 flex items-start justify-between">
              <div>
                <h2 id="add-memory-title" className="text-lg">Add a memory</h2>
                <p className="mt-1 text-sm text-muted-foreground">Write one durable fact or preference.</p>
              </div>
              <Button variant="ghost" size="icon" title="Close" onClick={() => setAddOpen(false)}><X className="h-4 w-4" /></Button>
            </div>
            <div className="space-y-5">
              <div className="space-y-2">
                <Label htmlFor="memory-content">What should your agents remember?</Label>
                <Textarea id="memory-content" value={newContent} onChange={(event) => setNewContent(event.target.value)} placeholder="I prefer concise answers with concrete examples." className="min-h-28" autoFocus />
              </div>
              <div className="space-y-2">
                <Label htmlFor="memory-category">Category</Label>
                <select id="memory-category" value={newCategory} onChange={(event) => setNewCategory(event.target.value)} className="h-10 w-full rounded-[6px] border border-input bg-background px-3 text-sm focus:outline-none focus:ring-2 focus:ring-ring">
                  {Object.entries(LABELS).filter(([key]) => key !== 'all').map(([key, label]) => <option key={key} value={key}>{label}</option>)}
                </select>
              </div>
              <div className="flex justify-end gap-2">
                <Button variant="outline" onClick={() => setAddOpen(false)}>Cancel</Button>
                <Button onClick={addMemory} disabled={saving || newContent.trim().length < 2}>{saving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ChevronRight className="mr-2 h-4 w-4" />}Add memory</Button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  )
}
