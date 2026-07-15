'use client'

import { signIn } from 'next-auth/react'
import { Button } from '@/components/ui/button'

function LogoSpike({ className = "h-5 w-5" }: { className?: string }) {
  return (
    <svg className={`text-primary fill-current shrink-0 ${className}`} viewBox="0 0 24 24">
      <path d="M12 2c.4 3.5 1.5 6.5 4 9 2.5 2.5 5.5 3.6 9 4-3.5.4-6.5 1.5-9 4-2.5 2.5-3.6 5.5-4 9-.4-3.5-1.5-6.5-4-9-2.5-2.5-5.5-3.6-9-4 3.5-.4 6.5-1.5 9-4 2.5-2.5 3.6-5.5 4-9z" />
    </svg>
  )
}

export default function LoginPage() {
  return (
    <div className="w-full max-w-md p-8 rounded-[12px] border border-border bg-card shadow-xs relative overflow-hidden animate-fade-in">
      {/* Subtle top divider line */}
      <div className="absolute top-0 left-0 right-0 h-[2px] bg-primary" />
      
      <div className="text-center space-y-6 mb-8">
        <div className="flex justify-center">
          <div className="h-12 w-12 rounded-[8px] border border-border bg-secondary flex items-center justify-center transition-transform hover:scale-105 duration-300 shadow-xs">
            <LogoSpike className="h-5 w-5" />
          </div>
        </div>
        <div className="space-y-2">
          <h1 className="text-3xl font-sans font-normal tracking-[-0.03em] text-foreground">
            Agents
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
          <svg className="h-[18px] w-[18px]" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z" fill="#FBBC05"/>
            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z" fill="#EA4335"/>
          </svg>
          Continue with Google
        </Button>
      </div>

      <p className="text-center text-xs text-muted-foreground mt-8 leading-relaxed">
        By signing in, you agree to our Terms of Service<br />and Privacy Policy
      </p>
    </div>
  )
}
