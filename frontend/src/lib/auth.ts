import { createAuthClient } from "better-auth/react";

const authUrl = import.meta.env.VITE_AUTH_URL || "http://localhost:3001";

export const authClient = createAuthClient({
  baseURL: authUrl,
});

export const { signIn, signUp, signOut, useSession } = authClient;
