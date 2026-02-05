"use client"

import { SessionProvider } from "next-auth/react"

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <SessionProvider
      // Refetch session every 4 minutes to trigger token refresh
      refetchInterval={4 * 60}
      refetchOnWindowFocus={true}
    >
      {children}
    </SessionProvider>
  )
}
