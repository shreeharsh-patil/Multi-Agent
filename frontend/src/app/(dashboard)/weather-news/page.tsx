'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Cloud, CloudDrizzle, CloudLightning, CloudSnow, CloudSun, Droplets,
  Eye, Gauge, Loader2, MapPin, Newspaper, RefreshCw, Search,
  Send, Sun, Thermometer, Wind, Zap, AlertCircle, Clock, ExternalLink,
} from 'lucide-react'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

function getToken() {
  try { return typeof window !== 'undefined' ? localStorage.getItem('access_token') : null } catch { return null }
}

async function apiFetch<T>(endpoint: string, opts: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (!(opts.body instanceof FormData) && opts.method !== 'GET') headers['Content-Type'] = 'application/json'
  const res = await fetch(`${BACKEND_URL}${endpoint}`, { ...opts, headers: { ...headers, ...(opts.headers as Record<string, string> | undefined) } })
  return res.json()
}

// ── Types ──────────────────────────────────────────────────────────────────

interface WeatherCurrent {
  description: string
  tempC: number
  tempF: number
  feelsLikeC: number
  humidity: number
  windKmph: number
  windDir: string
  visibilityKm: number
  uvIndex: string | number
  pressureHpa: string | number
  weatherCode: number
}

interface ForecastHour {
  time: string
  tempC: number
  desc: string
  chanceOfRain: number
}

interface ForecastDay {
  date: string
  maxTempC: number
  minTempC: number
  description: string
  chanceOfRain: number
  hourly: ForecastHour[]
}

interface WeatherResponse {
  success: boolean
  city: string
  country: string
  current: WeatherCurrent | null
  forecast: ForecastDay[]
}

interface Article {
  title: string
  link: string
  description: string
  pubDate: string
}

interface NewsResponse {
  success: boolean
  category: string
  categories: string[]
  articles: Article[]
}

interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string
  ts: Date
}

// ── Weather Code → icon / gradient ──────────────────────────────────────

function WeatherIcon({ code, className }: { code?: number; className?: string }) {
  const c = code ?? 116
  if (c <= 113) return <Sun className={className} />
  if (c <= 119) return <CloudSun className={className} />
  if (c <= 143) return <Cloud className={className} />
  if (c <= 266) return <CloudDrizzle className={className} />
  if (c <= 395) return <CloudSnow className={className} />
  return <CloudLightning className={className} />
}

function weatherGradient(code?: number) {
  const c = code ?? 116
  if (c <= 113) return 'from-amber-400 via-orange-300 to-sky-300'
  if (c <= 119) return 'from-sky-400 via-blue-300 to-slate-300'
  if (c <= 143) return 'from-slate-400 via-slate-300 to-blue-200'
  if (c <= 266) return 'from-slate-600 via-slate-400 to-blue-300'
  if (c <= 395) return 'from-slate-300 via-blue-100 to-white'
  return 'from-slate-700 via-indigo-500 to-purple-400'
}

function uvLabel(uv: string | number) {
  const n = Number(uv)
  if (n <= 2) return { label: 'Low', color: 'text-green-400' }
  if (n <= 5) return { label: 'Moderate', color: 'text-yellow-400' }
  if (n <= 7) return { label: 'High', color: 'text-orange-400' }
  return { label: 'Very High', color: 'text-red-400' }
}

// ── Markdown renderer (minimal) ──────────────────────────────────────────

