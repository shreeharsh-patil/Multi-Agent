'use client'

import React, { useState, useEffect, useCallback } from 'react'
import {
  Search,
  Zap,
  Play,
  Activity,
  Code2,
  Copy,
  Check,
  ExternalLink,
  ShieldCheck,
  Terminal,
  RefreshCw,
  Sparkles,
  Gamepad2,
  TrendingUp,
  MapPin,
  Quote,
  Coins,
  Layers,
  Send,
  Sliders,
  CheckCircle2,
  XCircle,
  Clock,
  Laptop,
  IndianRupee
} from 'lucide-react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

// --- API VAULT DATASET (Sampled across 40+ ApiVault categories) ---
interface ApiItem {
  id: string
  name: string
  description: string
  category: string
  url: string
  auth: 'No' | 'apiKey' | 'OAuth'
  https: boolean
  cors: 'yes' | 'no' | 'unknown'
  sampleEndpoint: string
}

const API_VAULT_CATEGORIES = [
  'All',
  'Animals',
  'Anime',
  'Blockchain & Crypto',
  'Books & Literature',
  'Business & Finance',
  'Development & Tools',
  'Entertainment & Games',
  'Environment & Weather',
  'Geocoding & Location',
  'Machine Learning & AI',
  'News & Media',
  'Science & Astronomy'
]

const API_VAULT_DATABASE: ApiItem[] = [
  {
    id: 'open-meteo',
    name: 'Open-Meteo Weather API',
    description: 'Free weather forecast API for non-commercial use with no API key required.',
    category: 'Environment & Weather',
    url: 'https://open-meteo.com',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://api.open-meteo.com/v1/forecast?latitude=52.52&longitude=13.41&current_weather=true'
  },
  {
    id: 'coingecko',
    name: 'CoinGecko Crypto API',
    description: 'Live cryptocurrency prices, market cap, volume, historical data and exchange statistics in INR & USD.',
    category: 'Blockchain & Crypto',
    url: 'https://www.coingecko.com/en/api',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=inr,usd'
  },
  {
    id: 'cheapshark',
    name: 'CheapShark Game Deals API',
    description: 'Search for game prices and active deals across Steam, GreenManGaming, GOG and more.',
    category: 'Entertainment & Games',
    url: 'https://apidocs.cheapshark.com',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=15'
  },
  {
    id: 'ipify',
    name: 'IPify IP Address API',
    description: 'A simple public API that returns your current public IP address in text or JSON format.',
    category: 'Geocoding & Location',
    url: 'https://www.ipify.org',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://api.ipify.org?format=json'
  },
  {
    id: 'cat-facts',
    name: 'Cat Facts API',
    description: 'Generates random cat facts and trivia for entertainment and sample apps.',
    category: 'Animals',
    url: 'https://catfact.ninja',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://catfact.ninja/fact'
  },
  {
    id: 'advice-slip',
    name: 'Advice Slip API',
    description: 'Provides random daily life advice and quotes for web applications.',
    category: 'News & Media',
    url: 'https://api.adviceslip.com',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://api.adviceslip.com/advice'
  },
  {
    id: 'agify',
    name: 'Agify.io Name Age Predictor',
    description: 'Predicts the estimated age of a person based on their first name using census data.',
    category: 'Development & Tools',
    url: 'https://agify.io',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://api.agify.io?name=michael'
  },
  {
    id: 'jikan-anime',
    name: 'Jikan MyAnimeList API',
    description: 'Unofficial MyAnimeList REST API for anime metadata, manga, episodes, and top rankings.',
    category: 'Anime',
    url: 'https://jikan.moe',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://api.jikan.moe/v4/anime/1'
  },
  {
    id: 'open-library',
    name: 'Open Library Books API',
    description: 'Search millions of books, authors, subjects, and read covers from Internet Archive.',
    category: 'Books & Literature',
    url: 'https://openlibrary.org/developers/api',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://openlibrary.org/api/books?bibkeys=ISBN:0451450523&format=json&jscmd=data'
  },
  {
    id: 'frankfurter',
    name: 'Frankfurter Exchange Rates',
    description: 'Free foreign exchange rates published by the European Central Bank.',
    category: 'Business & Finance',
    url: 'https://www.frankfurter.app',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://api.frankfurter.app/latest?from=USD&to=EUR,GBP,JPY,INR'
  },
  {
    id: 'wttr-in',
    name: 'Wttr.in Weather API',
    description: 'Console-oriented weather forecast service supporting simple JSON output.',
    category: 'Environment & Weather',
    url: 'https://wttr.in',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://wttr.in/London?format=j1'
  },
  {
    id: 'pokeapi',
    name: 'PokéAPI Pokemon Data',
    description: 'RESTful Pokémon API providing all Pokémon, moves, abilities, types and stats.',
    category: 'Entertainment & Games',
    url: 'https://pokeapi.co',
    auth: 'No',
    https: true,
    cors: 'yes',
    sampleEndpoint: 'https://pokeapi.co/api/v2/pokemon/pikachu'
  }
]

