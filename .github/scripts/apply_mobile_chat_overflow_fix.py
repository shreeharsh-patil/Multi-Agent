from pathlib import Path


def replace_once(path: str, old: str, new: str, label: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    if new in text:
        print(f"already applied: {label}")
        return
    if old not in text:
        raise RuntimeError(f"missing expected block for {label}: {path}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"applied: {label}")


# Chat: constrain the Radix viewport's intrinsic wrapper so one wide markdown
# child cannot widen/clamp the entire conversation on small screens.
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<ScrollArea ref={scrollRef} className="h-full w-full min-w-0 px-2 py-3 sm:px-6 sm:py-6">',
    '<ScrollArea\n              ref={scrollRef}\n              className="h-full w-full min-w-0 overflow-x-hidden px-2 py-3 sm:px-6 sm:py-6"\n              viewportClassName="overflow-x-hidden [&>div]:!block [&>div]:w-full [&>div]:min-w-0 [&>div]:max-w-full"\n            >',
    "constrain chat scroll viewport",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<div className="mx-auto w-full min-w-0 max-w-none space-y-6">',
    '<div className="mx-auto w-full min-w-0 max-w-full space-y-6 overflow-x-hidden">',
    "constrain chat feed width",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    "<div key={msg.id} className={`flex min-w-0 gap-2 sm:gap-3.5 ${msg.role === 'user' ? 'justify-end' : ''}`}>",
    "<div key={msg.id} className={`flex w-full max-w-full min-w-0 overflow-x-hidden gap-2 sm:gap-3.5 ${msg.role === 'user' ? 'justify-end' : ''}`}>",
    "constrain message row width",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<div className={`flex w-full min-w-0 max-w-[calc(100%_-_2.25rem)] flex-col sm:max-w-[92%] ${msg.role === \'user\' ? \'items-end\' : \'items-start\'}`}>',
    '<div className={`flex w-full min-w-0 max-w-[calc(100%_-_2.25rem)] flex-col overflow-hidden sm:max-w-[92%] ${msg.role === \'user\' ? \'items-end\' : \'items-start\'}`}>',
    "constrain message column width",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<div className="group relative max-w-full min-w-0">',
    '<div className="group relative max-w-full min-w-0 overflow-hidden">',
    "clip message group to column",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<div className="w-full min-w-0 max-w-full break-words text-xs leading-relaxed [overflow-wrap:anywhere] sm:text-sm">',
    '<div className="w-full min-w-0 max-w-full overflow-hidden break-words text-xs leading-relaxed [overflow-wrap:anywhere] [&>*]:max-w-full sm:text-sm">',
    "contain markdown output",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<p className="mb-2 last:mb-0 leading-relaxed">{children}</p>',
    '<p className="mb-2 max-w-full break-words leading-relaxed [overflow-wrap:anywhere] last:mb-0">{children}</p>',
    "wrap markdown paragraphs",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<li className="leading-relaxed">{children}</li>',
    '<li className="max-w-full break-words leading-relaxed [overflow-wrap:anywhere]">{children}</li>',
    "wrap markdown list items",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<div className="my-4 w-full overflow-x-auto rounded-xl border border-border/80 bg-card/60 shadow-sm backdrop-blur-sm scrollbar-thin">',
    '<div className="my-4 w-full min-w-0 max-w-full overflow-x-auto overscroll-x-contain rounded-xl border border-border/80 bg-card/60 shadow-sm backdrop-blur-sm scrollbar-thin">',
    "contain markdown tables",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/40 border-r border-border/30 last:border-r-0">{children}</th>',
    '<th className="whitespace-normal break-words px-3 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/40 border-r border-border/30 last:border-r-0 [overflow-wrap:anywhere] sm:px-4">{children}</th>',
    "wrap table headings",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<td className="px-4 py-3 align-top border-r border-border/20 last:border-r-0 leading-relaxed font-normal">{children}</td>',
    '<td className="whitespace-normal break-words px-3 py-3 align-top border-r border-border/20 last:border-r-0 leading-relaxed font-normal [overflow-wrap:anywhere] sm:px-4">{children}</td>',
    "wrap table cells",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    'className="inline-flex items-center gap-1.5 px-2 py-1 text-[11px] rounded-full bg-primary/10 text-primary border border-primary/20 hover:bg-primary/20 transition-colors max-w-full"',
    'className="inline-flex max-w-full min-w-0 items-center gap-1.5 overflow-hidden rounded-full border border-primary/20 bg-primary/10 px-2 py-1 text-[11px] text-primary transition-colors hover:bg-primary/20"',
    "constrain citation pills",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<span className="truncate">{cit.file_name || \'Document\'}</span>',
    '<span className="min-w-0 truncate">{cit.file_name || \'Document\'}</span>',
    "allow citation label shrink",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<div className="shrink-0 border-t border-border bg-background px-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))] pt-2.5 sm:px-6 sm:py-4">',
    '<div className="shrink-0 max-w-full overflow-x-hidden border-t border-border bg-background px-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))] pt-2.5 sm:px-6 sm:py-4">',
    "contain mobile composer",
)
replace_once(
    "frontend/src/app/(dashboard)/chat/page.tsx",
    '<div className="relative flex min-h-[56px] w-full min-w-0 items-end rounded-[16px] border border-border bg-card p-1.5 shadow-xs transition-all duration-200 focus-within:border-primary/45 focus-within:ring-1 focus-within:ring-primary/10 sm:items-center sm:p-2">',
    '<div className="relative flex min-h-[56px] w-full min-w-0 max-w-full items-end overflow-hidden rounded-[16px] border border-border bg-card p-1.5 shadow-xs transition-all duration-200 focus-within:border-primary/45 focus-within:ring-1 focus-within:ring-primary/10 sm:items-center sm:p-2">',
    "contain composer row",
)

# ScrollArea: allow callers to target the Radix viewport without changing every
# existing ScrollArea instance.
replace_once(
    "frontend/src/components/ui/scroll-area.tsx",
    '''const ScrollArea = forwardRef<\n  React.ElementRef<typeof ScrollAreaPrimitive.Root>,\n  React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root>\n>(({ className, children, ...props }, ref) => (''',
    '''type ScrollAreaProps = React.ComponentPropsWithoutRef<typeof ScrollAreaPrimitive.Root> & {\n  viewportClassName?: string\n}\n\nconst ScrollArea = forwardRef<\n  React.ElementRef<typeof ScrollAreaPrimitive.Root>,\n  ScrollAreaProps\n>(({ className, viewportClassName, children, ...props }, ref) => (''',
    "add viewportClassName prop",
)
replace_once(
    "frontend/src/components/ui/scroll-area.tsx",
    '<ScrollAreaPrimitive.Viewport className="h-full w-full min-w-0 rounded-[inherit]">',
    '<ScrollAreaPrimitive.Viewport className={cn("h-full w-full min-w-0 rounded-[inherit]", viewportClassName)}>',
    "apply viewportClassName",
)

# Shared markdown: prevent rendered information elsewhere from expanding its
# parent on mobile; wide tables/code still scroll inside their own wrappers.
replace_once(
    "frontend/src/components/markdown-renderer.tsx",
    '<div className={`prose min-w-0 max-w-full break-words text-sm leading-relaxed [overflow-wrap:anywhere] dark:prose-invert ${className}`}>',
    '<div className={`prose min-w-0 max-w-full overflow-hidden break-words text-sm leading-relaxed [overflow-wrap:anywhere] [&>*]:max-w-full dark:prose-invert ${className}`}>',
    "contain shared markdown output",
)
replace_once(
    "frontend/src/components/markdown-renderer.tsx",
    '<td className="px-4 py-3 align-top border-r border-border/20 last:border-r-0 leading-relaxed font-normal">',
    '<td className="whitespace-normal break-words px-3 py-3 align-top border-r border-border/20 last:border-r-0 leading-relaxed font-normal [overflow-wrap:anywhere] sm:px-4">',
    "wrap shared table cells",
)
replace_once(
    "frontend/src/components/markdown-renderer.tsx",
    '<th className="px-4 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/40 border-r border-border/30 last:border-r-0">',
    '<th className="whitespace-normal break-words px-3 py-3 text-xs font-semibold uppercase tracking-wider text-muted-foreground bg-muted/40 border-r border-border/30 last:border-r-0 [overflow-wrap:anywhere] sm:px-4">',
    "wrap shared table headings",
)

# Generated-image error/mobile actions must wrap instead of forcing a wide row.
replace_once(
    "frontend/src/components/image-preview-card.tsx",
    '<div className="flex items-center gap-2 mt-2">',
    '<div className="mt-2 flex w-full flex-col items-stretch gap-2 sm:w-auto sm:flex-row sm:items-center">',
    "stack image error actions on mobile",
)
replace_once(
    "frontend/src/components/image-preview-card.tsx",
    '<div className="flex items-center justify-end gap-2 border-t border-border bg-card p-2 md:hidden">',
    '<div className="flex max-w-full flex-wrap items-center justify-end gap-2 border-t border-border bg-card p-2 md:hidden">',
    "wrap mobile image actions",
)

# Read-only shared chats get the same viewport-width guarantees.
replace_once(
    "frontend/src/app/shared/chat/[token]/page.tsx",
    '<Card className="min-w-0 space-y-5 p-3 sm:space-y-6 sm:p-8">',
    '<Card className="min-w-0 max-w-full space-y-5 overflow-hidden p-3 sm:space-y-6 sm:p-8">',
    "contain shared chat card",
)
replace_once(
    "frontend/src/app/shared/chat/[token]/page.tsx",
    "<div key={index} className={`flex min-w-0 gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}>",
    "<div key={index} className={`flex w-full max-w-full min-w-0 overflow-hidden gap-3 ${message.role === 'user' ? 'justify-end' : ''}`}>",
    "contain shared chat rows",
)
replace_once(
    "frontend/src/app/shared/chat/[token]/page.tsx",
    "<div className={`min-w-0 max-w-[92%] rounded-xl px-3 py-3 text-sm sm:max-w-[85%] sm:px-4 ${message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'}`}>",
    "<div className={`min-w-0 max-w-[92%] overflow-hidden rounded-xl px-3 py-3 text-sm sm:max-w-[85%] sm:px-4 ${message.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-secondary text-secondary-foreground'}`}>",
    "contain shared chat bubbles",
)

print("mobile chat overflow fix applied")
