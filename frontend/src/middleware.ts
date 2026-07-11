import { withAuth } from 'next-auth/middleware'
import { NextResponse } from 'next/server'

export default withAuth(
  function middleware(req) {
    const token = req.nextauth.token
    const pathname = req.nextUrl.pathname

    // Allow login page without auth
    if (pathname === '/login') {
      if (token) {
        return NextResponse.redirect(new URL('/dashboard', req.url))
      }
      return NextResponse.next()
    }

    // Protect dashboard routes
    if (!token && pathname.startsWith('/dashboard')) {
      return NextResponse.redirect(new URL('/login', req.url))
    }

    return NextResponse.next()
  },
  {
    callbacks: {
      authorized: ({ token, req }) => {
        const pathname = req.nextUrl.pathname
        // Allow public paths
        if (pathname === '/login' || pathname === '/api/auth' || pathname.startsWith('/api/auth/')) {
          return true
        }
        // Require token for protected paths
        return !!token
      },
    },
  },
)

export const config = {
  matcher: [
    '/((?!_next/static|_next/image|favicon.ico|api/backend|api/auth).*)',
  ],
}
