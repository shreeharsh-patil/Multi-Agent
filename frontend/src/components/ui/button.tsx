import { forwardRef } from 'react'
import { Slot } from '@radix-ui/react-slot'
import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const buttonVariants = cva(
  'inline-flex items-center justify-center whitespace-nowrap rounded-[8px] text-sm font-medium transition-all duration-200 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50 active:scale-[0.98]',
  {
    variants: {
      variant: {
        default: 'bg-[#cc785c] text-white hover:bg-[#a9583e] shadow-sm',
        destructive: 'bg-red-950/10 text-red-600 border border-red-200/50 hover:bg-red-950/15',
        outline: 'border border-[#e6dfd8] bg-[#faf9f5] text-[#141413] hover:bg-[#f5f0e8]',
        secondary: 'bg-[#efe9de] border border-[#e6dfd8] text-[#141413] hover:bg-[#e8e0d2]',
        ghost: 'hover:bg-[#efe9de] hover:text-[#141413] text-[#6c6a64]',
        link: 'text-[#cc785c] underline-offset-4 hover:underline',
      },
      size: {
        default: 'h-10 px-5 py-2',
        sm: 'h-9 rounded-[6px] px-3',
        lg: 'h-11 rounded-[8px] px-8',
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
