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
      (user as any).backendId = data.user_id;

      return true;
    },

    async jwt({ token, user }) {
      if (user) token.backendId = (user as any).backendId;
      // console.log("JWT Token:", token);
      return token;
    },

    async session({ session, token }) {
      (session.user as any).backendId = token.backendId;
      return session;
    },
  }
});

export { handler as GET, handler as POST }
