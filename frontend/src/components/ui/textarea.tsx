import * as React from 'react'
import { cn } from '@/lib/utils'

export interface TextareaProps extends React.TextareaHTMLAttributes<HTMLTextAreaElement> {}

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(
  ({ className, ...props }, ref) => {
    return (
      <textarea
        className={cn(
          'flex min-h-[80px] w-full min-w-0 rounded-[8px] border border-[#e6dfd8] bg-[#faf9f5] px-4 py-3 text-base text-[#141413] placeholder:text-[#6c6a64] focus-visible:outline-none focus-visible:border-[#cc785c] focus-visible:ring-1 focus-visible:ring-[#cc785c]/30 transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50 sm:text-sm',
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
