'use client'

import { signIn } from 'next-auth/react'
import Image from 'next/image'
import Link from 'next/link'
import { Button } from '@/components/ui/button'

export default function LoginPage() {
  return (
    <div className="w-full max-w-md p-8 rounded-[12px] border border-border bg-card shadow-xs relative overflow-hidden animate-fade-in">
      {/* Subtle top divider line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-primary" />
      
      <div className="text-center space-y-6 mb-8">
        <div className="flex justify-center">
          <div className="h-12 w-12 rounded-[8px] border border-border bg-secondary flex items-center justify-center transition-transform hover:scale-105 duration-300 shadow-xs">
            <Image src="/logo.png" alt="Agentic Logo" width={24} height={24} className="h-6 w-6 object-contain" />
          </div>
        </div>
        <div className="space-y-2">
          <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-foreground">
            Agentic
          </h1>
          <p className="text-sm text-muted-foreground">
            An elegant, editorial workspace for collaborative AI agents.
          </p>
        </div>
      </div>

      <div className="space-y-4">
        <Button
          variant="outline"
          className="w-full h-12 text-[14px] font-medium gap-3 rounded-[8px] shadow-xs cursor-pointer"
          onClick={() => signIn('google', { callbackUrl: '/dashboard' })}
        >
          <svg className="h-[18px] w-[18px]" viewBox="0 0 48 48" xmlns="http://www.w3.org/2000/svg">
            <path fill="#FFC107" d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"/>
            <path fill="#FF3D00" d="m6.306 14.691 6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"/>
            <path fill="#4CAF50" d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0 1 24 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"/>
            <path fill="#1976D2" d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 0 1-4.087 5.571l.003-.002 6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"/>
          </svg>
          Continue with Google
        </Button>
      </div>

      <p className="text-center text-xs text-muted-foreground mt-8 leading-relaxed">
        By signing in, you agree to our{' '}
        <Link href="/terms" target="_blank" className="underline underline-offset-2 hover:text-foreground transition-colors font-medium">
          Terms of Service
        </Link>{' '}
        and{' '}
        <Link href="/privacy" target="_blank" className="underline underline-offset-2 hover:text-foreground transition-colors font-medium">
          Privacy Policy
        </Link>
      </p>
    </div>
  )
}
