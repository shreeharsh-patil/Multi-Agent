'use client'

import React, { useState, useEffect, useCallback, useRef } from 'react'
import {
  Cloud, CloudDrizzle, CloudLightning, CloudSnow, CloudSun, Droplets,
  Eye, Gauge, Loader2, MapPin, Newspaper, RefreshCw, Search,
  Send, Sun, Thermometer, Wind, Zap, AlertCircle, Clock, ExternalLink,
  Sparkles, Calendar
} from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { getAccessToken } from '@/lib/auth-store'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

async function apiFetch<T>(endpoint: string, opts: RequestInit = {}): Promise<T> {
  const token = getAccessToken()
  const headers: Record<string, string> = {}
  if (token) headers['Authorization'] = `Bearer ${token}`
  if (!(opts.body instanceof FormData) && opts.method !== 'GET') {
    headers['Content-Type'] = 'application/json'
  }
  const res = await fetch(`${BACKEND_URL}${endpoint}`, {
    ...opts,
    headers: { ...headers, ...(opts.headers as Record<string, string> | undefined) },
  })
  if (!res.ok) {
    throw new Error(`HTTP ${res.status}`)
  }
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

// ── Weather Code Helper ──────────────────────────────────────────────────

function WeatherIcon({ code, className }: { code?: number; className?: string }) {
  const c = code ?? 116
  if (c <= 113) return <Sun className={className} />
  if (c <= 119) return <CloudSun className={className} />
  if (c <= 143) return <Cloud className={className} />
  if (c <= 266) return <CloudDrizzle className={className} />
  if (c <= 395) return <CloudSnow className={className} />
  return <CloudLightning className={className} />
}

function uvLabel(uv: string | number) {
  const n = Number(uv)
  if (n <= 2) return { label: 'Low', color: 'text-emerald-500' }
  if (n <= 5) return { label: 'Moderate', color: 'text-amber-500' }
  if (n <= 7) return { label: 'High', color: 'text-orange-500' }
  return { label: 'Very High', color: 'text-rose-500' }
}

// ── Markdown renderer ──────────────────────────────────────────────────────

function MiniMarkdown({ text }: { text: string }) {
  const lines = text.split('\n')
  return (
    <div className="space-y-1.5 text-xs sm:text-sm leading-relaxed">
      {lines.map((line, i) => {
        if (line.startsWith('### ')) return <h3 key={i} className="text-sm font-semibold text-foreground mt-3 mb-1">{line.slice(4)}</h3>
        if (line.startsWith('## ')) return <h2 key={i} className="text-base font-bold text-foreground mt-4 mb-1">{line.slice(3)}</h2>
        if (line.startsWith('# ')) return <h1 key={i} className="text-lg font-bold text-foreground mt-4 mb-2">{line.slice(2)}</h1>
        if (line.startsWith('> ')) return <blockquote key={i} className="border-l-2 border-primary/50 pl-3 text-muted-foreground italic my-1">{line.slice(2)}</blockquote>
        if (line.startsWith('- ') || line.startsWith('* ')) return <li key={i} className="ml-4 list-disc text-foreground">{line.slice(2)}</li>
        if (line.startsWith('| ') && !line.startsWith('|---')) {
          const cells = line.split('|').filter(Boolean).map(c => c.trim())
          return <div key={i} className="flex gap-2 text-xs py-0.5">{cells.map((c, j) => <span key={j} className="flex-1 text-foreground">{c}</span>)}</div>
        }
        if (line.startsWith('|---')) return null
        const inline = line
          .replace(/\*\*(.+?)\*\*/g, '<strong class="font-semibold text-foreground">$1</strong>')
          .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline font-medium">$1</a>')
          .replace(/`([^`]+)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-xs font-mono">$1</code>')
        return (
          <p key={i} className="text-foreground/90"
            dangerouslySetInnerHTML={{ __html: inline || '\u00a0' }} />
        )
      })}
    </div>
  )
}