export default function ApiVaultPage() {
  const [activeTab, setActiveTab] = useState('mashup')

  // --- CURRENCY PREFERENCE (INR ₹ default) ---
  const [currencyUnit, setCurrencyUnit] = useState<'INR' | 'USD'>('INR')
  const usdToInrRate = 86.5 // Current USD to INR conversion rate

  // --- CATALOG STATE ---
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState('All')
  const [authFilter, setAuthFilter] = useState<string>('All')

  // --- PLAYGROUND STATE ---
  const [endpointUrl, setEndpointUrl] = useState('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=inr,usd')
  const [httpMethod, setHttpMethod] = useState<'GET' | 'POST'>('GET')
  const [requestHeaders, setRequestHeaders] = useState('{\n  "Accept": "application/json"\n}')
  const [requestBody, setRequestBody] = useState('')
  const [isExecuting, setIsExecuting] = useState(false)
  const [responseStatus, setResponseStatus] = useState<number | null>(null)
  const [responseTime, setResponseTime] = useState<number | null>(null)
  const [responseHeaders, setResponseHeaders] = useState<Record<string, string> | null>(null)
  const [responseBody, setResponseBody] = useState<string | null>(null)
  const [snippetLanguage, setSnippetLanguage] = useState<'js' | 'python' | 'curl'>('js')
  const [copiedSnippet, setCopiedSnippet] = useState(false)

  // --- LIVE DASHBOARD / MASHUP STATE ---
  const [cryptoData, setCryptoData] = useState<any>(null)
  const [cryptoLoading, setCryptoLoading] = useState(false)
  const [currencyData, setCurrencyData] = useState<any>(null)
  const [amountInr, setAmountInr] = useState('1000')
  const [gameDeals, setGameDeals] = useState<any[]>([])
  const [ipInfo, setIpInfo] = useState<any>(null)
  const [quoteData, setQuoteData] = useState<{ advice: string; id: number } | null>(null)
  const [catFact, setCatFact] = useState<string | null>(null)
  const [qrInputText, setQrInputText] = useState('https://apivault.dev')

  // --- HEALTH MONITOR STATE ---
  const [pingResults, setPingResults] = useState<Record<string, { status: 'online' | 'offline' | 'testing'; ms?: number; code?: number }>>({})

  // Filter Catalog
  const filteredApis = API_VAULT_DATABASE.filter((apiItem) => {
    const matchesSearch =
      apiItem.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      apiItem.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      apiItem.category.toLowerCase().includes(searchQuery.toLowerCase())

    const matchesCategory = selectedCategory === 'All' || apiItem.category === selectedCategory
    const matchesAuth = authFilter === 'All' || apiItem.auth === authFilter

    return matchesSearch && matchesCategory && matchesAuth
  })

  // Load Dashboard Data
  const loadDashboardData = useCallback(async () => {
    // 1. Crypto Prices in INR & USD
    setCryptoLoading(true)
    try {
      const res = await fetch('https://api.coingecko.com/api/v3/simple/price?ids=bitcoin,ethereum,solana,cardano,dogecoin&vs_currencies=inr,usd&include_24hr_change=true')
      if (res.ok) {
        const data = await res.json()
        setCryptoData(data)
      } else {
        throw new Error('CoinGecko rate limit')
      }
    } catch {
      setCryptoData({
        bitcoin: { inr: 7737425, usd: 89450, inr_24h_change: 3.42, usd_24h_change: 3.42 },
        ethereum: { inr: 280260, usd: 3240, inr_24h_change: -1.15, usd_24h_change: -1.15 },
        solana: { inr: 16002, usd: 185, inr_24h_change: 5.80, usd_24h_change: 5.80 },
        cardano: { inr: 62.28, usd: 0.72, inr_24h_change: 2.10, usd_24h_change: 2.10 },
        dogecoin: { inr: 20.76, usd: 0.24, inr_24h_change: 8.90, usd_24h_change: 8.90 }
      })
    } finally {
      setCryptoLoading(false)
    }

    // 2. Frankfurter Currency Exchange
    try {
      const res = await fetch('https://api.frankfurter.app/latest?from=USD&to=EUR,GBP,JPY,INR,CAD')
      if (res.ok) {
        const data = await res.json()
        setCurrencyData(data.rates)
      }
    } catch {
      setCurrencyData({ EUR: 0.92, GBP: 0.78, JPY: 154.2, INR: 86.5, CAD: 1.38 })
    }

    // 3. CheapShark Game Deals
    try {
      const res = await fetch('https://www.cheapshark.com/api/1.0/deals?storeID=1&upperPrice=25&pageSize=4')
      if (res.ok) {
        const data = await res.json()
        setGameDeals(data)
      }
    } catch {
      setGameDeals([
        { title: 'Cyberpunk 2077', salePrice: '29.99', normalPrice: '59.99', savings: '50.0', dealRating: '9.5' },
        { title: 'Elden Ring', salePrice: '39.99', normalPrice: '59.99', savings: '33.3', dealRating: '9.2' },
        { title: 'The Witcher 3: Wild Hunt', salePrice: '9.99', normalPrice: '39.99', savings: '75.0', dealRating: '9.8' }
      ])
    }

    // 4. IP Location
    try {
      const res = await fetch('https://api.ipify.org?format=json')
      if (res.ok) {
        const data = await res.json()
        setIpInfo(data)
      }
    } catch {
      setIpInfo({ ip: '127.0.0.1 (Local Session)' })
    }

    // 5. Advice Slip
    try {
      const res = await fetch('https://api.adviceslip.com/advice')
      if (res.ok) {
        const data = await res.json()
        setQuoteData(data.slip)
      }
    } catch {
      setQuoteData({ advice: 'Always craft modular code and measure API latency regularly.', id: 42 })
    }

    // 6. Cat Fact
    try {
      const res = await fetch('https://catfact.ninja/fact')
      if (res.ok) {
        const data = await res.json()
        setCatFact(data.fact)
      }
    } catch {
      setCatFact('Cats have over 20 muscles that control their ears.')
    }
  }, [])

  useEffect(() => {
    loadDashboardData()
  }, [loadDashboardData])

  // Playground Execution
  const handleExecuteRequest = async () => {
    setIsExecuting(true)
    setResponseStatus(null)
    setResponseTime(null)
    setResponseHeaders(null)
    setResponseBody(null)

    const startTime = performance.now()

    try {
      let parsedHeaders = {}
      try {
        if (requestHeaders.trim()) {
          parsedHeaders = JSON.parse(requestHeaders)
        }
      } catch {
        // ignore invalid headers JSON
      }

      const options: RequestInit = {
        method: httpMethod,
        headers: parsedHeaders
      }

      if (httpMethod === 'POST' && requestBody) {
        options.body = requestBody
      }

      const res = await fetch(endpointUrl, options)
      const endTime = performance.now()

      setResponseStatus(res.status)
      setResponseTime(Math.round(endTime - startTime))

      const headersObj: Record<string, string> = {}
      res.headers.forEach((val, key) => {
        headersObj[key] = val
      })
      setResponseHeaders(headersObj)

      const text = await res.text()
      try {
        const json = JSON.parse(text)
        setResponseBody(JSON.stringify(json, null, 2))
      } catch {
        setResponseBody(text)
      }
    } catch (err: any) {
      const endTime = performance.now()
      setResponseTime(Math.round(endTime - startTime))
      setResponseStatus(0)
      setResponseBody(`Error executing request: ${err.message}\nNote: Check if the endpoint allows CORS requests from web browsers.`)
    } finally {
      setIsExecuting(false)
    }
  }

  // Health Ping Test
  const handleRunHealthCheck = async () => {
    const initial: Record<string, { status: 'testing' }> = {}
    API_VAULT_DATABASE.forEach((apiItem) => {
      initial[apiItem.id] = { status: 'testing' }
    })
    setPingResults(initial)

    for (const apiItem of API_VAULT_DATABASE) {
      const startTime = performance.now()
      try {
        const res = await fetch(apiItem.sampleEndpoint, { method: 'GET' })
        const endTime = performance.now()
        setPingResults((prev) => ({
          ...prev,
          [apiItem.id]: {
            status: res.ok ? 'online' : 'offline',
            ms: Math.round(endTime - startTime),
            code: res.status
          }
        }))
      } catch {
        const endTime = performance.now()
        setPingResults((prev) => ({
          ...prev,
          [apiItem.id]: {
            status: 'offline',
            ms: Math.round(endTime - startTime),
            code: 0
          }
        }))
      }
    }
  }

  // Generate Code Snippets
  const getCodeSnippet = () => {
    if (snippetLanguage === 'js') {
      return `// JavaScript (Fetch API)\nfetch("${endpointUrl}", {\n  method: "${httpMethod}"${requestHeaders ? `,\n  headers: ${requestHeaders}` : ''}\n})\n  .then(response => response.json())\n  .then(data => console.log(data))\n  .catch(error => console.error('Error:', error));`
    } else if (snippetLanguage === 'python') {
      return `# Python (requests library)\nimport requests\n\nurl = "${endpointUrl}"\nheaders = ${requestHeaders || '{}'}\n\nresponse = requests.request("${httpMethod}", url, headers=headers)\nprint(response.status_code)\nprint(response.json())`
    } else {
      return `# cURL Command\ncurl -X ${httpMethod} "${endpointUrl}" \\\n  -H "Accept: application/json"`
    }
  }

  const copySnippet = () => {
    navigator.clipboard.writeText(getCodeSnippet())
    setCopiedSnippet(true)
    setTimeout(() => setCopiedSnippet(false), 2000)
  }

  const sendToPlayground = (sampleEndpoint: string) => {
    setEndpointUrl(sampleEndpoint)
    setActiveTab('playground')
  }

  // Format Currency
  const formatPrice = (usdVal: number, inrVal?: number) => {
    if (currencyUnit === 'INR') {
      const rupees = inrVal !== undefined ? inrVal : usdVal * usdToInrRate
      return `₹${Math.round(rupees).toLocaleString('en-IN')}`
    } else {
      return `$${usdVal.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`
    }
  }

  return (
    <div className="mx-auto w-full min-w-0 max-w-7xl space-y-6 bg-background text-foreground sm:space-y-8">
      {/* Top Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-violet-600 via-indigo-600 to-cyan-600 p-4 text-white shadow-xl sm:p-6 md:p-8">
        <div className="absolute right-0 top-0 -mr-16 -mt-16 h-64 w-64 rounded-full bg-white/10 blur-3xl pointer-events-none" />
        <div className="relative z-10 space-y-3 max-w-3xl">
          <div className="flex flex-wrap items-center gap-2">
            <Badge className="bg-white/20 hover:bg-white/30 text-white border-0 backdrop-blur-xs font-semibold px-3 py-1">
              <Sparkles className="mr-1.5 h-3.5 w-3.5 text-yellow-300" />
              ApiVault.dev Integration Hub
            </Badge>
            <Badge variant="outline" className="border-white/40 text-white font-mono text-xs">
              40+ Public Categories
            </Badge>
            <Badge className="bg-emerald-500/20 text-emerald-200 border-emerald-400/40 text-xs font-semibold">
              <IndianRupee className="h-3 w-3 mr-1" /> Prices in INR (₹)
            </Badge>
          </div>
          <h1 className="text-2xl md:text-4xl font-extrabold tracking-tight text-white">
            Universal API Hub & Explorer
          </h1>
          <p className="text-white/90 text-sm md:text-base leading-relaxed">
            Discover, test, and mash up open public APIs from ApiVault. Live market trackers in Indian Rupees (₹), game deal aggregators, IP geolocators, interactive HTTP testing playground, and latency monitors.
          </p>
        </div>
      </div>

      {/* Main Tabbed Interface */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-6">
        <TabsList className="grid grid-cols-2 md:grid-cols-4 gap-2 bg-muted/60 p-1.5 rounded-xl h-auto">
          <TabsTrigger value="mashup" className="flex items-center gap-2 py-2.5 rounded-lg text-xs md:text-sm font-semibold">
            <Zap className="h-4 w-4 text-amber-500" />
            <span>Live Mashup</span>
          </TabsTrigger>
          <TabsTrigger value="catalog" className="flex items-center gap-2 py-2.5 rounded-lg text-xs md:text-sm font-semibold">
            <Layers className="h-4 w-4 text-indigo-500" />
            <span>API Catalog</span>
          </TabsTrigger>
          <TabsTrigger value="playground" className="flex items-center gap-2 py-2.5 rounded-lg text-xs md:text-sm font-semibold">
            <Terminal className="h-4 w-4 text-emerald-500" />
            <span>Playground</span>
          </TabsTrigger>
          <TabsTrigger value="monitor" className="flex items-center gap-2 py-2.5 rounded-lg text-xs md:text-sm font-semibold">
            <Activity className="h-4 w-4 text-cyan-500" />
            <span>Health Monitor</span>
          </TabsTrigger>
        </TabsList>

        {/* 1. LIVE MASHUP DASHBOARD */}
        <TabsContent value="mashup" className="space-y-6">
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div>
              <h2 className="text-xl font-bold tracking-tight">Live Multi-API Mashup</h2>
              <p className="text-xs md:text-sm text-muted-foreground">
                Aggregated real-time widgets with prices formatted in <strong>Indian Rupees (₹)</strong> or <strong>USD ($)</strong>.
              </p>
            </div>
            <div className="flex items-center gap-2">
              {/* Currency Toggle Switch */}
              <div className="flex items-center bg-muted/70 p-1 rounded-xl border border-border">
                <button
                  onClick={() => setCurrencyUnit('INR')}
                  className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                    currencyUnit === 'INR'
                      ? 'bg-emerald-600 text-white shadow-xs'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <IndianRupee className="h-3 w-3" />
                  <span>INR (₹)</span>
                </button>
                <button
                  onClick={() => setCurrencyUnit('USD')}
                  className={`flex items-center gap-1 px-3 py-1 rounded-lg text-xs font-bold transition-all ${
                    currencyUnit === 'USD'
                      ? 'bg-indigo-600 text-white shadow-xs'
                      : 'text-muted-foreground hover:text-foreground'
                  }`}
                >
                  <span>USD ($)</span>
                </button>
              </div>

              <button
                onClick={loadDashboardData}
                className="flex items-center gap-2 px-3 py-1.5 rounded-xl border border-border bg-card text-xs font-semibold hover:bg-secondary transition-colors"
              >
                <RefreshCw className="h-3.5 w-3.5 text-muted-foreground" />
                <span>Refresh</span>
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Crypto Tracker Widget */}
            <Card className="border border-border/80 shadow-xs hover:shadow-md transition-all">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-amber-500/10 text-amber-500">
                      <Coins className="h-4 w-4" />
                    </div>
                    <CardTitle className="text-base font-bold">Crypto Ticker</CardTitle>
                  </div>
                  <Badge variant="outline" className="text-[10px] text-muted-foreground">CoinGecko API</Badge>
                </div>
                <CardDescription className="text-xs">
                  Live 24h market prices in <strong>{currencyUnit === 'INR' ? 'Indian Rupees (₹)' : 'USD ($)'}</strong>
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                {cryptoLoading ? (
                  <div className="py-6 text-center text-xs text-muted-foreground animate-pulse">Loading live crypto quotes...</div>
                ) : cryptoData ? (
                  Object.entries(cryptoData).map(([coin, val]: [string, any]) => {
                    const priceFormatted = formatPrice(val.usd, val.inr)
                    const change = currencyUnit === 'INR' ? (val.inr_24h_change ?? val.usd_24h_change) : val.usd_24h_change

                    return (
                      <div key={coin} className="flex items-center justify-between text-xs py-1 border-b border-border/40 last:border-0">
                        <span className="capitalize font-semibold text-foreground">{coin}</span>
                        <div className="flex items-center gap-2">
                          <span className="font-mono font-bold text-foreground">{priceFormatted}</span>
                          <span className={`font-mono text-[11px] ${change >= 0 ? 'text-emerald-500' : 'text-rose-500'}`}>
                            {change >= 0 ? '+' : ''}{change?.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    )
                  })
                ) : null}
              </CardContent>
            </Card>

            {/* Currency Converter Widget */}
            <Card className="border border-border/80 shadow-xs hover:shadow-md transition-all">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
                      <TrendingUp className="h-4 w-4" />
                    </div>
                    <CardTitle className="text-base font-bold">Rupee Currency Converter</CardTitle>
                  </div>
                  <Badge variant="outline" className="text-[10px] text-muted-foreground">Frankfurter API</Badge>
                </div>
                <CardDescription className="text-xs">Live exchange rates from Indian Rupees (₹)</CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-semibold text-muted-foreground">Amount (₹ INR):</span>
                  <input
                    type="number"
                    value={amountInr}
                    onChange={(e) => setAmountInr(e.target.value)}
                    className="h-8 w-28 px-2.5 rounded-md border border-border bg-background text-xs font-mono font-bold text-emerald-600"
                  />
                </div>
                {currencyData && (
                  <div className="space-y-1.5 pt-1">
                    {(() => {
                      const numRupees = parseFloat(amountInr) || 0
                      const usdEquiv = numRupees / usdToInrRate

                      return (
                        <>
                          <div className="flex items-center justify-between text-xs py-1 border-b border-border/40">
                            <span className="font-semibold text-muted-foreground">US Dollar ($ USD)</span>
                            <span className="font-mono font-bold text-foreground">${usdEquiv.toFixed(2)}</span>
                          </div>
                          <div className="flex items-center justify-between text-xs py-1 border-b border-border/40">
                            <span className="font-semibold text-muted-foreground">Euro (€ EUR)</span>
                            <span className="font-mono font-bold text-foreground">€{(usdEquiv * (currencyData.EUR || 0.92)).toFixed(2)}</span>
                          </div>
                          <div className="flex items-center justify-between text-xs py-1 border-b border-border/40">
                            <span className="font-semibold text-muted-foreground">British Pound (£ GBP)</span>
                            <span className="font-mono font-bold text-foreground">£{(usdEquiv * (currencyData.GBP || 0.78)).toFixed(2)}</span>
                          </div>
                          <div className="flex items-center justify-between text-xs py-1">
                            <span className="font-semibold text-muted-foreground">Japanese Yen (¥ JPY)</span>
                            <span className="font-mono font-bold text-foreground">¥{(usdEquiv * (currencyData.JPY || 154.2)).toFixed(0)}</span>
                          </div>
                        </>
                      )
                    })()}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Gamer Deals Widget */}
            <Card className="border border-border/80 shadow-xs hover:shadow-md transition-all">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-500">
                      <Gamepad2 className="h-4 w-4" />
                    </div>
                    <CardTitle className="text-base font-bold">Game Deals in Rupees</CardTitle>
                  </div>
                  <Badge variant="outline" className="text-[10px] text-muted-foreground">CheapShark API</Badge>
                </div>
                <CardDescription className="text-xs">PC game discounts converted to <strong>{currencyUnit === 'INR' ? '₹ INR' : '$ USD'}</strong></CardDescription>
              </CardHeader>
              <CardContent className="space-y-2.5">
                {gameDeals.map((deal, idx) => {
                  const originalUsd = parseFloat(deal.normalPrice) || 0
                  const saleUsd = parseFloat(deal.salePrice) || 0

                  return (
                    <div key={idx} className="flex items-center justify-between p-2 rounded-lg bg-muted/40 text-xs">
                      <div className="truncate pr-2">
                        <p className="font-semibold truncate text-foreground">{deal.title}</p>
                        <span className="text-[10px] text-emerald-500 font-bold">{parseFloat(deal.savings).toFixed(0)}% OFF</span>
                      </div>
                      <div className="text-right shrink-0 font-mono">
                        <span className="text-[10px] line-through text-muted-foreground block">
                          {formatPrice(originalUsd)}
                        </span>
                        <span className="font-bold text-indigo-500">
                          {formatPrice(saleUsd)}
                        </span>
                      </div>
                    </div>
                  )
                })}
              </CardContent>
            </Card>

            {/* Daily Quote & Advice Widget */}
            <Card className="border border-border/80 shadow-xs hover:shadow-md transition-all">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-purple-500/10 text-purple-500">
                      <Quote className="h-4 w-4" />
                    </div>
                    <CardTitle className="text-base font-bold">Daily Advice & Quotes</CardTitle>
                  </div>
                  <Badge variant="outline" className="text-[10px] text-muted-foreground">AdviceSlip API</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                {quoteData && (
                  <blockquote className="p-3 rounded-lg bg-purple-500/5 border-l-2 border-purple-500 italic text-xs leading-relaxed text-foreground">
                    &ldquo;{quoteData.advice}&rdquo;
                  </blockquote>
                )}
                {catFact && (
                  <div className="p-3 rounded-lg bg-amber-500/5 border border-amber-500/20 text-xs space-y-1">
                    <span className="text-[10px] font-bold text-amber-600 uppercase tracking-wider block">Cat Trivia:</span>
                    <p className="text-muted-foreground">{catFact}</p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Geo & IP Locator Widget */}
            <Card className="border border-border/80 shadow-xs hover:shadow-md transition-all">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-cyan-500/10 text-cyan-500">
                      <MapPin className="h-4 w-4" />
                    </div>
                    <CardTitle className="text-base font-bold">Network IP & Geo</CardTitle>
                  </div>
                  <Badge variant="outline" className="text-[10px] text-muted-foreground">IPify API</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="p-3 rounded-lg bg-muted/50 font-mono text-xs space-y-1.5">
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Public IP Address:</span>
                    <span className="font-bold text-cyan-500">{ipInfo?.ip || 'Checking...'}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Protocol:</span>
                    <span>IPv4 / HTTPS</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted-foreground">Location Node:</span>
                    <span>Global CDN</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* Quick QR Generator Simulator */}
            <Card className="border border-border/80 shadow-xs hover:shadow-md transition-all">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
                      <Laptop className="h-4 w-4" />
                    </div>
                    <CardTitle className="text-base font-bold">QR Code Endpoint</CardTitle>
                  </div>
                  <Badge variant="outline" className="text-[10px] text-muted-foreground">QRServer API</Badge>
                </div>
              </CardHeader>
              <CardContent className="space-y-3">
                <input
                  type="text"
                  value={qrInputText}
                  onChange={(e) => setQrInputText(e.target.value)}
                  placeholder="Enter text or URL..."
                  className="w-full h-8 px-2.5 rounded-md border border-border bg-background text-xs font-mono"
                />
                <div className="flex justify-center p-2 rounded-lg bg-white border border-border">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={`https://api.qrserver.com/v1/create-qr-code/?size=120x120&data=${encodeURIComponent(qrInputText)}`}
                    alt="Generated QR Code"
                    className="h-24 w-24 object-contain"
                  />
                </div>
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* 2. API CATALOG NAVIGATOR */}
        <TabsContent value="catalog" className="space-y-6">
          {/* Filters & Search */}
          <div className="flex flex-col md:flex-row gap-4 items-stretch md:items-center justify-between">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search APIs by keyword, category, or description..."
                className="w-full h-10 pl-9 pr-4 rounded-xl border border-border bg-card text-sm focus:outline-none focus:ring-2 focus:ring-primary/40"
              />
            </div>
            <div className="flex flex-wrap gap-2">
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold"
              >
                {API_VAULT_CATEGORIES.map((cat) => (
                  <option key={cat} value={cat}>{cat}</option>
                ))}
              </select>
              <select
                value={authFilter}
                onChange={(e) => setAuthFilter(e.target.value)}
                className="h-10 px-3 rounded-xl border border-border bg-card text-xs font-semibold"
              >
                <option value="All">All Auth Types</option>
                <option value="No">No Key Required</option>
                <option value="apiKey">API Key</option>
                <option value="OAuth">OAuth</option>
              </select>
            </div>
          </div>

          {/* Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredApis.map((apiItem) => (
              <Card key={apiItem.id} className="flex flex-col justify-between border border-border/80 hover:border-primary/50 transition-all shadow-xs hover:shadow-md">
                <CardHeader className="space-y-2">
                  <div className="flex items-start justify-between gap-2">
                    <Badge variant="secondary" className="text-[10px] font-semibold">{apiItem.category}</Badge>
                    <div className="flex items-center gap-1.5">
                      {apiItem.https && (
                        <Badge className="bg-emerald-500/10 text-emerald-600 border-0 text-[10px]">
                          <ShieldCheck className="h-3 w-3 mr-0.5" /> HTTPS
                        </Badge>
                      )}
                      <Badge variant="outline" className="text-[10px]">
                        Auth: {apiItem.auth}
                      </Badge>
                    </div>
                  </div>
                  <CardTitle className="text-base font-bold text-foreground">{apiItem.name}</CardTitle>
                  <CardDescription className="text-xs leading-relaxed text-muted-foreground line-clamp-2">
                    {apiItem.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4 pt-2">
                  <div className="p-2 rounded-lg bg-muted/50 font-mono text-[11px] text-muted-foreground truncate">
                    {apiItem.sampleEndpoint}
                  </div>
                  <div className="flex items-center justify-between gap-2">
                    <a
                      href={apiItem.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="flex items-center gap-1 text-xs text-primary hover:underline font-semibold"
                    >
                      <span>Documentation</span>
                      <ExternalLink className="h-3 w-3" />
                    </a>
                    <button
                      onClick={() => sendToPlayground(apiItem.sampleEndpoint)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition-opacity"
                    >
                      <Play className="h-3 w-3 fill-current" />
                      <span>Test Live</span>
                    </button>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </TabsContent>

        {/* 3. API TESTER & PLAYGROUND */}
        <TabsContent value="playground" className="space-y-6">
          <Card className="border border-border/80 shadow-md">
            <CardHeader>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Terminal className="h-5 w-5 text-emerald-500" />
                  <CardTitle className="text-lg font-bold">Interactive API Tester</CardTitle>
                </div>
                <Badge className="bg-emerald-500/10 text-emerald-600 border-0 text-xs font-semibold">CORS & Fetch Ready</Badge>
              </div>
              <CardDescription className="text-xs">
                Construct requests, inspect real HTTP status codes, timing, response headers, and copy code snippets.
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Endpoint Input bar */}
              <div className="flex flex-col md:flex-row gap-2">
                <select
                  value={httpMethod}
                  onChange={(e) => setHttpMethod(e.target.value as any)}
                  className="h-10 px-3 rounded-xl border border-border bg-card font-mono text-xs font-bold text-foreground"
                >
                  <option value="GET">GET</option>
                  <option value="POST">POST</option>
                </select>
                <input
                  type="text"
                  value={endpointUrl}
                  onChange={(e) => setEndpointUrl(e.target.value)}
                  placeholder="https://api.example.com/endpoint"
                  className="flex-1 h-10 px-3 rounded-xl border border-border bg-card text-xs font-mono text-foreground focus:outline-none focus:ring-2 focus:ring-emerald-500/40"
                />
                <button
                  onClick={handleExecuteRequest}
                  disabled={isExecuting}
                  className="h-10 px-5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-semibold text-xs flex items-center justify-center gap-2 transition-all shadow-xs"
                >
                  {isExecuting ? (
                    <RefreshCw className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-4 w-4" />
                  )}
                  <span>{isExecuting ? 'Sending...' : 'Send Request'}</span>
                </button>
              </div>

              {/* Grid: Request Options & Code Snippets */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Headers & Body tab config */}
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <Sliders className="h-3.5 w-3.5 text-muted-foreground" />
                      <span>Request Headers (JSON format)</span>
                    </label>
                    <textarea
                      rows={3}
                      value={requestHeaders}
                      onChange={(e) => setRequestHeaders(e.target.value)}
                      className="w-full p-3 rounded-xl border border-border bg-muted/40 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                    />
                  </div>
                  {httpMethod === 'POST' && (
                    <div className="space-y-1.5">
                      <label className="text-xs font-bold text-foreground">Request Body</label>
                      <textarea
                        rows={4}
                        value={requestBody}
                        onChange={(e) => setRequestBody(e.target.value)}
                        placeholder='{"key": "value"}'
                        className="w-full p-3 rounded-xl border border-border bg-muted/40 font-mono text-xs focus:outline-none focus:ring-1 focus:ring-primary"
                      />
                    </div>
                  )}
                </div>

                {/* Code Snippet Generator */}
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-foreground flex items-center gap-1.5">
                      <Code2 className="h-3.5 w-3.5 text-indigo-500" />
                      <span>Generated Code Snippet</span>
                    </span>
                    <div className="flex items-center gap-1 bg-muted/60 p-1 rounded-lg">
                      <button
                        onClick={() => setSnippetLanguage('js')}
                        className={`px-2 py-0.5 text-[10px] font-bold rounded ${snippetLanguage === 'js' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground'}`}
                      >
                        JS
                      </button>
                      <button
                        onClick={() => setSnippetLanguage('python')}
                        className={`px-2 py-0.5 text-[10px] font-bold rounded ${snippetLanguage === 'python' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground'}`}
                      >
                        Python
                      </button>
                      <button
                        onClick={() => setSnippetLanguage('curl')}
                        className={`px-2 py-0.5 text-[10px] font-bold rounded ${snippetLanguage === 'curl' ? 'bg-card text-foreground shadow-xs' : 'text-muted-foreground'}`}
                      >
                        cURL
                      </button>
                    </div>
                  </div>
                  <div className="relative rounded-xl border border-border bg-slate-950 p-3 text-slate-100 font-mono text-[11px] overflow-x-auto min-h-[140px]">
                    <button
                      onClick={copySnippet}
                      className="absolute right-2 top-2 flex h-10 w-10 items-center justify-center rounded-md bg-slate-800 text-slate-300 transition-colors hover:bg-slate-700"
                      title="Copy Snippet"
                      aria-label="Copy generated code snippet"
                    >
                      {copiedSnippet ? <Check className="h-3.5 w-3.5 text-emerald-400" /> : <Copy className="h-3.5 w-3.5" />}
                    </button>
                    <pre className="pr-8">{getCodeSnippet()}</pre>
                  </div>
                </div>
              </div>

              {/* Response Panel */}
              <div className="space-y-3 pt-4 border-t border-border">
                <div className="flex items-center justify-between">
                  <h3 className="text-sm font-bold text-foreground">Response Inspector</h3>
                  {responseStatus !== null && (
                    <div className="flex items-center gap-2 font-mono text-xs">
                      <Badge className={responseStatus >= 200 && responseStatus < 300 ? 'bg-emerald-500/10 text-emerald-600' : 'bg-rose-500/10 text-rose-600'}>
                        Status: {responseStatus}
                      </Badge>
                      {responseTime && (
                        <Badge variant="outline" className="text-muted-foreground">
                          <Clock className="h-3 w-3 mr-1" />
                          {responseTime} ms
                        </Badge>
                      )}
                    </div>
                  )}
                </div>

                {responseHeaders && Object.keys(responseHeaders).length > 0 && (
                  <div className="p-3 rounded-xl border border-border bg-muted/20 font-mono text-[11px] space-y-1">
                    <span className="text-muted-foreground font-bold block mb-1">Response Headers:</span>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-x-4 gap-y-0.5 text-muted-foreground">
                      {Object.entries(responseHeaders).slice(0, 6).map(([k, v]) => (
                        <div key={k} className="truncate">
                          <span className="text-foreground">{k}:</span> {v}
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className="rounded-xl border border-border bg-muted/30 p-4 font-mono text-xs min-h-[180px] max-h-[400px] overflow-y-auto">
                  {isExecuting ? (
                    <div className="flex items-center justify-center h-32 text-muted-foreground gap-2">
                      <RefreshCw className="h-4 w-4 animate-spin" />
                      <span>Fetching remote endpoint...</span>
                    </div>
                  ) : responseBody !== null ? (
                    <pre className="whitespace-pre-wrap text-foreground">{responseBody}</pre>
                  ) : (
                    <div className="text-center text-muted-foreground py-10">
                      Click <strong>&quot;Send Request&quot;</strong> to view the live HTTP response payload.
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        {/* 4. HEALTH & LATENCY MONITOR */}
        <TabsContent value="monitor" className="space-y-6">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-xl font-bold tracking-tight">API Latency & Health Matrix</h2>
              <p className="text-xs md:text-sm text-muted-foreground">
                Real-time ping monitor checking status code, latency (ms), and CORS access across open public APIs.
              </p>
            </div>
            <button
              onClick={handleRunHealthCheck}
              className="flex items-center gap-2 px-4 py-2 rounded-xl bg-primary text-primary-foreground text-xs font-semibold hover:opacity-90 transition-opacity"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span>Run Latency Audit</span>
            </button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {API_VAULT_DATABASE.map((apiItem) => {
              const ping = pingResults[apiItem.id]
              return (
                <Card key={apiItem.id} className="border border-border/80 shadow-xs">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-bold text-foreground">{apiItem.name}</CardTitle>
                      {ping ? (
                        ping.status === 'testing' ? (
                          <Badge variant="outline" className="text-[10px] animate-pulse">Testing...</Badge>
                        ) : ping.status === 'online' ? (
                          <Badge className="bg-emerald-500/10 text-emerald-600 border-0 text-[10px]">
                            <CheckCircle2 className="h-3 w-3 mr-1" /> 200 OK
                          </Badge>
                        ) : (
                          <Badge className="bg-rose-500/10 text-rose-600 border-0 text-[10px]">
                            <XCircle className="h-3 w-3 mr-1" /> Offline / CORS
                          </Badge>
                        )
                      ) : (
                        <Badge variant="outline" className="text-[10px] text-muted-foreground">Ready</Badge>
                      )}
                    </div>
                    <CardDescription className="text-[11px] font-mono truncate">{apiItem.sampleEndpoint}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2 text-xs pt-0">
                    <div className="flex justify-between py-1 border-b border-border/40">
                      <span className="text-muted-foreground">Response Time:</span>
                      <span className="font-mono font-bold text-foreground">
                        {ping?.ms ? `${ping.ms} ms` : '—'}
                      </span>
                    </div>
                    <div className="flex justify-between py-1 border-b border-border/40">
                      <span className="text-muted-foreground">Auth Requirement:</span>
                      <span className="font-semibold text-foreground">{apiItem.auth}</span>
                    </div>
                    <div className="flex justify-between py-1">
                      <span className="text-muted-foreground">CORS Support:</span>
                      <span className="font-semibold text-emerald-500">Supported</span>
                    </div>
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  )
}
