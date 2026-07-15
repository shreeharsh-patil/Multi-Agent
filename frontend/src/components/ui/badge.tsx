import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-[6px] border px-2 py-0.5 text-[10px] font-semibold tracking-wider uppercase transition-colors focus:outline-none',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-white text-black',
        secondary: 'border-[#2A2A2F] bg-[#1A1A1D] text-[#F5F5F7]',
        destructive: 'border-transparent bg-red-950/20 text-red-400',
        outline: 'border-[#2A2A2F] text-[#A1A1AA]',
        success: 'border-transparent bg-emerald-500/10 text-emerald-400',
        warning: 'border-transparent bg-amber-500/10 text-amber-400',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  },
)

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />
}

export { Badge, badgeVariants }
