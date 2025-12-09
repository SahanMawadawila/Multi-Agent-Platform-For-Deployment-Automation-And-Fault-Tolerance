import NextAuth from "next-auth"

declare module "next-auth" {
  interface Session {
    backendToken?: string;
    user: {
      name?: string | null;
      email?: string | null;
      image?: string | null;
      backendId?: number | string;
    };
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    backendId?: number | string;
    backendToken?: string;
  }
}
