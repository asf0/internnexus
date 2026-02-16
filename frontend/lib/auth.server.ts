import { cookies } from "next/headers";
import { decode } from "next-auth/jwt";

/**
 * Server-side only helper to get the backend JWT token.
 * This token is NEVER exposed to the client - it stays in the HTTP-only cookie.
 * Use this in server actions and API routes to make authenticated requests to the backend.
 */
export async function getBackendToken(): Promise<string | undefined> {
  const cookieStore = await cookies();
  
  const authCookie = 
    cookieStore.get("__Secure-next-auth.session-token")?.value ||
    cookieStore.get("authjs.session-token")?.value ||
    cookieStore.get("next-auth.session-token")?.value;
  
  if (!authCookie) return undefined;

  try {
    const token = await decode({
      token: authCookie,
      secret: process.env.AUTH_SECRET!,
      salt: "authjs.session-token",
    });
    
    return token?.backendToken as string | undefined;
  } catch (error) {
    console.error("Error getting backend token:", error);
    return undefined;
  }
}
