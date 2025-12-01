"use client"
import { useSession, signIn, signOut } from "next-auth/react"

export default function AuthButton() {
  const { data: session } = useSession()
  console.log(session)

  if (!session) {
    return (
      <>
        <button onClick={() => signIn("google")}>Sign in with Google</button>
        <button onClick={() => signIn("github")}>Sign in with GitHub</button>
      </>
    )
  }

  return (
    
    <button onClick={() => signOut()}>Sign Out</button>
  )
}