const QUICK_QUERIES = [
  "🌤 What's the weather like in New York?",
  "🌧 Will it rain in London today?",
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
      if (r.categories && r.categories.length > 0) setCategories(r.categories)
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
        content: 'Unable to connect to service. Please check your backend connection.',
        ts: new Date(),
      }])
    } finally {
      setChatLoading(false)
    }
  }, [chatInput, chatLoading, city, newsCategory])

  const cur = weather?.current
  const uv = cur ? uvLabel(cur.uvIndex) : null

  return (
    <div className="space-y-6">
      {/* ── Page Header ──────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-2 border-b border-border">
        <div>
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20">
              <CloudSun className="h-5 w-5" />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-foreground">Weather & News</h1>
          </div>
          <p className="text-xs text-muted-foreground mt-1">
            Live weather forecasts, news headlines, and AI-powered insights.
          </p>
        </div>

        {/* Tab Switcher */}
        <div className="flex items-center gap-1 bg-secondary/60 p-1 rounded-lg border border-border shrink-0 self-start sm:self-auto">
          {(['weather', 'news', 'chat'] as const).map(t => (
            <button
              key={t}
              onClick={() => setTab(t)}
              className={`px-3.5 py-1.5 rounded-md text-xs font-medium transition-all ${
                tab === t
                  ? 'bg-background text-foreground shadow-xs border border-border/50 font-semibold'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {t === 'weather' ? '🌤 Weather' : t === 'news' ? '📰 News' : '💬 Ask AI'}
            </button>
          ))}
        </div>
      </div>

      {/* ══ WEATHER TAB ════════════════════════════════════════════════ */}
      {tab === 'weather' && (
        <div className="space-y-6">
          {/* Search bar */}
          <div className="flex items-center gap-3">
            <div className="relative flex-1 max-w-md">
              <MapPin className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                value={cityInput}
                onChange={e => setCityInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') { setCity(cityInput); fetchWeather(cityInput) } }}
                placeholder="Enter city name..."
                className="pl-9 text-xs sm:text-sm"
              />
            </div>
            <Button
              onClick={() => { setCity(cityInput); fetchWeather(cityInput) }}
              disabled={weatherLoading}
              size="sm"
              className="gap-2 text-xs"
            >
              {weatherLoading ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
              Search
            </Button>
            <Button
              variant="outline"
              size="icon"
              onClick={() => fetchWeather(city)}
              disabled={weatherLoading}
              title="Refresh weather"
              className="h-9 w-9 shrink-0"
            >
              <RefreshCw className={`h-3.5 w-3.5 text-muted-foreground ${weatherLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>

          {weatherError && (
            <Card className="border-destructive/40 bg-destructive/5">
              <CardContent className="p-4 flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
                <p className="text-xs sm:text-sm text-destructive">{weatherError}</p>
              </CardContent>
            </Card>
          )}

          {weatherLoading && !weather && (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-xs text-muted-foreground">Loading weather data...</p>
            </div>
          )}

          {weather && cur && (
            <div className="space-y-6">
              {/* Main Weather Hero Card */}
              <Card className="relative overflow-hidden border-border bg-gradient-to-br from-card via-card to-secondary/30 shadow-xs">
                <CardContent className="p-6">
                  <div className="flex items-start justify-between flex-wrap gap-4">
                    <div>
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground mb-1 font-medium">
                        <MapPin className="h-3.5 w-3.5 text-primary" />
                        <span>{weather.city}{weather.country ? `, ${weather.country}` : ''}</span>
                      </div>
                      <div className="flex items-baseline gap-4 mt-2">
                        <span className="text-6xl font-bold tracking-tight text-foreground">{cur.tempC}°C</span>
                        <div>
                          <p className="text-base font-semibold text-foreground">{cur.description}</p>
                          <p className="text-xs text-muted-foreground">Feels like {cur.feelsLikeC}°C ({cur.tempF}°F)</p>
                        </div>
                      </div>
                    </div>
                    <div className="p-3 rounded-2xl bg-secondary/80 border border-border/50 text-primary">
                      <WeatherIcon code={cur.weatherCode} className="h-16 w-16" />
                    </div>
                  </div>

                  {/* Weather Stats Grid */}
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-6 pt-6 border-t border-border">
                    {[
                      { icon: Droplets, label: 'Humidity', value: `${cur.humidity}%` },
                      { icon: Wind, label: 'Wind', value: `${cur.windKmph} km/h ${cur.windDir}` },
                      { icon: Eye, label: 'Visibility', value: `${cur.visibilityKm} km` },
                      { icon: Gauge, label: 'Pressure', value: `${cur.pressureHpa} hPa` },
                    ].map(({ icon: Icon, label, value }) => (
                      <div key={label} className="p-3 rounded-lg bg-secondary/40 border border-border/40 flex items-center gap-3">
                        <Icon className="h-4 w-4 text-muted-foreground shrink-0" />
                        <div>
                          <p className="text-[10px] uppercase font-semibold text-muted-foreground tracking-wider">{label}</p>
                          <p className="text-xs sm:text-sm font-semibold text-foreground">{value}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>

              {/* Extended Metrics */}
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {[
                  { icon: Zap, label: 'UV Index', value: `${cur.uvIndex} (${uv?.label})`, color: uv?.color },
                  { icon: Thermometer, label: 'Feels Like', value: `${cur.feelsLikeC}°C`, color: 'text-foreground' },
                  { icon: Droplets, label: 'Humidity', value: `${cur.humidity}%`, color: 'text-foreground' },
                  { icon: Wind, label: 'Wind Speed', value: `${cur.windKmph} km/h`, color: 'text-foreground' },
                ].map(({ icon: Icon, label, value, color }) => (
                  <Card key={label} className="shadow-none border-border">
                    <CardContent className="p-4 flex items-center gap-3">
                      <div className="p-2 rounded-md bg-secondary text-primary">
                        <Icon className="h-4 w-4" />
                      </div>
                      <div>
                        <p className="text-[10px] uppercase font-medium text-muted-foreground">{label}</p>
                        <p className={`text-xs sm:text-sm font-semibold ${color}`}>{value}</p>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>

              {/* 3-Day Forecast */}
              {weather.forecast.length > 0 && (
                <div className="space-y-3">
                  <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                    <Calendar className="h-4 w-4 text-primary" />
                    3-Day Weather Forecast
                  </h2>

                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                    {weather.forecast.map((day) => (
                      <Card key={day.date} className="shadow-xs border-border">
                        <CardHeader className="p-4 pb-2 flex flex-row items-center justify-between space-y-0">
                          <CardTitle className="text-xs sm:text-sm font-semibold">
                            {new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}
                          </CardTitle>
                          <Badge variant="secondary" className="text-[10px] font-medium gap-1">
                            🌧 {day.chanceOfRain}%
                          </Badge>
                        </CardHeader>
                        <CardContent className="p-4 pt-1">
                          <p className="text-xs text-muted-foreground mb-3">{day.description}</p>
                          <div className="flex items-baseline justify-between pt-2 border-t border-border">
                            <span className="text-lg font-bold text-foreground">{day.maxTempC}°C</span>
                            <span className="text-xs text-muted-foreground">Min {day.minTempC}°C</span>
                          </div>

                          {day.hourly.length > 0 && (
                            <div className="grid grid-cols-4 gap-1 mt-3 pt-3 border-t border-border/60">
                              {day.hourly.map((h, hi) => (
                                <div key={hi} className="text-center">
                                  <p className="text-[9px] text-muted-foreground">{String(Math.floor(parseInt(h.time) / 100)).padStart(2, '0')}:00</p>
                                  <p className="text-xs font-semibold text-foreground">{h.tempC}°</p>
                                </div>
                              ))}
                            </div>
                          )}
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ══ NEWS TAB ═══════════════════════════════════════════════════ */}
      {tab === 'news' && (
        <div className="space-y-6">
          {/* Category Filter Badges */}
          <div className="flex items-center gap-2 flex-wrap pb-1">
            {categories.map(cat => (
              <Badge
                key={cat}
                variant={newsCategory === cat ? 'default' : 'outline'}
                onClick={() => { setNewsCategory(cat); fetchNews(cat) }}
                className={`cursor-pointer text-xs px-3 py-1 transition-all ${
                  newsCategory === cat ? 'shadow-xs font-medium' : 'hover:bg-secondary text-muted-foreground'
                }`}
              >
                {cat}
              </Badge>
            ))}
            <Button
              variant="outline"
              size="icon"
              onClick={() => fetchNews(newsCategory)}
              disabled={newsLoading}
              title="Refresh news"
              className="h-7 w-7 ml-auto shrink-0"
            >
              <RefreshCw className={`h-3 w-3 text-muted-foreground ${newsLoading ? 'animate-spin' : ''}`} />
            </Button>
          </div>

          {newsError && (
            <Card className="border-destructive/40 bg-destructive/5">
              <CardContent className="p-4 flex items-center gap-3">
                <AlertCircle className="h-5 w-5 text-destructive shrink-0" />
                <p className="text-xs sm:text-sm text-destructive">{newsError}</p>
              </CardContent>
            </Card>
          )}

          {newsLoading && !news && (
            <div className="flex flex-col items-center justify-center py-20 gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-xs text-muted-foreground">Fetching news headlines...</p>
            </div>
          )}

          {news && (
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="text-sm font-semibold text-foreground flex items-center gap-2">
                  <Newspaper className="h-4 w-4 text-primary" />
                  {news.category} Headlines ({news.articles.length})
                </h2>
                <span className="text-[11px] text-muted-foreground flex items-center gap-1">
                  <Clock className="h-3 w-3" /> Updated live
                </span>
              </div>

              {news.articles.length === 0 ? (
                <Card>
                  <CardContent className="p-8 text-center text-xs text-muted-foreground">
                    No articles found for this category right now. Try refreshing or selecting another topic.
                  </CardContent>
                </Card>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {news.articles.map((article, i) => (
                    <Card
                      key={i}
                      className="group hover:border-primary/40 hover:shadow-xs transition-all flex flex-col justify-between"
                    >
                      <CardHeader className="p-4 pb-2">
                        <div className="flex items-start gap-3">
                          <span className="text-lg font-bold text-muted-foreground/60 shrink-0 font-mono">
                            {String(i + 1).padStart(2, '0')}
                          </span>
                          <div className="min-w-0 flex-1">
                            <CardTitle className="text-sm font-semibold text-foreground leading-snug group-hover:text-primary transition-colors line-clamp-2">
                              {article.title}
                            </CardTitle>
                          </div>
                        </div>
                      </CardHeader>
                      <CardContent className="p-4 pt-1 flex-1 flex flex-col justify-between gap-3">
                        {article.description && (
                          <p className="text-xs text-muted-foreground leading-relaxed line-clamp-3">
                            {article.description}
                          </p>
                        )}
                        <div className="flex items-center justify-between pt-2 border-t border-border text-[11px]">
                          {article.pubDate ? (
                            <span className="text-muted-foreground flex items-center gap-1">
                              <Clock className="h-3 w-3" />
                              {article.pubDate.slice(0, 22)}
                            </span>
                          ) : <span />}

                          {article.link && (
                            <a
                              href={article.link}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="flex items-center gap-1 text-primary font-medium hover:underline"
                            >
                              Read <ExternalLink className="h-3 w-3" />
                            </a>
                          )}
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* ══ CHAT TAB ═══════════════════════════════════════════════════ */}
      {tab === 'chat' && (
        <Card className="border-border">
          <CardContent className="p-4 sm:p-6 flex flex-col gap-4 min-h-[500px]">
            {/* Context pills */}
            <div className="flex items-center gap-2 flex-wrap text-xs pb-2 border-b border-border">
              <span className="text-muted-foreground">Context:</span>
              <Badge variant="outline" className="gap-1 font-normal">
                <MapPin className="h-3 w-3 text-primary" /> {city}
              </Badge>
              <Badge variant="outline" className="gap-1 font-normal">
                <Newspaper className="h-3 w-3 text-primary" /> {newsCategory}
              </Badge>
            </div>

            {/* Quick questions */}
            {messages.length === 0 && (
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 py-2">
                {QUICK_QUERIES.map(q => (
                  <Button
                    key={q}
                    variant="outline"
                    onClick={() => sendChat(q)}
                    disabled={chatLoading}
                    className="justify-start text-xs h-auto py-2.5 px-3 whitespace-normal text-left font-normal"
                  >
                    {q}
                  </Button>
                ))}
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto space-y-4 max-h-[420px] pr-1">
              {messages.map(msg => (
                <div key={msg.id} className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  {msg.role === 'assistant' && (
                    <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20 shrink-0 self-start">
                      <Sparkles className="h-4 w-4" />
                    </div>
                  )}
                  <div className={`max-w-[85%] rounded-lg p-3 sm:p-4 text-xs sm:text-sm ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground font-medium'
                      : 'bg-secondary/60 border border-border text-foreground'
                  }`}>
                    {msg.role === 'assistant'
                      ? <MiniMarkdown text={msg.content} />
                      : <p className="leading-relaxed">{msg.content}</p>
                    }
                    <p className={`text-[10px] mt-1.5 text-right ${msg.role === 'user' ? 'text-primary-foreground/70' : 'text-muted-foreground'}`}>
                      {msg.ts.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </p>
                  </div>
                </div>
              ))}

              {chatLoading && (
                <div className="flex gap-3 justify-start">
                  <div className="p-2 rounded-lg bg-primary/10 text-primary border border-primary/20 shrink-0">
                    <Sparkles className="h-4 w-4" />
                  </div>
                  <div className="bg-secondary/60 border border-border rounded-lg px-4 py-3 flex items-center gap-2 text-xs text-muted-foreground">
                    <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                    Analyzing request and fetching data...
                  </div>
                </div>
              )}
              <div ref={chatEndRef} />
            </div>

            {/* Chat input */}
            <div className="flex items-center gap-2 pt-2 border-t border-border">
              <Input
                value={chatInput}
                onChange={e => setChatInput(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat() } }}
                placeholder="Ask about weather forecasts, news updates, or travel advice..."
                disabled={chatLoading}
                className="flex-1 text-xs sm:text-sm"
              />
              <Button
                onClick={() => sendChat()}
                disabled={!chatInput.trim() || chatLoading}
                size="icon"
                className="shrink-0"
              >
                <Send className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
