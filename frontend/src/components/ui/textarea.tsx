import * as React from 'react'
import { cn } from '@/lib/utils'

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          'flex min-h-[80px] w-full rounded-[20px] border border-[#2A2A2F] bg-[#1A1A1D] px-4 py-3 text-sm text-[#F5F5F7] placeholder:text-[#71717A] focus-visible:outline-none focus-visible:border-[#71717A] transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        ref={ref}
        {...props}
      />
    )
  },
)
Textarea.displayName = 'Textarea'

export { Textarea }
