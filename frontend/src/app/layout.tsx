import type { Metadata } from 'next'
import { Inter, Cormorant_Garamond, JetBrains_Mono } from 'next/font/google'
import './globals.css'
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

export const metadata: Metadata = {
  title: 'Agents - AI Workspace',
  description: 'An elegant, editorial collaborative multi-agent platform',
  icons: {
    icon: '/logo.png',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${cormorant.variable} ${jetbrainsMono.variable} antialiased font-sans bg-background text-foreground`}>
        <ThemeProvider attribute="class" defaultTheme="light" forcedTheme="light" enableSystem={false}>
          <SessionProvider>
            {children}
          </SessionProvider>
          <Toaster richColors position="top-right" />
        </ThemeProvider>
      </body>
    </html>
  )
}

