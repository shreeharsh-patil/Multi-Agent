import 'next-auth'

declare module 'next-auth' {
  interface Session {
    user: {
      id: string
      name?: string | null
      email?: string | null
      image?: string | null
    }
    accessToken?: string
  }

  interface Token {
    accessToken?: string
    sub?: string
  }
}

declare module 'next-auth/jwt' {
  interface JWT {
    accessToken?: string
    sub?: string
  }
}
