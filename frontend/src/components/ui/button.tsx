import { forwardRef } from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-[24px] text-sm font-medium transition-all duration-200 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]',
  {
    variants: {
      variant: {
        default: 'bg-white text-black hover:bg-zinc-200 shadow-sm',
        destructive: 'bg-red-950/20 text-red-400 border border-red-900/30 hover:bg-red-900/25',
        outline: 'border border-[#2F2F2F] bg-transparent text-[#F9F9F9] hover:bg-[#2F2F2F]',
        secondary: 'bg-[#2F2F2F] border border-[#2F2F2F] text-[#F9F9F9] hover:bg-[#3F3F3F]',
        ghost: 'hover:bg-[#2F2F2F] hover:text-[#F9F9F9] text-[#B4B4B4]',
        link: 'text-white underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-5 py-2',
        sm: 'h-9 rounded-[20px] px-3',
        lg: 'h-11 rounded-[24px] px-8',
        icon: 'h-10 w-10',
      },
    },
    defaultVariants: {
      variant: 'default',
      size: 'default',
    },
  },
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    const Comp = asChild ? Slot : 'button'
    return (
      <Comp
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  },
)
Button.displayName = 'Button'

export { Button, buttonVariants }
