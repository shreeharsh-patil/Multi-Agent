import { cva, type VariantProps } from 'class-variance-authority'
import { cn } from '@/lib/utils'

const badgeVariants = cva(
  'inline-flex items-center rounded-full border px-2.5 py-0.5 text-[10px] font-medium tracking-wide transition-colors focus:outline-none',
  {
    variants: {
      variant: {
        default: 'border-transparent bg-[#efe9de] text-[#141413]',
        secondary: 'border-transparent bg-[#efe9de] text-[#141413]',
        destructive: 'border-transparent bg-red-950/10 text-red-600',
        outline: 'border-[#e6dfd8] text-[#6c6a64]',
        success: 'border-transparent bg-[#5db872]/15 text-[#5db872]',
        warning: 'border-transparent bg-[#e8a55a]/15 text-[#e8a55a]',
        coral: 'border-transparent bg-[#cc785c] text-white uppercase tracking-[1.5px]',
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
