import type { Config } from 'tailwindcss'
import animate from 'tailwindcss-animate'
import typography from '@tailwindcss/typography'

const config: Config = {
  darkMode: ['class'],
  content: [
    './src/pages/**/*.{ts,tsx}',
    './src/components/**/*.{ts,tsx}',
    './src/app/**/*.{ts,tsx}',
  ],
  theme: {
    container: {
      center: true,
      padding: '2rem',
      screens: {
        '2xl': '1400px',
      },
    },
    extend: {
      // Compatibility tokens used throughout the existing UI. These names are
      // first-class in newer Tailwind/shadcn stacks but need explicit values
      // while this app remains on Tailwind CSS v3.
      spacing: {
        '4.5': '1.125rem',
      },
      fontSize: {
        '4.5xl': ['2.75rem', { lineHeight: '1' }],
      },
      boxShadow: {
        xs: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
      },
      transitionDuration: {
        '350': '350ms',
      },
      backdropBlur: {
        xs: '2px',
      },
      fontFamily: {
        sans: ['var(--font-sans)', 'var(--font-ibm-plex)', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        serif: ['var(--font-serif)', 'Georgia', 'serif'],
        mono: ['var(--font-mono)', 'monospace'],
        pixel: ['var(--font-pixel)', 'monospace'],
      },
      colors: {
        border: 'hsl(var(--border))',
        input: 'hsl(var(--input))',
        ring: 'hsl(var(--ring))',
        background: 'hsl(var(--background))',
        foreground: 'hsl(var(--foreground))',
        primary: {
          DEFAULT: 'hsl(var(--primary))',
          foreground: 'hsl(var(--primary-foreground))',
        },
        secondary: {
          DEFAULT: 'hsl(var(--secondary))',
          foreground: 'hsl(var(--secondary-foreground))',
        },
        destructive: {
          DEFAULT: 'hsl(var(--destructive))',
          foreground: 'hsl(var(--destructive-foreground))',
        },
        muted: {
          DEFAULT: 'hsl(var(--muted))',
          foreground: 'hsl(var(--muted-foreground))',
        },
        accent: {
          DEFAULT: 'hsl(var(--accent))',
          foreground: 'hsl(var(--accent-foreground))',
        },
        popover: {
          DEFAULT: 'hsl(var(--popover))',
          foreground: 'hsl(var(--popover-foreground))',
        },
        card: {
          DEFAULT: 'hsl(var(--card))',
          foreground: 'hsl(var(--card-foreground))',
        },
        sidebar: {
          DEFAULT: 'hsl(var(--sidebar-background))',
          foreground: 'hsl(var(--sidebar-foreground))',
          border: 'hsl(var(--sidebar-border))',
          accent: 'hsl(var(--sidebar-accent))',
          'accent-foreground': 'hsl(var(--sidebar-accent-foreground))',
          ring: 'hsl(var(--sidebar-ring))',
        },
      },
      borderRadius: {
        lg: 'var(--radius)',
        md: 'calc(var(--radius) - 2px)',
        sm: 'calc(var(--radius) - 4px)',
      },
      keyframes: {
        'accordion-down': {
          from: { height: '0' },
          to: { height: 'var(--radix-accordion-content-height)' },
        },
        'accordion-up': {
          from: { height: 'var(--radix-accordion-content-height)' },
          to: { height: '0' },
        },
        'fade-in': {
          from: { opacity: '0' },
          to: { opacity: '1' },
        },
        'slide-in': {
          from: { transform: 'translateX(-10px)', opacity: '0' },
          to: { transform: 'translateX(0)', opacity: '1' },
        },
        'marquee-left': {
          from: { transform: 'translateX(0)' },
          to: { transform: 'translateX(-33.333%)' },
        },
        'marquee-right': {
          from: { transform: 'translateX(-33.333%)' },
          to: { transform: 'translateX(0)' },
        },
        'word-reveal': {
          '0%': { opacity: '0', filter: 'blur(24px)', transform: 'translateY(24px)' },
          '60%': { filter: 'blur(3px)', opacity: '0.85' },
          '100%': { opacity: '1', filter: 'blur(0px)', transform: 'translateY(0px)' },
        },
        'fade-up': {
          from: { opacity: '0', transform: 'translateY(20px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'fade-in-up': {
          from: { opacity: '0', transform: 'translateY(8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'row-slide-in': {
          from: { opacity: '0', transform: 'translateY(10px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'pr-slide-in': {
          from: { opacity: '0', transform: 'translateY(-8px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'status-pulse': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.4' },
        },
        'fade-slide': {
          from: { opacity: '0', transform: 'translateX(-5px)' },
          to: { opacity: '1', transform: 'translateX(0)' },
        },
        'log-in': {
          from: { opacity: '0', transform: 'translateY(3px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        'glitch-shift': {
          '0%, 100%': { transform: 'translate(0)' },
          '33%': { transform: 'translate(-2px, 2px)' },
          '66%': { transform: 'translate(2px, -2px)' },
        },
        'glitch-opacity': {
          '0%, 100%': { opacity: '1' },
          '50%': { opacity: '0.8' },
        },
        'ping-slow': {
          '75%, 100%': { transform: 'scale(2.2)', opacity: '0' },
        },
      },
      animation: {
        'accordion-down': 'accordion-down 0.2s ease-out',
        'accordion-up': 'accordion-up 0.2s ease-out',
        'fade-in': 'fade-in 0.3s ease-out',
        'slide-in': 'slide-in 0.3s ease-out',
        'marquee-left': 'marquee-left 28s linear infinite',
        'marquee-right': 'marquee-right 22s linear infinite',
        'word-reveal': 'word-reveal 1.2s cubic-bezier(0.16,1,0.3,1) 0.3s forwards',
        'fade-up': 'fade-up 0.7s cubic-bezier(0.16,1,0.3,1) forwards',
        'fade-in-up': 'fade-in-up 0.5s cubic-bezier(0.16,1,0.3,1) both',
        'row-slide-in': 'row-slide-in 0.4s cubic-bezier(0.16,1,0.3,1) both',
        'pr-slide-in': 'pr-slide-in 0.4s cubic-bezier(0.16,1,0.3,1) both',
        'status-pulse': 'status-pulse 2s ease-in-out infinite',
        'fade-slide': 'fade-slide 0.3s ease both',
        'log-in': 'log-in 0.2s ease forwards',
        'glitch-shift': 'glitch-shift 5s infinite ease-in-out, glitch-opacity 3s infinite ease-in-out',
      },
    },
  },
  plugins: [animate, typography],
}

export default config
