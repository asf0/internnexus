import { cookies } from "next/headers";
import { decode } from "next-auth/jwt";

/**
 * Server-side only helper to get the backend JWT token.
 * This token is NEVER exposed to the client - it stays in the HTTP-only cookie.
 * Use this in server actions and API routes to make authenticated requests to the backend.
 */
export async function getBackendToken(): Promise<string | undefined> {
  const cookieStore = await cookies();
  
  const secureAuthjsCookie = cookieStore.get("__Secure-authjs.session-token")?.value;
  const authjsCookie = cookieStore.get("authjs.session-token")?.value;
  const legacyCookie = cookieStore.get("next-auth.session-token")?.value;
  
  const authCookie = secureAuthjsCookie || authjsCookie || legacyCookie;
  const cookieName = secureAuthjsCookie ? "__Secure-authjs.session-token" 
    : authjsCookie ? "authjs.session-token" 
    : "next-auth.session-token";
  
  if (!authCookie) {
    return undefined;
  }

  try {
    const decoded = await decode({
      token: authCookie,
      secret: process.env.AUTH_SECRET!,
      salt: cookieName,
    });
    
    return decoded?.backendToken as string | undefined;
  } catch {
    return undefined;
  }
}
