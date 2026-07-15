import { forwardRef } from 'react'
import { cn } from '@/lib/utils'

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, type, ...props }, ref) => {
    return (
      <input
        type={type}
        className={cn(
          'flex h-10 w-full rounded-[8px] border border-[#e6dfd8] bg-[#faf9f5] px-4 py-2 text-sm text-[#141413] placeholder:text-[#6c6a64] focus-visible:outline-none focus-visible:border-[#cc785c] focus-visible:ring-1 focus-visible:ring-[#cc785c]/30 transition-all duration-200 disabled:cursor-not-allowed disabled:opacity-50',
          className,
        )}
        ref={ref}
        {...props}
      />
    )
  },
)
Input.displayName = 'Input'

export { Input }
