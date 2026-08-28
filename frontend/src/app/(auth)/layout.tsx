export default function AuthLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="flex min-h-screen min-h-[100svh] items-center justify-center bg-gradient-to-br from-background via-background to-primary/5 p-3 supports-[height:100dvh]:min-h-dvh sm:p-4">
      {children}
    </div>
  )
}
