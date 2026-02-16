import { cookies } from "next/headers";
import { decode } from "next-auth/jwt";

/**
 * Server-side only helper to get the backend JWT token.
 * This token is NEVER exposed to the client - it stays in the HTTP-only cookie.
 * Use this in server actions and API routes to make authenticated requests to the backend.
 */
export async function getBackendToken(): Promise<string | undefined> {
  const cookieStore = await cookies();
  
  // Log all available cookies for debugging
  const allCookies = cookieStore.getAll();
  console.log("[getBackendToken] All cookies:", allCookies.map(c => c.name));
  
  const secureCookie = cookieStore.get("__Secure-next-auth.session-token")?.value;
  const authjsCookie = cookieStore.get("authjs.session-token")?.value;
  const legacyCookie = cookieStore.get("next-auth.session-token")?.value;
  
  console.log("[getBackendToken] Cookie check:", {
    secureCookieLength: secureCookie?.length || 0,
    authjsCookieLength: authjsCookie?.length || 0,
    legacyCookieLength: legacyCookie?.length || 0,
  });
  
  const authCookie = secureCookie || authjsCookie || legacyCookie;
  
  if (!authCookie) {
    console.log("[getBackendToken] No auth cookie found!");
    return undefined;
  }

  try {
    console.log("[getBackendToken] Attempting decode with AUTH_SECRET length:", process.env.AUTH_SECRET?.length);
    
    const decoded = await decode({
      token: authCookie,
      secret: process.env.AUTH_SECRET!,
      salt: "authjs.session-token",
    });
    
    console.log("[getBackendToken] Decode result:", {
      hasToken: !!decoded,
      hasBackendToken: decoded && "backendToken" in decoded,
      tokenKeys: decoded ? Object.keys(decoded) : [],
    });
    
    return decoded?.backendToken as string | undefined;
  } catch (error) {
    console.error("[getBackendToken] Decode error:", error);
    return undefined;
  }
}
