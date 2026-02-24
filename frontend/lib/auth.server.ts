import { cookies } from "next/headers";
import { decode } from "next-auth/jwt";

async function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Server-side only helper to get the backend JWT token.
 * This token is NEVER exposed to the client - it stays in the HTTP-only cookie.
 * Use this in server actions and API routes to make authenticated requests to the backend.
 */
export async function getBackendToken(maxRetries = 3): Promise<string | undefined> {
  for (let attempt = 0; attempt < maxRetries; attempt++) {
    const cookieStore = await cookies();

    const secureAuthjsCookie = cookieStore.get("__Secure-authjs.session-token")?.value;
    const authjsCookie = cookieStore.get("authjs.session-token")?.value;
    const legacyCookie = cookieStore.get("next-auth.session-token")?.value;

    const authCookie = secureAuthjsCookie || authjsCookie || legacyCookie;
    const cookieName = secureAuthjsCookie
      ? "__Secure-authjs.session-token"
      : authjsCookie
        ? "authjs.session-token"
        : "next-auth.session-token";

    if (authCookie) {
      try {
        const decoded = await decode({
          token: authCookie,
          secret: process.env.AUTH_SECRET!,
          salt: cookieName,
        });

        if (decoded?.backendToken) {
          return decoded.backendToken as string;
        }
      } catch {
        // Continue to retry on decode error
      }
    }

    // Exponential backoff: 100ms, 200ms, 400ms
    if (attempt < maxRetries - 1) {
      await delay(100 * Math.pow(2, attempt));
    }
  }

  return undefined;
}
