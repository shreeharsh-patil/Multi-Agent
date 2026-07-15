import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-[20px] border px-2.5 py-0.5 text-[10px] font-medium tracking-wide transition-colors focus:outline-none',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-[#2F2F2F] text-white',
        secondary: 'border-[#2F2F2F] bg-[#2F2F2F] text-[#F9F9F9]',
        destructive: 'border-transparent bg-red-950/20 text-red-400',
        outline: 'border-[#2F2F2F] text-[#B4B4B4]',
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