function MiniMarkdown({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        if (line.startsWith('### ')) return <h3 key={i} className="text-sm font-bold text-white mt-3">{line.slice(4)}</h3>
        if (line.startsWith('## ')) return <h2 key={i} className="text-base font-bold text-white mt-4">{line.slice(3)}</h2>
        if (line.startsWith('# ')) return <h1 key={i} className="text-lg font-bold text-white mt-4">{line.slice(2)}</h1>
        if (line.startsWith('> ')) return <blockquote key={i} className="border-l-2 border-sky-500/50 pl-3 text-slate-400 text-xs">{line.slice(2)}</blockquote>
        if (line.startsWith('- ') || line.startsWith('* ')) return <li key={i} className="ml-4 list-disc text-slate-300 text-sm">{line.slice(2)}</li>
        if (line.startsWith('| ') && !line.startsWith('|---')) {
          const cells = line.split('|').filter(Boolean).map(c => c.trim())
          return <div key={i} className="flex gap-2 text-xs">{cells.map((c, j) => <span key={j} className="flex-1 text-slate-300">{c}</span>)}</div>
        }
        if (line.startsWith('|---')) return null
        const inline = line
          .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white font-semibold">$1</strong>')
          .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-sky-400 hover:text-sky-300 underline">$1</a>')
          .replace(/`([^`]+)`/g, '<code class="bg-slate-800 px-1 rounded text-sky-300 text-xs font-mono">$1</code>')
        return (
          <p key={i} className="text-slate-300 text-sm leading-relaxed"
            dangerouslySetInnerHTML={{ __html: inline || '\u00a0' }} />
        )
      })}
    </div>
  )
}

// ── News category pill ────────────────────────────────────────────────────

const CAT_COLORS: Record<string, string> = {
  World:       'bg-blue-500/20 text-blue-300 border-blue-500/30',
  Technology:  'bg-violet-500/20 text-violet-300 border-violet-500/30',
  Science:     'bg-teal-500/20 text-teal-300 border-teal-500/30',
  Business:    'bg-amber-500/20 text-amber-300 border-amber-500/30',
  Health:      'bg-rose-500/20 text-rose-300 border-rose-500/30',
  Sports:      'bg-green-500/20 text-green-300 border-green-500/30',
  'AI/Tech':   'bg-purple-500/20 text-purple-300 border-purple-500/30',
}

const QUICK_QUERIES = [
  '🌤 What's the weather like in New York?',
  '🌧 Will it rain in Mumbai today?',
  '📰 What are the top world news headlines?',
  '🤖 Latest AI and technology news',
  '💼 Top business and finance stories today',
  '🔬 Any interesting science news?',
]

// ── Main component ─────────────────────────────────────────────────────────

export default function WeatherNewsPage() {
  // Weather state
  const [city, setCity] = useState('London')
  const [cityInput, setCityInput] = useState('London')
  const [weather, setWeather] = useState<WeatherResponse | null>(null)
  const [weatherLoading, setWeatherLoading] = useState(false)
  const [weatherError, setWeatherError] = useState<string | null>(null)

  // News state
  const [newsCategory, setNewsCategory] = useState('World')
  const [news, setNews] = useState<NewsResponse | null>(null)
  const [newsLoading, setNewsLoading] = useState(false)
  const [newsError, setNewsError] = useState<string | null>(null)
  const [categories, setCategories] = useState<string[]>(['World', 'Technology', 'Science', 'Business', 'Health', 'Sports', 'AI/Tech'])

  // Chat state
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [chatInput, setChatInput] = useState('')
  const [chatLoading, setChatLoading] = useState(false)
  const chatEndRef = useRef<HTMLDivElement>(null)

  // Active tab
  const [tab, setTab] = useState<'weather' | 'news' | 'chat'>('weather')

  // Auto-scroll chat
  useEffect(() => { chatEndRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, chatLoading])

  // Fetch categories on mount
  useEffect(() => {
    apiFetch<{ categories: string[] }>('/api/weather-news/categories').then(r => {
      if (r.categories) setCategories(r.categories)
    }).catch(() => {})
  }, [])

  // Fetch weather
  const fetchWeather = useCallback(async (c: string) => {
    if (!c.trim()) return
    setWeatherLoading(true)
    setWeatherError(null)
    try {
      const data = await apiFetch<WeatherResponse>(`/api/weather-news/weather?city=${encodeURIComponent(c.trim())}`)
      setWeather(data)
    } catch {
      setWeatherError('Failed to fetch weather data. Please try again.')
    } finally {
      setWeatherLoading(false)
    }
  }, [])

  // Fetch news
  const fetchNews = useCallback(async (cat: string) => {
    setNewsLoading(true)
    setNewsError(null)
    try {
      const data = await apiFetch<NewsResponse>(`/api/weather-news/news?category=${encodeURIComponent(cat)}`)
      setNews(data)
    } catch {
      setNewsError('Failed to fetch news. Please try again.')
    } finally {
      setNewsLoading(false)
    }
  }, [])

  // Load initial data
  useEffect(() => { fetchWeather('London') }, [fetchWeather])
  useEffect(() => { fetchNews('World') }, [fetchNews])

  // Chat send
  const sendChat = useCallback(async (q?: string) => {
    const query = (q ?? chatInput).trim()
    if (!query || chatLoading) return

    const userMsg: ChatMessage = { id: Date.now().toString(), role: 'user', content: query, ts: new Date() }
    setMessages(prev => [...prev, userMsg])
    setChatInput('')
    setChatLoading(true)

    try {
      const res = await apiFetch<{ success: boolean; output: string }>('/api/weather-news/ask', {
        method: 'POST',
        body: JSON.stringify({ query, city, news_category: newsCategory }),
      })
      setMessages(prev => [...prev, {
        id: Date.now().toString() + 'r',
        role: 'assistant',
        content: res.output || 'No response received.',
        ts: new Date(),
      }])
    } catch (err) {
      setMessages(prev => [...prev, {
        id: Date.now().toString() + 'e',
        role: 'assistant',
        content: '❌ Failed to get a response. Please check your connection.',
        ts: new Date(),
      }])
    } finally {
      setChatLoading(false)
    }
  }, [chatInput, chatLoading, city, newsCategory])

  // ── Render ──────────────────────────────────────────────────────────────

  const cur = weather?.current
  const grad = weatherGradient(cur?.weatherCode)
  const uv = cur ? uvLabel(cur.uvIndex) : null

  return (
    <div className="min-h-screen bg-[#0b0f1a] text-white flex flex-col">
      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="border-b border-slate-800 bg-[#0b0f1a]/95 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center gap-4 flex-wrap">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600 flex items-center justify-center shadow-lg shadow-sky-500/25">
              <CloudSun className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-lg font-bold text-white">Weather & News</h1>
              <p className="text-xs text-slate-400">Real-time data · No API key needed</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-1 bg-slate-900 border border-slate-800 rounded-xl p-1 ml-auto">
            {(['weather', 'news', 'chat'] as const).map(t => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all capitalize ${
                  tab === t
                    ? 'bg-sky-500 text-white shadow-sm'
                    : 'text-slate-400 hover:text-white'
                }`}
              >
                {t === 'weather' ? '🌤 Weather' : t === 'news' ? '📰 News' : '💬 Ask AI'}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-6 py-6 w-full flex-1">

        {/* ══ WEATHER TAB ════════════════════════════════════════════════ */}
        {tab === 'weather' && (
          <div className="space-y-5">
            {/* City search */}
            <div className="flex gap-3">
              <div className="relative flex-1 max-w-md">
                <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
                <input
                  value={cityInput}
                  onChange={e => setCityInput(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') { setCity(cityInput); fetchWeather(cityInput) } }}
                  placeholder="Enter city name…"
                  className="w-full bg-slate-900 border border-slate-700 rounded-xl pl-10 pr-4 py-2.5 text-sm outline-none focus:border-sky-500/50 transition-colors"
                />
              </div>
              <button
                onClick={() => { setCity(cityInput); fetchWeather(cityInput) }}
                disabled={weatherLoading}
                className="flex items-center gap-2 px-4 py-2.5 bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 text-white rounded-xl text-sm font-medium transition-colors"
              >
                {weatherLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
                Search
              </button>
              <button
                onClick={() => fetchWeather(city)}
                disabled={weatherLoading}
                className="w-10 h-10 flex items-center justify-center bg-slate-800 border border-slate-700 hover:border-slate-600 rounded-xl transition-colors"
                title="Refresh"
              >
                <RefreshCw className={`w-4 h-4 text-slate-400 ${weatherLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {weatherError && (
              <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-3">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
                <p className="text-red-300 text-sm">{weatherError}</p>
              </div>
            )}

            {weatherLoading && !weather && (
              <div className="flex items-center justify-center py-24">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-12 h-12 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-slate-400">Fetching live weather data…</p>
                </div>
              </div>
            )}

            {weather && cur && (
              <>
                {/* Hero weather card */}
                <div className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${grad} p-6 shadow-xl`}>
                  <div className="absolute inset-0 opacity-10" style={{
                    backgroundImage: 'radial-gradient(circle at 80% 20%, white 0%, transparent 60%)',
                  }} />
                  <div className="relative z-10 flex items-start justify-between flex-wrap gap-4">
                    <div>
                      <div className="flex items-center gap-2 mb-1">
                        <MapPin className="w-4 h-4 text-white/70" />
                        <span className="text-white/90 font-medium">{weather.city}{weather.country ? `, ${weather.country}` : ''}</span>
                      </div>
                      <div className="flex items-end gap-3">
                        <span className="text-7xl font-bold text-white">{cur.tempC}°</span>
                        <div className="pb-2">
                          <p className="text-white/90 text-lg font-medium">{cur.description}</p>
                          <p className="text-white/70 text-sm">Feels like {cur.feelsLikeC}°C</p>
                        </div>
                      </div>
                    </div>
                    <WeatherIcon code={cur.weatherCode} className="w-24 h-24 text-white/80 drop-shadow-lg" />
                  </div>

                  {/* Stat row */}
                  <div className="relative z-10 mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {[
                      { icon: Droplets, label: 'Humidity', value: `${cur.humidity}%` },
                      { icon: Wind, label: 'Wind', value: `${cur.windKmph} km/h ${cur.windDir}` },
                      { icon: Eye, label: 'Visibility', value: `${cur.visibilityKm} km` },
                      { icon: Gauge, label: 'Pressure', value: `${cur.pressureHpa} hPa` },
                    ].map(({ icon: Icon, label, value }) => (
                      <div key={label} className="bg-black/20 backdrop-blur-sm rounded-xl px-3 py-2.5 flex items-center gap-2.5">
                        <Icon className="w-4 h-4 text-white/70 shrink-0" />
                        <div>
                          <p className="text-[10px] text-white/60 uppercase tracking-wide">{label}</p>
                          <p className="text-sm font-semibold text-white">{value}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* UV + extra stats */}
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    { icon: Zap, label: 'UV Index', value: `${cur.uvIndex} — ${uv?.label}`, cls: uv?.color },
                    { icon: Thermometer, label: 'Feels Like', value: `${cur.feelsLikeC}°C`, cls: 'text-orange-300' },
                    { icon: Droplets, label: 'Humidity', value: `${cur.humidity}%`, cls: 'text-sky-300' },
                    { icon: Wind, label: 'Wind Speed', value: `${cur.windKmph} km/h`, cls: 'text-teal-300' },
                  ].map(({ icon: Icon, label, value, cls }) => (
                    <div key={label} className="bg-slate-900/50 border border-slate-800 rounded-2xl p-4 flex items-center gap-3">
                      <div className="w-9 h-9 rounded-xl bg-slate-800 flex items-center justify-center shrink-0">
                        <Icon className={`w-4 h-4 ${cls}`} />
                      </div>
                      <div>
                        <p className="text-[10px] text-slate-500 uppercase tracking-wide">{label}</p>
                        <p className={`text-sm font-semibold ${cls}`}>{value}</p>
                      </div>
                    </div>
                  ))}
                </div>

                {/* 3-day forecast */}
                {weather.forecast.length > 0 && (
                  <div>
                    <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest mb-3">📅 3-Day Forecast</h2>
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                      {weather.forecast.map((day) => (
                        <div key={day.date} className="bg-slate-900/50 border border-slate-800 rounded-2xl p-4">
                          <div className="flex items-center justify-between mb-3">
                            <span className="text-sm font-semibold text-white">{new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                            <span className="text-[10px] bg-sky-500/20 text-sky-300 border border-sky-500/30 px-2 py-0.5 rounded-full">🌧 {day.chanceOfRain}%</span>
                          </div>
                          <p className="text-xs text-slate-400 mb-2">{day.description}</p>
                          <div className="flex items-center justify-between">
                            <span className="text-lg font-bold text-white">{day.maxTempC}°</span>
                            <span className="text-sm text-slate-500">{day.minTempC}°</span>
                          </div>
                          {/* Hourly mini */}
                          {day.hourly.length > 0 && (
                            <div className="mt-3 grid grid-cols-4 gap-1">
                              {day.hourly.map((h, hi) => (
                                <div key={hi} className="text-center">
                                  <p className="text-[9px] text-slate-600">{String(Math.floor(parseInt(h.time) / 100)).padStart(2, '0')}:00</p>
                                  <p className="text-[11px] font-semibold text-slate-300">{h.tempC}°</p>
                                </div>
                              ))}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {/* ══ NEWS TAB ═══════════════════════════════════════════════════ */}
        {tab === 'news' && (
          <div className="space-y-5">
            {/* Category picker */}
            <div className="flex items-center gap-2 flex-wrap">
              {categories.map(cat => (
                <button
                  key={cat}
                  onClick={() => { setNewsCategory(cat); fetchNews(cat) }}
                  className={`px-3.5 py-1.5 rounded-xl text-xs font-semibold border transition-all ${
                    newsCategory === cat
                      ? (CAT_COLORS[cat] ?? 'bg-sky-500/20 text-sky-300 border-sky-500/30')
                      : 'bg-slate-900 border-slate-800 text-slate-400 hover:border-slate-700 hover:text-slate-300'
                  }`}
                >
                  {cat}
                </button>
              ))}
              <button
                onClick={() => fetchNews(newsCategory)}
                disabled={newsLoading}
                className="ml-auto w-8 h-8 flex items-center justify-center bg-slate-800 border border-slate-700 hover:border-slate-600 rounded-xl transition-colors"
                title="Refresh news"
              >
                <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${newsLoading ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {newsError && (
              <div className="flex items-center gap-3 bg-red-500/10 border border-red-500/30 rounded-xl px-5 py-3">
                <AlertCircle className="w-5 h-5 text-red-400 shrink-0" />
                <p className="text-red-300 text-sm">{newsError}</p>
              </div>
            )}

            {newsLoading && !news && (
              <div className="flex items-center justify-center py-24">
                <div className="flex flex-col items-center gap-4">
                  <div className="w-12 h-12 border-4 border-sky-500 border-t-transparent rounded-full animate-spin" />
                  <p className="text-slate-400">Fetching live headlines…</p>
                </div>
              </div>
            )}

            {news && (
              <>
                <div className="flex items-center justify-between">
                  <h2 className="text-sm font-bold text-slate-300 uppercase tracking-widest flex items-center gap-2">
                    <Newspaper className="w-4 h-4 text-sky-400" />
                    {news.category} · {news.articles.length} Headlines
                  </h2>
                  <span className="text-[10px] text-slate-600 flex items-center gap-1">
                    <Clock className="w-3 h-3" /> Live from RSS
                  </span>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {news.articles.map((article, i) => (
                    <div
                      key={i}
                      className="group bg-slate-900/50 border border-slate-800 hover:border-slate-700 rounded-2xl p-4 transition-colors"
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-2xl font-black text-slate-700 w-8 shrink-0 mt-0.5 leading-none">{String(i + 1).padStart(2, '0')}</span>
                        <div className="min-w-0 flex-1">
                          <h3 className="text-sm font-semibold text-white leading-snug group-hover:text-sky-300 transition-colors mb-1.5">
                            {article.title}
                          </h3>
                          {article.description && (
                            <p className="text-[11px] text-slate-500 leading-relaxed line-clamp-2">{article.description}</p>
                          )}
                          <div className="mt-2.5 flex items-center justify-between">
                            {article.pubDate && (
                              <span className="text-[10px] text-slate-600 flex items-center gap-1">
                                <Clock className="w-3 h-3" />
                                {article.pubDate.slice(0, 22)}
                              </span>
                            )}
                            {article.link && (
                              <a
                                href={article.link}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="flex items-center gap-1 text-[10px] text-sky-500 hover:text-sky-400 transition-colors"
                                onClick={e => e.stopPropagation()}
                              >
                                Read <ExternalLink className="w-2.5 h-2.5" />
                              </a>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        )}

        {/* ══ CHAT TAB ═══════════════════════════════════════════════════ */}
        {tab === 'chat' && (
          <div className="flex flex-col gap-4 h-full" style={{ minHeight: 'calc(100vh - 200px)' }}>
            {/* Context pills */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs text-slate-500">Context:</span>
              <span className="flex items-center gap-1.5 text-xs bg-sky-500/10 border border-sky-500/20 text-sky-400 px-2.5 py-1 rounded-lg">
                <MapPin className="w-3 h-3" /> {city}
              </span>
              <span className={`flex items-center gap-1.5 text-xs border px-2.5 py-1 rounded-lg ${CAT_COLORS[newsCategory] ?? 'bg-slate-800 border-slate-700 text-slate-400'}`}>
                <Newspaper className="w-3 h-3" /> {newsCategory}
              </span>
              <span className="text-xs text-slate-600 ml-1">Change city/category in the other tabs</span>
            </div>

            {/* Quick questions */}
            {messages.length === 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2.5 mb-2">
                {QUICK_QUERIES.map(q => (
                  <button
                    key={q}
                    onClick={() => sendChat(q)}
                    disabled={chatLoading}
                    className="text-left text-xs text-slate-400 hover:text-sky-300 bg-slate-900/50 hover:bg-slate-800/60 border border-slate-800 hover:border-slate-700 px-3.5 py-2.5 rounded-xl transition-all disabled:opacity-50"
                  >
                    {q}
                  </button>
                ))}
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 pr-1">
              {messages.map(msg => (
                <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && (
                    <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600 flex items-center justify-center shrink-0 mt-0.5">
                      <CloudSun className="w-4 h-4 text-white" />
                    </div>
                  )}
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    msg.role === 'user'
                      ? 'bg-sky-500/20 border border-sky-500/30 rounded-tr-sm'
                      : 'bg-slate-800/60 border border-slate-700/50 rounded-tl-sm'
                  }`}>
                    {msg.role === 'assistant'
                      ? <MiniMarkdown text={msg.content} />
                      : <p className="text-sm text-slate-200">{msg.content}</p>
                    }
                    <p className="text-[10px] text-slate-600 mt-1.5 text-right">
                      {msg.ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}

              {chatLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-sky-500 to-blue-600 flex items-center justify-center shrink-0">
                    <CloudSun className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-slate-800/60 border border-slate-700/50 rounded-2xl rounded-tl-sm px-5 py-4">
                    <div className="flex gap-1.5 items-center">
                      {[0, 1, 2].map(i => (
                        <div key={i} className="w-1.5 h-1.5 rounded-full bg-sky-400 animate-bounce" style={{ animationDelay: `${i * 0.15}s` }} />
                      ))}
                      <span className="text-xs text-slate-500 ml-1">Fetching real-time data…</span>
                    </div>
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat input */}
            <div className="shrink-0 flex items-end gap-2 bg-slate-900/60 border border-slate-700 rounded-2xl p-2 focus-within:border-sky-500/50 transition-colors">
              <textarea
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat() } }}
                placeholder="Ask about weather, news, forecasts… (e.g. 'Will it rain in Tokyo this weekend?')"
                disabled={chatLoading}
                className="flex-1 bg-transparent text-sm text-white placeholder:text-slate-500 resize-none outline-none px-2 py-1.5 min-h-[38px] max-h-[100px]"
                rows={1}
              />
              <button
                onClick={() => sendChat()}
                disabled={!chatInput.trim() || chatLoading}
                className="w-9 h-9 rounded-xl bg-sky-500 hover:bg-sky-400 disabled:bg-slate-700 flex items-center justify-center transition-colors shrink-0"
              >
                <Send className="w-4 h-4 text-white" />
              </button>
            </div>
            <p className="text-[10px] text-slate-600 text-center -mt-2">Enter to send · Shift+Enter for new line · Fetches live data on every query</p>
          </div>
        )}
      </div>
    </div>
  )
}
