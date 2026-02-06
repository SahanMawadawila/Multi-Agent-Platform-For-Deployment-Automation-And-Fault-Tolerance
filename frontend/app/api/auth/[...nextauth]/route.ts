import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import GitHubProvider from "next-auth/providers/github"

// Refresh the backend token using refresh token
async function refreshBackendToken(refreshToken: string) {
  try {
    const res = await fetch(process.env.BACKEND_URL + "/auth/refresh", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

const handler = NextAuth({
  providers: [
    GoogleProvider({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
    GitHubProvider({
      clientId: process.env.GITHUB_ID!,
      clientSecret: process.env.GITHUB_SECRET!,
    }),
  ],

  callbacks: {
    async signIn({ user, account }) {
      const res = await fetch(process.env.BACKEND_URL + "/auth/sync", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: user.email,
          name: user.name,
          provider: account?.provider,
          provider_id: account?.providerAccountId,
        }),
      });

      if (!res.ok) return false;

      const data = await res.json();

      // Save tokens and expiry in user object
      (user as any).backendId = data.user_id;
      (user as any).backendToken = data.access_token;
      (user as any).backendRefreshToken = data.refresh_token;
      (user as any).backendTokenExpiresAt = data.expires_at;

      return true;
    },

    async jwt({ token, user }) {
      // Initial sign in
      if (user) {
        token.backendId = (user as any).backendId;
        token.backendToken = (user as any).backendToken;
        token.backendRefreshToken = (user as any).backendRefreshToken;
        token.backendTokenExpiresAt = (user as any).backendTokenExpiresAt;
      }

      // Check if token needs refresh (5 min buffer before expiry)
      const expiresAt = token.backendTokenExpiresAt as number || 0;
      if (expiresAt && Date.now() >= expiresAt - 5 * 60 * 1000) {
        const refreshed = await refreshBackendToken(token.backendRefreshToken as string);
        if (refreshed) {
          token.backendToken = refreshed.access_token;
          token.backendTokenExpiresAt = refreshed.expires_at;
        }
      }

      return token;
    },

    async session({ session, token }) {
      // Expose backend data to the client session
      (session.user as any).backendId = token.backendId;
      session.backendToken = token.backendToken as string;

      return session;
    },
  }
});

export { handler as GET, handler as POST }
