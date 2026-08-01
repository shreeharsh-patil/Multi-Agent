'use client'

import { useCallback, useEffect, useState } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import { preprocessLaTeX } from '@/lib/latex'
import { Brain, Check, ChevronRight, Plus, RotateCcw, Sparkles, Trash2 } from 'lucide-react'
import { api, type FlashcardDeckInfo, type FlashcardInfo } from '@/lib/api'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'

type View = 'cards' | 'review' | 'generate'

const ratings = [
  { id: 'again' as const, label: 'Again', detail: '10 min', className: 'border-red-200 text-red-700 hover:bg-red-50' },
  { id: 'hard' as const, label: 'Hard', detail: '1 day', className: 'border-amber-200 text-amber-700 hover:bg-amber-50' },
  { id: 'good' as const, label: 'Good', detail: 'Normal', className: 'border-emerald-200 text-emerald-700 hover:bg-emerald-50' },
  { id: 'easy' as const, label: 'Easy', detail: 'Longer', className: 'border-sky-200 text-sky-700 hover:bg-sky-50' },
]

export default function FlashcardsPage() {
  const [decks, setDecks] = useState<FlashcardDeckInfo[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [cards, setCards] = useState<FlashcardInfo[]>([])
  const [due, setDue] = useState<FlashcardInfo[]>([])
  const [view, setView] = useState<View>('cards')
  const [revealed, setRevealed] = useState(false)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [deckDraft, setDeckDraft] = useState('')
  const [cardDraft, setCardDraft] = useState({ front: '', back: '', tags: '' })
  const [source, setSource] = useState('')

  const refreshDecks = useCallback(async () => {
    const response = await api.flashcards.decks()
    if (response.success && response.data) {
      setDecks(response.data)
      setSelectedId((current) => current || response.data![0]?.id || null)
    } else setError(response.error || 'Could not load decks')
    setLoading(false)
  }, [])

  const refreshCards = useCallback(async (deckId: string) => {
    const [cardsResponse, dueResponse] = await Promise.all([api.flashcards.cards(deckId), api.flashcards.due(deckId)])
    if (cardsResponse.success && cardsResponse.data) setCards(cardsResponse.data)
    if (dueResponse.success && dueResponse.data) setDue(dueResponse.data)
  }, [])

  useEffect(() => { refreshDecks() }, [refreshDecks])
  useEffect(() => { if (selectedId) refreshCards(selectedId) }, [selectedId, refreshCards])

  const createDeck = async () => {
    if (!deckDraft.trim()) return
    setBusy(true)
    const response = await api.flashcards.createDeck({ name: deckDraft.trim() })
    if (response.success && response.data) {
      setDeckDraft('')
      await refreshDecks()
      setSelectedId(response.data.id)
    } else setError(response.error || 'Could not create deck')
    setBusy(false)
  }

  const createCard = async () => {
    if (!selectedId || !cardDraft.front.trim() || !cardDraft.back.trim()) return
    setBusy(true)
    const response = await api.flashcards.createCard(selectedId, {
      front: cardDraft.front, back: cardDraft.back,
      tags: cardDraft.tags.split(',').map((tag) => tag.trim()).filter(Boolean),
    })
    if (response.success) {
      setCardDraft({ front: '', back: '', tags: '' })
      await Promise.all([refreshCards(selectedId), refreshDecks()])
    } else setError(response.error || 'Could not create card')
    setBusy(false)
  }

  const review = async (rating: 'again' | 'hard' | 'good' | 'easy') => {
    const card = due[0]
    if (!card) return
    setBusy(true)
    const response = await api.flashcards.review(card.id, rating)
    if (response.success) {
      setDue((current) => current.slice(1))
      setRevealed(false)
      await refreshDecks()
    } else setError(response.error || 'Review was not saved')
    setBusy(false)
  }

  const generate = async () => {
    if (!selectedId || source.trim().length < 10) return
    setBusy(true)
    const response = await api.flashcards.generate(selectedId, source, 10)
    if (response.success) {
      setSource('')
      setView('cards')
      await Promise.all([refreshCards(selectedId), refreshDecks()])
    } else setError(response.error || 'Could not generate cards')
    setBusy(false)
  }

  const selectedDeck = decks.find((deck) => deck.id === selectedId)
  const reviewCard = due[0]

  return (
    <div className="mx-auto flex h-full max-w-[1280px] flex-col gap-5">
      <header className="flex flex-wrap items-end justify-between gap-3 border-b border-border pb-4">
        <div>
          <h1 className="text-2xl font-normal text-foreground">Flashcards</h1>
          <p className="mt-1 text-sm text-muted-foreground">Review what is due, then get back to your work.</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => setView('generate')} disabled={!selectedId}><Sparkles className="mr-2 h-4 w-4" />Generate</Button>
          <Button onClick={() => { setView('review'); setRevealed(false) }} disabled={!due.length}><Brain className="mr-2 h-4 w-4" />Review {due.length || ''}</Button>
        </div>
      </header>

      {error ? <div className="border-l-2 border-red-500 bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div> : null}

      <div className="grid min-h-0 flex-1 gap-0 overflow-hidden border border-border bg-card md:grid-cols-[260px_1fr]">
        <aside className="flex min-h-0 flex-col border-b border-border bg-secondary/40 md:border-b-0 md:border-r">
          <div className="border-b border-border p-3">
            <div className="flex gap-2">
              <Input value={deckDraft} onChange={(event) => setDeckDraft(event.target.value)} onKeyDown={(event) => event.key === 'Enter' && createDeck()} placeholder="New deck" className="h-8 text-xs" />
              <Button size="icon" className="h-8 w-8 shrink-0" onClick={createDeck} disabled={busy || !deckDraft.trim()} title="Create deck"><Plus className="h-4 w-4" /></Button>
            </div>
          </div>
          <div className="min-h-0 flex-1 overflow-y-auto p-2">
            {loading ? <p className="p-3 text-xs text-muted-foreground">Loading decks...</p> : decks.length === 0 ? <p className="p-3 text-xs text-muted-foreground">Create a deck to begin.</p> : decks.map((deck) => (
              <button key={deck.id} onClick={() => { setSelectedId(deck.id); setView('cards') }} className={`mb-1 flex w-full items-center gap-2 rounded-[6px] px-3 py-2.5 text-left ${selectedId === deck.id ? 'bg-card shadow-xs' : 'hover:bg-card/60'}`}>
                <span className="min-w-0 flex-1"><span className="block truncate text-sm font-medium">{deck.name}</span><span className="text-[11px] text-muted-foreground">{deck.cardCount} cards</span></span>
                <span className={`min-w-6 rounded px-1.5 py-0.5 text-center text-[10px] ${deck.dueCount ? 'bg-[#1f8a65] text-white' : 'bg-secondary text-muted-foreground'}`}>{deck.dueCount}</span>
                <ChevronRight className="h-3.5 w-3.5 text-muted-foreground" />
              </button>
            ))}
          </div>
        </aside>

        <main className="min-h-0 overflow-y-auto p-4 sm:p-6">
          {!selectedDeck ? <div className="grid h-full place-items-center text-sm text-muted-foreground">Select or create a deck.</div> : view === 'review' ? (
            <div className="mx-auto flex h-full max-w-3xl flex-col justify-center">
              {reviewCard ? <>
                <div className="mb-3 flex items-center justify-between text-xs text-muted-foreground"><span>{selectedDeck.name}</span><span>{due.length} due</span></div>
                <div className="h-1 overflow-hidden bg-secondary"><div className="h-full bg-[#1f8a65] transition-all" style={{ width: `${Math.max(6, 100 / Math.max(due.length, 1))}%` }} /></div>
                <div className="grid min-h-[340px] place-items-center border-x border-b border-border bg-background p-8 text-center">
                  <div className="max-w-2xl"><div className="prose prose-lg max-w-none prose-headings:font-semibold prose-headings:tracking-normal prose-strong:font-bold prose-em:italic"><ReactMarkdown remarkPlugins={[remarkGfm, [remarkMath, { singleDollar: true }]]} rehypePlugins={[rehypeKatex]}>{preprocessLaTeX(reviewCard.front)}</ReactMarkdown></div>{revealed ? <div className="prose mt-8 max-w-none border-t border-border pt-7 text-muted-foreground prose-headings:font-semibold prose-headings:tracking-normal prose-strong:font-bold prose-em:italic"><ReactMarkdown remarkPlugins={[remarkGfm, [remarkMath, { singleDollar: true }]]} rehypePlugins={[rehypeKatex]}>{preprocessLaTeX(reviewCard.back)}</ReactMarkdown></div> : null}</div>
                </div>
                {!revealed ? <Button className="mt-4 h-11" onClick={() => setRevealed(true)}>Show answer</Button> : <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">{ratings.map((rating) => <button key={rating.id} disabled={busy} onClick={() => review(rating.id)} className={`h-14 rounded-[6px] border bg-card text-sm font-medium transition-colors disabled:opacity-50 ${rating.className}`}><span className="block">{rating.label}</span><span className="text-[10px] font-normal opacity-70">{rating.detail}</span></button>)}</div>}
              </> : <div className="grid place-items-center py-24 text-center"><Check className="mb-3 h-8 w-8 text-[#1f8a65]" /><p className="font-medium">Review complete</p><p className="mt-1 text-sm text-muted-foreground">Nothing else is due in this deck.</p><Button variant="outline" className="mt-5" onClick={() => setView('cards')}>Back to cards</Button></div>}
            </div>
          ) : view === 'generate' ? (
            <div className="mx-auto max-w-3xl"><h2 className="text-lg font-medium">Generate cards with an agent</h2><p className="mt-1 text-sm text-muted-foreground">Paste notes or source material. The agent will create ten focused cards.</p><Textarea value={source} onChange={(event) => setSource(event.target.value)} className="mt-5 min-h-[300px]" placeholder="Paste lecture notes, a report, or study material..." /><div className="mt-3 flex justify-end gap-2"><Button variant="ghost" onClick={() => setView('cards')}>Cancel</Button><Button onClick={generate} disabled={busy || source.trim().length < 10}><Sparkles className="mr-2 h-4 w-4" />{busy ? 'Generating...' : 'Generate 10 cards'}</Button></div></div>
          ) : (
            <div>
              <div className="flex items-center justify-between"><div><h2 className="text-lg font-medium">{selectedDeck.name}</h2><p className="text-xs text-muted-foreground">{cards.length} cards, {due.length} due</p></div>{decks.length > 0 ? <Button variant="ghost" size="icon" title="Delete deck" onClick={async () => { if (selectedId && confirm('Delete this deck and all its cards?')) { await api.flashcards.deleteDeck(selectedId); setSelectedId(null); await refreshDecks() } }}><Trash2 className="h-4 w-4 text-red-600" /></Button> : null}</div>
              <div className="mt-5 grid gap-3 lg:grid-cols-2"><div className="border border-border p-4"><h3 className="text-sm font-medium">Add a card</h3><Input className="mt-3" value={cardDraft.front} onChange={(event) => setCardDraft((current) => ({ ...current, front: event.target.value }))} placeholder="Front: question or cue" /><Textarea className="mt-2 min-h-24" value={cardDraft.back} onChange={(event) => setCardDraft((current) => ({ ...current, back: event.target.value }))} placeholder="Back: concise answer" /><Input className="mt-2" value={cardDraft.tags} onChange={(event) => setCardDraft((current) => ({ ...current, tags: event.target.value }))} placeholder="Tags, comma separated" /><Button className="mt-3" onClick={createCard} disabled={busy || !cardDraft.front.trim() || !cardDraft.back.trim()}><Plus className="mr-2 h-4 w-4" />Add card</Button></div>
                <div className="border border-border"><div className="border-b border-border px-4 py-3 text-sm font-medium">Card inventory</div><div className="max-h-[420px] overflow-y-auto">{cards.length === 0 ? <p className="p-5 text-sm text-muted-foreground">No cards yet.</p> : cards.map((card) => <div key={card.id} className="group flex items-start gap-3 border-b border-border px-4 py-3 last:border-0"><RotateCcw className="mt-0.5 h-3.5 w-3.5 text-muted-foreground" /><div className="min-w-0 flex-1"><p className="truncate text-sm">{card.front}</p><p className="mt-1 truncate text-xs text-muted-foreground">{card.back}</p></div><span className="text-[10px] text-muted-foreground">{card.intervalDays ? `${card.intervalDays}d` : 'new'}</span><button className="opacity-0 group-hover:opacity-100" onClick={async () => { await api.flashcards.deleteCard(card.id); if (selectedId) await Promise.all([refreshCards(selectedId), refreshDecks()]) }} title="Delete card"><Trash2 className="h-3.5 w-3.5 text-red-600" /></button></div>)}</div></div>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
