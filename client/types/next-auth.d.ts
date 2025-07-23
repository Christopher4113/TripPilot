import type { DefaultSession, DefaultUser } from "next-auth"

declare module "next-auth" {
  interface User extends DefaultUser {
    username: string | null;
  }

  interface Session extends DefaultSession {
    user: {
      username: string | null;
      email?: string | null;
      name?: string | null;
    };
  }
}