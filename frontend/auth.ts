import NextAuth from "next-auth"
import GitHub from "next-auth/providers/github"
import Google from "next-auth/providers/google"
import Credentials from "next-auth/providers/credentials"
import type { DefaultSession } from "next-auth"

const backendBaseUrl = process.env.BACKEND_URL;

// Extend the session type to include accessToken and user.id
declare module "next-auth" {
  interface Session {
    accessToken?: string
    backendToken?: string  // Our backend JWT token
    user: {
      id?: string
    } & DefaultSession["user"]
  }

  interface JWT {
    accessToken?: string
    backendToken?: string  // Our backend JWT token
    id?: string
    provider?: string
  }

  interface User {
    backendToken?: string
  }
}
 
export const { handlers, signIn, signOut, auth } = NextAuth({
  trustHost: true,
  cookies: {
      pkceCodeVerifier: {
        name: 'authjs.pkce.code_verifier',
        options: {
          httpOnly: true,
          sameSite: 'lax',
          path: '/',
          secure: false, // Critical for localhost http
        },
      },
    },
  providers: [
    GitHub({
      clientId: process.env.GH_CLIENT_ID as string,
      clientSecret: process.env.GH_CLIENT_SECRET as string,
    }),
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID as string,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET as string,
    }),
    Credentials({
      credentials: {
        email: { label: "Email", type: "email" },
        password: { label: "Password", type: "password" }
      },
      authorize: async (credentials) => {
        // Call backend login endpoint
        const email = credentials?.email as string | undefined
        const password = credentials?.password as string | undefined
        
        if (!email || !password) {
          return null
        }
        
        try {
          const response = await fetch(`${backendBaseUrl}/auth/login`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ email, password }),
          })
          
          if (!response.ok) {
            const error = await response.json()
            throw new Error(error.detail?.message || "Login failed")
          }
          
          const data = await response.json()
          
          return {
            id: data.user.id,
            email: data.user.email,
            name: data.user.name,
            backendToken: data.access_token,
          }
        } catch (error) {
          console.error("Login error:", error)
          return null
        }
      }
    })
  ],
  callbacks: {
    async jwt({ token, user, account, profile }) {
      // Handle OAuth sign-in
      if (account && profile) {
        // Exchange OAuth token for backend JWT
        try {
          if (!profile.email) {
            throw new Error("Email is required from OAuth provider")
          }
          if (!account.access_token) {
            throw new Error("Access token is missing from OAuth provider")
          }
          const oauthData = {
            provider: account.provider,
            provider_account_id: account.providerAccountId,
            email: profile.email,
            name: profile.name || null,
            image: profile.image || null,
            access_token: account.access_token,
            refresh_token: account.refresh_token || null,
            expires_at: account.expires_at 
              ? new Date(account.expires_at * 1000) 
              : null,
          }
          
          const response = await fetch(`${backendBaseUrl}/auth/oauth/callback`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(oauthData),
          })
          
          if (!response.ok) {
            console.error("OAuth callback failed:", await response.text())
            throw new Error("Failed to exchange OAuth token")
          }
          
          const data = await response.json()
          token.backendToken = data.access_token
          token.id = data.user.id
        } catch (error) {
          console.error("OAuth exchange error:", error)
        }
      }
      
      // Handle credentials sign-in
      if (user?.backendToken) {
        token.backendToken = user.backendToken
        token.id = user.id
      }
      
      return token
    },
    async session({ session, token }) {
      // Send backend JWT to client
      session.backendToken = token.backendToken as string
      session.user.id = token.id as string
      return session
    }
  },

  session: {
    strategy: "jwt",
    maxAge: 24 * 60 * 60, // 24 hours
  },
  secret: process.env.AUTH_SECRET,
})
