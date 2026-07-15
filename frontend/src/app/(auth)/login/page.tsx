'use client'

import { signIn } from 'next-auth/react'
import { Button } from '@/components/ui/button'
import { Chrome, Sparkles } from 'lucide-react'

export default function LoginPage() {
  return (
    <div className="w-full max-w-md space-y-8 p-8">
      <div className="text-center space-y-4">
        <div className="flex justify-center">
          <div className="h-16 w-16 rounded-2xl bg-primary flex items-center justify-center">
            <Sparkles className="h-8 w-8 text-primary-foreground" />
          </div>
        </div>
        <h1 className="text-3xl font-bold tracking-tight">Multi-Agent AI Platform</h1>
        <p className="text-muted-foreground">
          Sign in to access your intelligent AI workspace
        </p>
      </div>

      <div className="space-y-4 flex flex-col">
        <Button
          variant="outline"
          className="w-full h-12 text-base gap-3"
          onClick={() => signIn('google', { callbackUrl: '/dashboard' })}
        >
          <Chrome className="h-5 w-5" />
          Continue with Google
        </Button>

        <Button
          variant="secondary"
          className="w-full h-12 text-base gap-3 border border-dashed border-zinc-700 bg-zinc-900/50 hover:bg-zinc-800 text-zinc-300 hover:text-white"
          onClick={() => signIn('credentials', { callbackUrl: '/dashboard' })}
        >
          <Sparkles className="h-5 w-5 text-violet-400" />
          Developer Quick Login
        </Button>
      </div>

      <p className="text-center text-xs text-muted-foreground">
        By signing in, you agree to our Terms of Service and Privacy Policy
      </p>
    </div>
  )
}
