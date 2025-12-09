import NextAuth from "next-auth"
import GoogleProvider from "next-auth/providers/google"
import GitHubProvider from "next-auth/providers/github"

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

      // ⭐️ Save both in user object
      (user as any).backendId = data.user_id;
      (user as any).backendToken = data.access_token;

      return true;
    },

    async jwt({ token, user }) {
      // ⭐️ Save backend data into token
      if (user) {
        token.backendId = (user as any).backendId;
        token.backendToken = (user as any).backendToken; 
      }

      return token;
    },

    async session({ session, token }) {
      // ⭐️ Expose backend data to the client session
      (session.user as any).backendId = token.backendId;
      session.backendToken = token.backendToken;

      return session;
    },
  }
});

export { handler as GET, handler as POST }
