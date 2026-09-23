import type { Metadata } from 'next'
import { Inter, Cormorant_Garamond, JetBrains_Mono, IBM_Plex_Sans, Courier_Prime } from 'next/font/google'
import './globals.css'
import 'katex/dist/katex.min.css'
import { ThemeProvider } from '@/components/theme-provider'
import { SessionProvider } from '@/components/session-provider'
import { Toaster } from 'sonner'

const inter = Inter({
  variable: '--font-sans',
  subsets: ['latin'],
})

const cormorant = Cormorant_Garamond({
  variable: '--font-serif',
  subsets: ['latin'],
  weight: ['400', '500', '600', '700'],
})

const jetbrainsMono = JetBrains_Mono({
  variable: '--font-mono',
  subsets: ['latin'],
})

const ibmPlexSans = IBM_Plex_Sans({
  variable: '--font-ibm-plex',
  subsets: ['latin'],
  weight: ['300', '400', '500', '600'],
  display: 'swap',
})

const courierPrime = Courier_Prime({
  variable: '--font-pixel',
  weight: ['400', '700'],
  subsets: ['latin'],
  display: 'swap',
})

export const viewport = {
  width: 'device-width',
  initialScale: 1,
}

export const metadata: Metadata = {
  title: 'Agentic — AI Agent Workspace',
  description: 'Chat with multiple specialized AI agents, research the web, query documents with RAG, generate quizzes, create study plans, and build custom agents — all in one collaborative workspace.',
  keywords: ['AI agents', 'multi-agent', 'RAG', 'knowledge base', 'AI workspace', 'study tools', 'research assistant', 'custom agents', 'LLM orchestration'],
  authors: [{ name: 'Agentic' }],
  openGraph: {
    title: 'Agentic — AI Agent Workspace',
    description: 'Chat with multiple specialized AI agents, research the web, query documents with RAG, and more.',
    type: 'website',
    siteName: 'Agentic',
  },
  twitter: {
    card: 'summary_large_image',
    title: 'Agentic — AI Agent Workspace',
    description: 'Chat with multiple specialized AI agents, research the web, query documents with RAG, and more.',
  },
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/favicon.png', type: 'image/png' },
    ],
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${cormorant.variable} ${jetbrainsMono.variable} ${ibmPlexSans.variable} ${courierPrime.variable} antialiased font-sans bg-background text-foreground`}>
        <ThemeProvider attribute="class" defaultTheme="light" forcedTheme="light" enableSystem={false}>
          <SessionProvider>
            {children}
          </SessionProvider>
          <Toaster richColors closeButton position="top-right" />
        </ThemeProvider>
      </body>
    </html>
  )
}
